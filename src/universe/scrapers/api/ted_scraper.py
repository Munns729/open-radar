"""
Scraper for TED (Tenders Electronic Daily) - EU public procurement notices.
Covers DE, NL, BE (and optionally FR) government IT contract winners.
Source: https://api.ted.europa.eu/v3/notices/search (no auth required)
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-3 country codes used by TED
COUNTRY_MAP = {
    "DE": "DEU",  # Germany
    "NL": "NLD",  # Netherlands
    "BE": "BEL",  # Belgium
    "FR": "FRA",  # France
}


class TEDScraper:
    """
    Client for TED Search API (Tenders Electronic Daily).
    Discovers companies winning EU public procurement contracts.
    """

    BASE_URL = "https://api.ted.europa.eu/v3/notices/search"

    def __init__(self, rate_limit_delay: float = 0.6):
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        await asyncio.sleep(self.rate_limit_delay)

    async def _post(
        self, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """POST search request with error handling."""
        if not self.session:
            raise RuntimeError("Scraper context not entered.")

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.post(
                    self.BASE_URL, json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning(
                            f"TED rate limited. Waiting 60s. Attempt {attempt + 1}"
                        )
                        await asyncio.sleep(60)
                    else:
                        text = await response.text()
                        logger.error(
                            f"TED API error {response.status}: {text[:500]}"
                        )
                        return None
            except Exception as e:
                logger.error(f"TED request failed: {e}")
                await asyncio.sleep(2)
        return None

    def _build_query(
        self,
        country_code: str,
        cpv_prefixes: List[str] = None,
        notice_types: List[str] = None,
    ) -> str:
        """
        Build expert search query.
        - place-of-performance: country where contract is performed
        - classification-cpv: CPV codes (72=IT, 48=software, 79=business services)
        - notice-type: can-standard = contract award notice (winners)
        """
        if cpv_prefixes is None:
            cpv_prefixes = ["72*", "48*"]  # IT services, software
        if notice_types is None:
            notice_types = ["can-standard", "can-social", "can-desg", "can-tran"]

        ted_country = COUNTRY_MAP.get(
            country_code.upper(), country_code.upper()
        )
        if len(ted_country) == 2:
            ted_country = COUNTRY_MAP.get(country_code.upper(), ted_country)

        cpv_expr = " OR ".join(
            f"classification-cpv = {cp}" for cp in cpv_prefixes
        )
        notice_expr = " OR ".join(
            f"notice-type = {nt}" for nt in notice_types
        )
        # Prefer recent notices (eForms have better winner-name structure)
        from datetime import datetime, timezone
        year_ago = (datetime.now(timezone.utc).year - 1) * 10000
        return (
            f"place-of-performance = {ted_country} AND "
            f"({cpv_expr}) AND "
            f"({notice_expr}) AND "
            f"publication-date >= {year_ago}"
        )

    def _extract_companies(
        self,
        notices: List[Dict],
        country_code: str,
        source_base: str = "https://ted.europa.eu/en/notice/",
    ) -> List[Dict[str, Any]]:
        """
        Extract company records from TED notice response.
        TED returns flat fields: winner-name, business-name, organisation-name-serv-prov
        (can be dict with lang keys, or list of values).
        """
        companies = {}
        iso2 = country_code.upper()[:2]
        if len(iso2) == 3:
            iso2 = {"DEU": "DE", "NLD": "NL", "BEL": "BE", "FRA": "FR"}.get(
                iso2, iso2[:2]
            )

        for notice in notices:
            try:
                pub_num = notice.get("publication-number") or ""
                source_url = f"{source_base}{pub_num}" if pub_num else None

                # Collect company names from winner/business/org fields
                # Each can be: str, list, or dict like {"deu": ["Name1"], "eng": ["Name2"]}
                def _flatten(val):
                    if val is None:
                        return []
                    if isinstance(val, str):
                        return [val.strip()] if val.strip() else []
                    if isinstance(val, list):
                        return [str(v).strip() for v in val if v]
                    if isinstance(val, dict):
                        out = []
                        for v in val.values():
                            out.extend(_flatten(v))
                        return out
                    return []

                names = []
                for key in [
                    "winner-name",
                    "business-name",
                    "organisation-name-serv-prov",
                    "organisation-name-tenderer",
                ]:
                    names.extend(_flatten(notice.get(key)))

                # Skip buyer names (govt bodies) - heuristic: skip if contains police, ministry, etc
                skip_keywords = (
                    "polizei",
                    "minister",
                    "ministry",
                    "bundesamt",
                    "stadt ",
                    "gemeinde",
                    "landkreis",
                    "regional",
                    "university",
                    "universität",
                    "krankenhaus",
                    "hospital",
                )
                for name in names:
                    if not name or len(name) < 2:
                        continue
                    name_lower = name.lower()
                    if any(kw in name_lower for kw in skip_keywords):
                        continue
                    if name in companies:
                        continue

                    # Winner/business info
                    winner_country = notice.get("winner-country") or notice.get(
                        "place-of-performance"
                    )
                    country_val = iso2
                    if winner_country:
                        c = _flatten(winner_country)
                        if c and c[0]:
                            cc = str(c[0])[:2]
                            country_val = {"DEU": "DE", "NLD": "NL", "BEL": "BE", "FRA": "FR"}.get(
                                str(c[0])[:3], cc
                            )

                    reg = _flatten(notice.get("winner-identifier") or notice.get("business-identifier"))
                    reg_str = reg[0] if reg else None

                    city = _flatten(notice.get("business-city") or notice.get("winner-post-code"))
                    address_str = ", ".join(city) if city else None

                    website = _flatten(notice.get("winner-internet-address"))
                    website_str = website[0] if website else None

                    companies[name] = {
                        "name": name,
                        "website": website_str,
                        "description": "TED public procurement contractor (IT/services)",
                        "address": address_str,
                        "hq_country": country_val,
                        "companies_house_number": None,
                        "registration_number": reg_str,
                        "certification_type": None,
                        "certification_number": None,
                        "scope": None,
                        "issuing_body": None,
                        "source_url": source_url,
                    }

            except Exception as e:
                logger.warning(f"Error parsing TED notice: {e}")
                continue

        return list(companies.values())

    async def discover(
        self,
        country_code: str,
        limit: int = 50,
        cpv_prefixes: List[str] = None,
        page_start: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Discover companies from TED for a given country.

        Args:
            country_code: ISO 2-letter (DE, NL, BE, FR) or 3-letter (DEU, NLD, etc.)
            limit: Max companies to return
            cpv_prefixes: CPV code prefixes, e.g. ["72*", "48*"] for IT/software
        """
        query = self._build_query(country_code, cpv_prefixes=cpv_prefixes)
        # TED API requires explicit fields from supported list
        fields = [
            "publication-date",
            "place-of-performance",
            "winner-name",
            "winner-country",
            "winner-identifier",
            "winner-post-code",
            "winner-internet-address",
            "organisation-name-serv-prov",
            "organisation-name-tenderer",
            "business-name",
            "business-identifier",
            "business-city",
        ]
        all_companies = []
        page = page_start
        page_size = min(50, limit)
        seen_names = set()

        logger.info(f"TED discovery for {country_code}: {query[:80]}...")

        while len(all_companies) < limit:
            payload = {
                "query": query,
                "fields": fields,
                "page": page,
                "limit": page_size,
                "paginationMode": "PAGE_NUMBER",
            }

            data = await self._post(payload)
            if not data:
                break

            notices = data.get("notices") or data.get("results") or []
            if isinstance(data.get("notice"), list):
                notices = data["notice"]
            elif isinstance(data.get("notice"), dict):
                notices = [data["notice"]]

            if not notices:
                break

            companies = self._extract_companies(notices, country_code)
            for c in companies:
                if c["name"] not in seen_names:
                    seen_names.add(c["name"])
                    all_companies.append(c)
                    if len(all_companies) >= limit:
                        break

            if len(notices) < page_size:
                break
            page += 1
            if page > 60:  # 60 * 50 = 3000, stay under 15k limit
                break

        logger.info(f"TED discovered {len(all_companies)} companies for {country_code}")
        return all_companies[:limit]

    async def scrape(
        self,
        countries: List[str] = None,
        limit_per_country: int = 25,
        page_start: int = 1,
    ) -> Any:
        """
        Scrape TED for multiple countries. Returns object with .data for workflow.
        Use page_start for pagination across runs.
        """
        if countries is None:
            countries = ["DE", "NL", "BE"]

        all_data = []
        for cc in countries:
            try:
                companies = await self.discover(cc, limit=limit_per_country, page_start=page_start)
                all_data.extend(companies)
            except Exception as e:
                logger.warning(f"TED scrape failed for {cc}: {e}")

        class Result:
            data = []

        Result.data = all_data
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with TEDScraper() as scraper:
            print("Testing TED discovery for DE (limit=5)...")
            results = await scraper.discover("DE", limit=5)
            for r in results:
                print(f"  - {r['name']}: {r.get('description', '')[:80]}...")
            print(f"Total: {len(results)} companies")

    asyncio.run(main())

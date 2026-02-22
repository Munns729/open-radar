"""
Contracts Finder scraper - UK below-threshold public procurement.
Discovers companies winning UK government contracts (awards).
Source: https://www.contractsfinder.service.gov.uk/ - OCDS API, no auth.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# CPV prefixes for IT/software/services
IT_CPV_PREFIXES = ["72", "48", "79"]  # IT services, software, business services


class ContractsFinderScraper:
    """
    Client for Contracts Finder OCDS API.
    Discovers UK companies winning public procurement contracts.
    """

    BASE_URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

    def __init__(self, rate_limit_delay: float = 0.5):
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Accept": "application/json"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        await asyncio.sleep(self.rate_limit_delay)

    def _extract_suppliers_from_releases(self, releases: List[Dict]) -> List[Dict[str, Any]]:
        """Extract supplier/winner companies from OCDS releases."""
        companies = {}
        for release in releases:
            try:
                parties = release.get("parties") or []
                awards = release.get("awards") or []
                tender = release.get("tender", {})
                ocid = release.get("ocid", "")

                # Get winner IDs from awards
                winner_ids = set()
                for award in awards:
                    for sup in award.get("suppliers", []):
                        winner_ids.add(sup.get("id", ""))

                # Map parties to companies
                for party in parties:
                    pid = party.get("id", "")
                    if pid not in winner_ids and not winner_ids:
                        # If no awards, take all parties (some notices lack award structure)
                        pass
                    elif winner_ids and pid not in winner_ids:
                        continue

                    name = (party.get("name") or "").strip()
                    if not name or len(name) < 2:
                        continue

                    # Skip govt bodies
                    skip = ("ministry", "council", "authority", "nhs", "police", "borough")
                    if any(s in name.lower() for s in skip):
                        continue

                    if name in companies:
                        continue

                    addr = party.get("address", {})
                    address_parts = [
                        addr.get("streetAddress"),
                        addr.get("locality"),
                        addr.get("postalCode"),
                        addr.get("countryName"),
                    ]
                    address_str = ", ".join(p for p in address_parts if p) or None

                    identifier = party.get("identifier", {})
                    reg_num = identifier.get("id") or identifier.get("legalName")

                    companies[name] = {
                        "name": name,
                        "website": None,
                        "description": "UK Contracts Finder - public procurement contractor",
                        "address": address_str,
                        "hq_country": "GB",
                        "companies_house_number": None,
                        "registration_number": str(reg_num) if reg_num else None,
                        "certification_type": None,
                        "certification_number": None,
                        "scope": None,
                        "issuing_body": None,
                        "source_url": f"https://www.contractsfinder.service.gov.uk/Notice/{ocid}" if ocid else None,
                    }

            except Exception as e:
                logger.warning(f"Error parsing Contracts Finder release: {e}")
                continue

        return list(companies.values())

    async def discover(
        self,
        limit: int = 50,
        published_from_days: int = 365,
        stages: str = "award",
    ) -> List[Dict[str, Any]]:
        """
        Discover companies from Contracts Finder award notices.

        Args:
            limit: Max companies to return
            published_from_days: Only notices from last N days
            stages: OCDS stages - "award" for contract winners
        """
        from_dt = datetime.now(timezone.utc) - timedelta(days=published_from_days)
        published_from = from_dt.strftime("%Y-%m-%dT00:00:00Z")

        params = {
            "publishedFrom": published_from,
            "stages": stages,
            "limit": min(100, limit * 2),
        }

        all_companies = []
        cursor = None

        while len(all_companies) < limit:
            if cursor:
                params["cursor"] = cursor

            try:
                await self._rate_limit()
                async with self.session.get(self.BASE_URL, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Contracts Finder API {response.status}")
                        break

                    data = await response.json()
            except Exception as e:
                logger.error(f"Contracts Finder request failed: {e}")
                break

            releases = data.get("releases") or []
            if not releases:
                break

            companies = self._extract_suppliers_from_releases(releases)
            seen = {c["name"] for c in all_companies}
            for c in companies:
                if c["name"] not in seen:
                    seen.add(c["name"])
                    all_companies.append(c)
                    if len(all_companies) >= limit:
                        break

            cursor = data.get("cursor")
            if not cursor:
                break

        logger.info(f"Contracts Finder: {len(all_companies)} companies")
        return all_companies[:limit]

    async def scrape(self, limit: int = 50) -> Any:
        """Workflow-compatible scrape."""
        companies = await self.discover(limit=limit)

        class Result:
            data = []

        Result.data = companies
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with ContractsFinderScraper() as scraper:
            results = await scraper.discover(limit=5)
            for r in results:
                print(f"  - {r['name']}: {r.get('address', '')[:50]}...")

    asyncio.run(main())

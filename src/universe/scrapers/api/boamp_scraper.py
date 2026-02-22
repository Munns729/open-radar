"""
Scraper for BOAMP (Bulletin Officiel des Annonces des Marchés Publics) - French public procurement.
Discovers IT/tech services companies winning French government contracts.
Source: https://boamp-datadila.opendatasoft.com/api/explore/v2.1/ (OpenDataSoft, no auth)
"""
import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# BOAMP descriptor codes: 72=IT/technical control, 48=software, 74=business services, 274=services
IT_SERVICE_DESCRIPTORS = {"72", "48", "74", "274"}


class BOAMPScraper:
    """
    Client for BOAMP OpenDataSoft API.
    Discovers French companies winning public procurement contracts (award notices).
    """

    BASE_URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"

    def __init__(self, rate_limit_delay: float = 0.5):
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Accept": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        await asyncio.sleep(self.rate_limit_delay)

    async def _get(
        self, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """GET request with error handling."""
        if not self.session:
            raise RuntimeError("Scraper context not entered.")

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning(
                            f"BOAMP rate limited. Waiting 60s. Attempt {attempt + 1}"
                        )
                        await asyncio.sleep(60)
                    else:
                        text = await response.text()
                        logger.error(
                            f"BOAMP API error {response.status}: {text[:500]}"
                        )
                        return None
            except Exception as e:
                logger.error(f"BOAMP request failed: {e}")
                await asyncio.sleep(2)
        return None

    def _has_it_service_signal(self, record: Dict) -> bool:
        """Check if record is IT/tech services related (descriptors or type_marche)."""
        dc = record.get("dc") or record.get("descripteur_code") or []
        if isinstance(dc, str):
            dc = [dc]
        if any(d in IT_SERVICE_DESCRIPTORS for d in dc):
            return True
        type_marche = record.get("type_marche") or []
        if isinstance(type_marche, str):
            type_marche = [type_marche]
        if "SERVICES" in type_marche:
            return True
        return False

    def _extract_titulaire_from_donnees(self, donnees_str: str) -> Optional[Dict]:
        """Parse donnees JSON to get TITULAIRE (winner) details."""
        if not donnees_str:
            return None
        try:
            data = json.loads(donnees_str)
            attr = data.get("ATTRIBUTION") or {}
            decision = attr.get("DECISION") or {}
            if isinstance(decision, list):
                decision = decision[0] if decision else {}
            titulaire = decision.get("TITULAIRE")
            if not titulaire:
                return None
            if isinstance(titulaire, list):
                titulaire = titulaire[0] if titulaire else {}
            return titulaire if isinstance(titulaire, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _extract_companies(
        self, records: List[Dict], source_base: str = "https://www.boamp.fr/pages/avis/?q=idweb:"
    ) -> List[Dict[str, Any]]:
        """Extract company records from BOAMP API response."""
        companies = {}


        for record in records:
            try:
                if not self._has_it_service_signal(record):
                    continue

                titulaires = record.get("titulaire")
                if not titulaires:
                    donnees = record.get("donnees")
                    if donnees:
                        t = self._extract_titulaire_from_donnees(donnees)
                        if t:
                            titulaires = [t.get("DENOMINATION")]
                        else:
                            continue
                    else:
                        continue

                if isinstance(titulaires, str):
                    titulaires = [titulaires]

                idweb = record.get("idweb") or record.get("id", "")
                source_url = f"{source_base}{idweb}" if idweb else None

                for name in titulaires:
                    if not name or not isinstance(name, str):
                        continue
                    name = name.strip()
                    if len(name) < 2:
                        continue

                    # Skip government/obvious entities
                    skip = (
                        "ministère",
                        "ministere",
                        "mairie",
                        "ville de",
                        "région",
                        "region",
                        "département",
                        "departement",
                        "état",
                        "etat",
                        "groupe",
                    )
                    if any(s in name.lower() for s in skip):
                        continue

                    if name in companies:
                        continue

                    # Try to get address from donnees
                    address = None
                    donnees_str = record.get("donnees")
                    if donnees_str:
                        t = self._extract_titulaire_from_donnees(donnees_str)
                        if t:
                            parts = [
                                t.get("ADRESSE"),
                                t.get("CP"),
                                t.get("VILLE"),
                            ]
                            address = ", ".join(p for p in parts if p)

                    companies[name] = {
                        "name": name,
                        "website": None,
                        "description": f"BOAMP public procurement contractor (France)",
                        "address": address,
                        "hq_country": "FR",
                        "companies_house_number": None,
                        "registration_number": None,
                        "certification_type": None,
                        "certification_number": None,
                        "scope": None,
                        "issuing_body": None,
                        "source_url": source_url,
                    }

            except Exception as e:
                logger.warning(f"Error parsing BOAMP record: {e}")
                continue

        return list(companies.values())

    async def discover(
        self,
        limit: int = 50,
        offset: int = 0,
        min_year: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover companies from BOAMP award notices (avis d'attribution).
        Filters for IT/tech services contracts.

        Args:
            limit: Max companies to return
            offset: Pagination offset
            min_year: Only include notices from this year onwards
        """
        from datetime import datetime, timezone

        year = min_year or (datetime.now(timezone.utc).year - 2)
        # OpenDataSoft where: nature_categorise contains 'attribution'
        where = "nature_categorise like '%attribution%'"
        if min_year:
            where += f" AND dateparution >= '{year}-01-01'"

        params = {
            "where": where,
            "limit": min(100, limit * 2),
            "offset": offset,
            "order_by": "dateparution desc",
        }

        data = await self._get(params)
        if not data:
            return []

        records = data.get("results") or []
        companies = self._extract_companies(records)

        logger.info(f"BOAMP discovered {len(companies)} companies (from {len(records)} records)")
        return companies[:limit]

    async def scrape(self, limit: int = 50, offset: int = 0) -> Any:
        """
        Scrape BOAMP for French IT contractors. Returns object with .data for workflow.
        Use offset for pagination across runs.
        """
        all_data = []
        try:
            companies = await self.discover(limit=limit, offset=offset)
            all_data.extend(companies)
        except Exception as e:
            logger.warning(f"BOAMP scrape failed: {e}")

        class Result:
            data = []

        Result.data = all_data
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with BOAMPScraper() as scraper:
            print("Testing BOAMP discovery (limit=5)...")
            results = await scraper.discover(limit=5)
            for r in results:
                print(f"  - {r['name']}: {(r.get('address') or '')[:60]}...")
            print(f"Total: {len(results)} companies")

    asyncio.run(main())

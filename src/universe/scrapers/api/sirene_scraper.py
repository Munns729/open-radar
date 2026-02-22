"""
SIRENE / API Recherche d'Entreprises - French company registry discovery.
Discovers French IT/tech services companies by NAF code.
Source: https://recherche-entreprises.api.gouv.fr - no auth, 7 req/sec.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.universe.scrapers.base import ApiScraper

logger = logging.getLogger(__name__)

# NAF codes for IT services (French activity classification)
FR_IT_NAF_CODES = ["62.01Z", "62.02A", "62.03Z", "62.09Z"]


class SIRENEScraper(ApiScraper):
    """
    Client for API Recherche d'Entreprises (French company search).
    Discovers French IT companies by NAF code.
    """

    BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"

    def __init__(self, rate_limit_delay: float = 0.2):
        super().__init__(
            rate_limit_delay=rate_limit_delay,
            headers={
                "Accept": "application/json",
                "User-Agent": "RADAR-PE-Discovery/1.0 (deal sourcing)",
            },
        )

    def _result_to_company(self, r: Dict) -> Dict[str, Any]:
        """Convert API result to workflow format."""
        name = r.get("nom_complet") or r.get("nom_raison_sociale") or ""
        siren = r.get("siren", "")
        siege = r.get("siege") or {}
        adresse = siege.get("adresse") or ""
        activite = r.get("activite_principale") or ""

        return {
            "name": name.strip(),
            "website": None,
            "description": f"French IT company (NAF {activite})",
            "address": adresse or None,
            "hq_country": "FR",
            "companies_house_number": None,
            "registration_number": siren or None,
            "certification_type": None,
            "certification_number": None,
            "scope": None,
            "issuing_body": None,
            "source_url": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}" if siren else None,
        }

    async def discover(
        self,
        limit: int = 100,
        naf_codes: List[str] = None,
        tranche_effectif: str = None,
        page_start: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Discover French IT companies by NAF code.
        """
        naf = naf_codes or FR_IT_NAF_CODES
        activite = ",".join(naf)
        all_companies = []
        page = page_start
        per_page = min(25, limit)

        while len(all_companies) < limit:
            params = {
                "q": "société",
                "activite_principale": activite,
                "etat_administratif": "A",
                "page": page,
                "per_page": per_page,
            }
            if tranche_effectif:
                params["tranche_effectif_salarie"] = tranche_effectif

            data = await self._get("", params=params)
            if not data:
                break

            results = data.get("results") or []
            if not results:
                break

            for r in results:
                try:
                    c = self._result_to_company(r)
                    if c["name"]:
                        all_companies.append(c)
                        if len(all_companies) >= limit:
                            break
                except Exception as e:
                    logger.warning(f"Error parsing SIRENE result: {e}")

            if len(results) < per_page:
                break
            page += 1
            if page > 40:
                break

        logger.info(f"SIRENE: {len(all_companies)} French IT companies")
        return all_companies[:limit]

    async def scrape(self, limit: int = 100, page_start: int = 1) -> Any:
        """Workflow-compatible scrape. Use page_start for pagination across runs."""
        companies = await self.discover(limit=limit, page_start=page_start)

        class Result:
            data = []

        Result.data = companies
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with SIRENEScraper() as scraper:
            results = await scraper.discover(limit=5)
            for r in results:
                print(f"  - {r['name']} (SIREN {r['registration_number']})")

    asyncio.run(main())

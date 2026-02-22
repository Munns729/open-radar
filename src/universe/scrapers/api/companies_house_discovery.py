"""
Companies House SIC-based discovery for UK IT/tech services companies.
Uses the Companies House advanced search API to find companies by SIC codes.
"""
import asyncio
import logging
from typing import List, Dict, Any, Union

from .companies_house_scraper import CompaniesHouseScraper

logger = logging.getLogger(__name__)

# UK SIC codes for IT services, software, consultancy (sweet spot for PE)
UK_IT_SIC_CODES = [
    "62012",  # Business and domestic software development
    "62020",  # Information technology consultancy
    "62090",  # Other IT and computer service activities
    "70229",  # Management consultancy (other than financial)
    "71129",  # Other engineering activities
]


def _format_address(addr: Union[Dict, str, None]) -> str:
    """Flatten Companies House address object to string."""
    if not addr:
        return ""
    if isinstance(addr, str):
        return addr
    parts = [
        addr.get("address_line_1"),
        addr.get("address_line_2"),
        addr.get("locality"),
        addr.get("postal_code"),
        addr.get("country"),
    ]
    return ", ".join(p for p in parts if p) or ""


class CompaniesHouseDiscoveryScraper:
    """
    Discovers UK companies by SIC code using Companies House advanced search.
    Returns structured company dicts for the workflow.
    """

    def __init__(self, sic_codes: List[str] = None):
        self.sic_codes = sic_codes or UK_IT_SIC_CODES
        self._ch = CompaniesHouseScraper()

    async def __aenter__(self):
        await self._ch.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._ch.__aexit__(exc_type, exc_val, exc_tb)

    async def discover(self, limit: int = 100, start_index: int = 0) -> List[Dict[str, Any]]:
        """
        Discover UK IT/tech companies by SIC code.
        Returns list of dicts in workflow format.
        """
        items = await self._ch.advanced_search(
            sic_codes=self.sic_codes,
            start_index=start_index,
        )
        companies = []
        for item in items[:limit]:
            try:
                addr = item.get("registered_office_address") or {}
                address_str = _format_address(addr)
                companies.append({
                    "name": item.get("company_name") or "",
                    "website": None,
                    "description": f"UK company (SIC: {', '.join(self.sic_codes[:3])})",
                    "address": address_str or None,
                    "hq_country": "GB",
                    "companies_house_number": item.get("company_number"),
                    "registration_number": None,
                    "certification_type": None,
                    "certification_number": None,
                    "scope": None,
                    "issuing_body": None,
                    "source_url": f"https://find-and-update.company-information.service.gov.uk/company/{item.get('company_number')}" if item.get("company_number") else None,
                })
            except Exception as e:
                logger.warning(f"Error parsing CH item: {e}")
                continue

        logger.info(f"Companies House discovery: {len(companies)} companies (SIC: {self.sic_codes})")
        return companies

    async def scrape(self, limit: int = 100, start_index: int = 0) -> Any:
        """Workflow-compatible scrape. Returns object with .data. Use start_index for pagination."""
        companies = await self.discover(limit=limit, start_index=start_index)

        class Result:
            data = []

        Result.data = companies
        return Result


if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with CompaniesHouseDiscoveryScraper() as scraper:
            results = await scraper.discover(limit=5)
            for r in results:
                print(f"  - {r['name']} ({r['companies_house_number']})")

    asyncio.run(main())

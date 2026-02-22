"""
FCA Financial Services Register scraper for UK PE/VC firm discovery.
Uses the official FCA API (requires free registration at register.fca.org.uk/Developer).
"""
import logging
from typing import List, Dict, Any, Optional

from src.core.config import settings

logger = logging.getLogger(__name__)


class FCARegisterScraper:
    """
    Discovers UK PE/VC firms via the FCA Financial Services Register API.
    Set FCA_API_EMAIL and FCA_API_KEY in .env (free registration required).
    """

    UK_SEARCH_TERMS = [
        "Private Equity",
        "Venture Capital",
        "Growth Equity",
        "Capital Partners",
        "Investment Partners",
    ]

    def __init__(self, search_terms: Optional[List[str]] = None):
        self.search_terms = search_terms or self.UK_SEARCH_TERMS

    def _get_client(self):
        """Lazy import to avoid requiring the package when FCA is not configured."""
        if not settings.fca_api_email or not settings.fca_api_key:
            raise ValueError(
                "FCA_API_EMAIL and FCA_API_KEY must be set. "
                "Register at https://register.fca.org.uk/Developer/s/"
            )
        from financial_services_register_api.api import FinancialServicesRegisterApiClient
        return FinancialServicesRegisterApiClient(
            settings.fca_api_email,
            settings.fca_api_key,
        )

    def scrape(self, limit_per_term: int = 50) -> List[Dict[str, Any]]:
        """
        Search FCA Register for PE/VC firms. Returns list of firm dicts
        with keys: name, reference_number, status, location (extracted from name).
        """
        try:
            client = self._get_client()
        except ValueError as e:
            logger.warning("FCA Register skipped: %s", e)
            return []

        seen_names = set()
        results = []

        for term in self.search_terms:
            try:
                res = client.common_search(term, "firm")
                if not res or not getattr(res, "data", None):
                    continue

                data = res.data
                if not isinstance(data, list):
                    data = [data] if data else []

                for item in data[:limit_per_term]:
                    name_raw = item.get("Name") or item.get("name", "")
                    if not name_raw or name_raw in seen_names:
                        continue

                    # Parse "Firm Name (Postcode: XY1 2AB)" to extract name and location
                    name = name_raw
                    location = "UK"
                    if " (Postcode:" in name_raw:
                        name, _ = name_raw.split(" (Postcode:", 1)
                        name = name.strip()
                        # Could extract postcode for region, but UK is sufficient

                    # Skip "No longer authorised" if desired
                    status = item.get("Status", "")
                    if status and "No longer" in str(status):
                        continue

                    seen_names.add(name_raw)
                    results.append({
                        "name": name.strip(),
                        "reference_number": item.get("Reference Number"),
                        "status": status,
                        "location": location,
                        "hq_country": "UK",
                    })

            except Exception as e:
                logger.warning("FCA search failed for '%s': %s", term, e)

        logger.info("FCA Register returned %d UK firms", len(results))
        return results

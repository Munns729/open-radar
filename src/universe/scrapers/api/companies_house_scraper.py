"""
Scraper for Companies House API (UK).
Fetches company profile, filing history, and parses iXBRL accounts for turnover.
"""
import asyncio
import io
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

import aiohttp
from src.core.data_types import ScraperOutput

from src.core.config import settings

API_KEY = settings.companies_house_api_key or ""
DOCUMENT_API_BASE = "https://document-api.company-information.service.gov.uk"

logger = logging.getLogger(__name__)

# iXBRL tag names for turnover/revenue (UK GAAP, FRS 102, IFRS)
TURNOVER_TAG_NAMES = frozenset({
    "turnover", "revenue", "turnoverrevenue", "revenueoperatingactivities",
    "revenuefromcontractswithcustomers", "salesrevenuegoodsservices",
    "uk-gaap:turnover", "uk-gaap:revenue", "ifrs-full:revenuefromcontractswithcustomers",
})


class CompaniesHouseScraper:
    """
    Client for Companies House REST API.
    """
    BASE_URL = "https://api.company-information.service.gov.uk"
    
    def __init__(self, api_key: str = API_KEY, rate_limit_delay: float = 0.5):
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay # 600 reqs / 5 mins = ~2 reqs/sec max, safest is 0.5s delay
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            logger.warning("No Companies House API Key found. Scraper will fail on authenticated requests.")

    async def __aenter__(self):
        # Basic Auth: username is API key, password is empty string
        auth = aiohttp.BasicAuth(login=self.api_key, password="")
        self.session = aiohttp.ClientSession(auth=auth, headers={
            "Accept": "application/json"
        })
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        """Simple sleep to respect rate limits"""
        await asyncio.sleep(self.rate_limit_delay)

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Authenticated GET request with error handling"""
        if not self.session:
            raise RuntimeError("Scraper context not entered.")
            
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.info(f"Companies House 404 for {endpoint}")
                        return None
                    elif response.status == 429:
                        logger.warning(f"Rate limited by Companies House. Waiting 60s. Attempt {attempt + 1}")
                        await asyncio.sleep(60)
                    else:
                        logger.error(f"Failed to fetch {url}: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                await asyncio.sleep(1)
        return None

    async def get_company(self, company_number: str) -> Optional[Dict[str, Any]]:
        """Get basic company profile"""
        return await self._get(f"/company/{company_number}")

    async def get_company_financials(self, company_number: str) -> Optional[Dict[str, Any]]:
        """
        Get latest accounts/financials.
        """
        profile = await self.get_company(company_number)
        if not profile:
            return None
            
        return profile.get('accounts', {})

    async def get_filing_history(self, company_number: str, category: str = "accounts") -> List[Dict[str, Any]]:
        """Get filing history filtered by category (e.g. accounts)."""
        data = await self._get(
            f"/company/{company_number}/filing-history",
            params={"category": category, "items_per_page": 25}
        )
        if not data or "items" not in data:
            return []
        return data["items"]

    def _extract_document_id(self, metadata_url: str) -> Optional[str]:
        """Extract document_id from document_metadata URL."""
        if not metadata_url:
            return None
        # URL format: .../document/{id}/metadata or .../document/{id}
        match = re.search(r"/document/([A-Za-z0-9_-]+)(?:/metadata)?", metadata_url)
        return match.group(1) if match else None

    async def _fetch_document_content(self, document_id: str) -> Optional[str]:
        """
        Fetch document content from Document API.
        Requests iXBRL (application/xhtml+xml); follows 302 redirect.
        """
        if not self.session:
            raise RuntimeError("Scraper context not entered.")
        url = f"{DOCUMENT_API_BASE}/document/{document_id}/content"
        auth = aiohttp.BasicAuth(login=self.api_key, password="")
        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(
                    url,
                    auth=auth,
                    headers={"Accept": "application/xhtml+xml"},
                    allow_redirects=True,
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    if response.status == 404:
                        return None
                    if response.status == 429:
                        await asyncio.sleep(60)
                        continue
                    logger.debug(f"Document API {response.status} for {document_id}")
                    return None
            except Exception as e:
                logger.warning(f"Document fetch failed: {e}")
                await asyncio.sleep(1)
        return None

    def _parse_turnover_from_ixbrl(self, html_content: str) -> Optional[int]:
        """
        Parse turnover/revenue from iXBRL HTML.
        Returns value in GBP (integer), or None if not found.
        """
        try:
            from ixbrlparse import IXBRL
            doc = IXBRL(io.StringIO(html_content), raise_on_error=False)
            for item in getattr(doc, "numeric", []) or []:
                name = (getattr(item, "name", "") or "").lower().replace("-", "").replace("_", "")
                if any(tag in name for tag in TURNOVER_TAG_NAMES):
                    val = getattr(item, "value", None)
                    if val is not None and isinstance(val, (int, float)):
                        # Check unit - prefer GBP
                        unit = getattr(item, "unit", None) or ""
                        unit_str = str(unit).lower()
                        if "gbp" in unit_str or "sterling" in unit_str:
                            return int(val)
                        if "eur" in unit_str or "usd" in unit_str:
                            # Approximate conversion
                            rate = 0.85 if "eur" in unit_str else 0.8
                            return int(val * rate)
                        # Assume GBP if no unit (common in UK filings)
                        return int(val)
        except Exception as e:
            logger.debug(f"ixbrlparse failed: {e}")
        # Fallback: regex for common turnover patterns in iXBRL
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "lxml")
            for tag in soup.find_all(["ix:nonfraction", "ix:nonFraction"]):
                name = (tag.get("name") or "").lower()
                if "turnover" in name or "revenue" in name:
                    text = (tag.get_text() or "").replace(",", "").strip()
                    match = re.search(r"[\d.]+", text)
                    if match:
                        val = float(match.group(0))
                        scale = int(tag.get("scale", 0) or 0)
                        if scale:
                            val *= 10 ** scale
                        return int(val)
        except Exception as e:
            logger.debug(f"BeautifulSoup fallback failed: {e}")
        return None

    async def get_turnover_from_filings(self, company_number: str) -> Optional[int]:
        """
        Fetch latest accounts filing and extract turnover from iXBRL.
        Returns turnover in GBP (integer) or None.
        """
        items = await self.get_filing_history(company_number, category="accounts")
        if not items:
            return None
        for item in items:
            links = item.get("links") or {}
            meta_url = links.get("document_metadata")
            if not meta_url:
                continue
            doc_id = self._extract_document_id(meta_url)
            if not doc_id:
                continue
            content = await self._fetch_document_content(doc_id)
            if not content:
                continue
            turnover = self._parse_turnover_from_ixbrl(content)
            if turnover and turnover > 0:
                logger.info(f"Extracted turnover £{turnover:,} from iXBRL for {company_number}")
                return turnover
        return None

    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """Search for companies by name"""
        data = await self._get("/search/companies", params={"q": query, "items_per_page": 5})
        if data and 'items' in data:
            return data['items']
        return []

    async def advanced_search(self, sic_codes: List[str], start_index: int = 0, incorporated_from: str = None, incorporated_to: str = None) -> List[Dict[str, Any]]:
        """
        Search companies by SIC codes using advanced search endpoint.
        """
        params = {
            "sic_codes": ",".join(sic_codes),
            "company_status": "active",
            "size": 5000,
            "items_per_page": 100, 
            "start_index": start_index
        }
        if incorporated_from:
            params["incorporated_from"] = incorporated_from
        if incorporated_to:
            params["incorporated_to"] = incorporated_to
            
        data = await self._get("/advanced-search/companies", params=params)
        if data and 'items' in data:
            return data['items']
        return []

    async def bulk_enrich(self, company_numbers: List[str]) -> ScraperOutput:
        """
        Fetch details for a list of company numbers.
        Returns a ScraperOutput with enriched data.
        """
        results = []
        logger.info(f"Bulk enriching {len(company_numbers)} companies...")
        
        for cn in company_numbers:
            profile = await self.get_company(cn)
            if profile:
                # Normalize some fields
                # Enhanced Extraction
                sic_desc = self._get_sic_description(profile.get("sic_codes", []))
                size_est = self._estimate_size(profile.get("accounts", {}))
                
                enriched = {
                    "company_number": cn,
                    "legal_name": profile.get("company_name"),
                    "status": profile.get("company_status"),
                    "address": profile.get("registered_office_address"),
                    "sic_codes": profile.get("sic_codes", []),
                    "description": sic_desc, # Placeholder description from SIC
                    "created_at": profile.get("date_of_creation"),
                    "accounts": profile.get("accounts", {}),
                    "size_estimate": size_est,
                    "raw_data": profile
                }
                results.append(enriched)
            
        return ScraperOutput(
            source="Companies House",
            data_type="company_profile",
            data=results,
            row_count=len(results),
            metadata={"requested_count": len(company_numbers)}
        )

    def _get_sic_description(self, sic_codes: List[str]) -> str:
        """Map SIC codes to text description"""
        # MVP Mapping - In prod use full CSV
        SIC_MAP = {
            "62012": "Business and domestic software development",
            "62020": "Information technology consultancy activities",
            "62090": "Other information technology and computer service activities",
            "70229": "Management consultancy activities other than financial management",
            "71129": "Other engineering activities",
            "25400": "Manufacture of weapons and ammunition",
            "30300": "Manufacture of air and spacecraft and related machinery"
        }
        descs = [SIC_MAP.get(code, f"SIC {code}") for code in sic_codes]
        return "; ".join(descs) if descs else "Unknown Sector"

    @staticmethod
    def revenue_plausible_for_accounts(accounts: Dict, revenue_gbp: int) -> bool:
        """Sanity-check LLM revenue against UK account type band."""
        from src.universe.revenue_bands import revenue_plausible_uk
        return revenue_plausible_uk(accounts, revenue_gbp)

    @staticmethod
    def get_band_midpoint(accounts: Dict) -> Optional[Tuple[int, str]]:
        """
        When LLM revenue is misaligned with CH band, return (midpoint_gbp, source_label).
        Returns None if band has no cap (full) or no midpoint (dormant).
        """
        from src.universe.revenue_bands import get_uk_band_from_accounts
        result = get_uk_band_from_accounts(accounts)
        if result is None:
            return None
        cap, midpoint, source = result
        if midpoint <= 0:
            return None
        return (midpoint, source)

    def _estimate_size(self, accounts: Dict) -> Dict[str, Any]:
        """
        Extract exact size only. No estimates.
        """
        # We perform NO estimation based on account type as it can be "woefully off".
        # We only look for explicit data fields.
        last = accounts.get("last_accounts", {})
        
        size_data = {"employees": None, "revenue_band": "Unknown", "revenue_int": None}
        
        # Check for explicit employee count
        if "employees" in last:
             size_data["employees"] = last["employees"]

        return size_data

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        if not settings.companies_house_api_key:
             print("Warning: No API Key found. Set COMPANIES_HOUSE_API_KEY to test.")
        
        async with CompaniesHouseScraper() as scraper:
            print("Searching for 'DeepMind'...")
            results = await scraper.search_companies("DeepMind")
            if results:
                print(f"Found: {results[0].get('company_name')} ({results[0].get('company_number')})")
            else:
                print("No results found.")

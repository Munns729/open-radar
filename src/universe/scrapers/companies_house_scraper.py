"""
Scraper for Companies House API (UK).
"""
import asyncio
import logging
import base64
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import aiohttp
from src.core.data_types import ScraperOutput

from src.core.config import settings

API_KEY = settings.companies_house_api_key or ""

logger = logging.getLogger(__name__)

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
             
        return estimate

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

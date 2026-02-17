"""
OpenCorporates Scraper - European company data source.

Uses the OpenCorporates API (free tier, no API key required) to fetch
company registration data for non-UK European companies.

Free tier provides: name, registration number, jurisdiction, status,
registered address, incorporation date, company type, officers.

Does NOT provide direct financial data (revenue, EBITDA) — that remains
the domain of the LLM enrichment agent for European companies.
"""
import logging
from typing import Dict, Any, Optional, List

import httpx

logger = logging.getLogger(__name__)

# OpenCorporates free API base
OC_API_BASE = "https://api.opencorporates.com/v0.4"

# Map ISO 3166-1 alpha-2 to OpenCorporates jurisdiction codes
JURISDICTION_MAP = {
    "FR": "fr",
    "DE": "de",
    "NL": "nl",
    "BE": "be",
    "LU": "lu",
    "ES": "es",
    "IT": "it",
    "AT": "at",
    "CH": "ch",
    "IE": "ie",
    "SE": "se",
    "DK": "dk",
    "NO": "no",
    "FI": "fi",
    "PL": "pl",
    "PT": "pt",
    "CZ": "cz",
}


class OpenCorporatesScraper:
    """
    Fetches European company data from OpenCorporates free API.
    
    Usage:
        scraper = OpenCorporatesScraper()
        results = await scraper.search_companies("Dassault Systemes", "FR")
        if results:
            profile = await scraper.get_company("fr", results[0]["company_number"])
    """
    
    def __init__(self, api_token: Optional[str] = None, timeout: float = 15.0):
        """
        Args:
            api_token: Optional API token for higher rate limits.
                       Free tier works without a token (~50 req/day).
            timeout: HTTP request timeout in seconds.
        """
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _build_params(self, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        params = {}
        if self.api_token:
            params["api_token"] = self.api_token
        if extra:
            params.update(extra)
        return params
    
    async def search_companies(
        self, 
        name: str, 
        country_code: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name in a specific jurisdiction.
        
        Args:
            name: Company name to search for.
            country_code: ISO 3166-1 alpha-2 country code (e.g., "FR").
            limit: Max results to return.
            
        Returns:
            List of company dicts with keys: company_number, name, jurisdiction,
            incorporation_date, company_type, current_status, registered_address.
        """
        jurisdiction = JURISDICTION_MAP.get(country_code.upper())
        if not jurisdiction:
            logger.debug(f"No OpenCorporates jurisdiction mapping for {country_code}")
            return []
        
        client = await self._get_client()
        url = f"{OC_API_BASE}/companies/search"
        params = self._build_params({
            "q": name,
            "jurisdiction_code": jurisdiction,
            "per_page": limit,
            "order": "score",
        })
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            companies = data.get("results", {}).get("companies", [])
            for item in companies:
                co = item.get("company", {})
                results.append({
                    "company_number": co.get("company_number"),
                    "name": co.get("name"),
                    "jurisdiction": co.get("jurisdiction_code"),
                    "incorporation_date": co.get("incorporation_date"),
                    "company_type": co.get("company_type"),
                    "current_status": co.get("current_status"),
                    "registered_address": co.get("registered_address_in_full"),
                    "opencorporates_url": co.get("opencorporates_url"),
                })
            
            logger.info(f"OpenCorporates: found {len(results)} matches for '{name}' in {jurisdiction}")
            return results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("OpenCorporates rate limit reached — free tier is ~50 req/day")
            else:
                logger.warning(f"OpenCorporates search failed ({e.response.status_code}): {e}")
            return []
        except Exception as e:
            logger.warning(f"OpenCorporates search error: {e}")
            return []
    
    async def get_company(
        self, 
        jurisdiction: str, 
        company_number: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get full company profile from OpenCorporates.
        
        Returns:
            Dict with company details, or None if not found.
        """
        client = await self._get_client()
        url = f"{OC_API_BASE}/companies/{jurisdiction}/{company_number}"
        params = self._build_params()
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            co = data.get("results", {}).get("company", {})
            return {
                "company_number": co.get("company_number"),
                "name": co.get("name"),
                "jurisdiction": co.get("jurisdiction_code"),
                "incorporation_date": co.get("incorporation_date"),
                "company_type": co.get("company_type"),
                "current_status": co.get("current_status"),
                "registered_address": co.get("registered_address_in_full"),
                "previous_names": [
                    pn.get("company_name", "") 
                    for pn in co.get("previous_names", [])
                ],
                "officers_count": len(co.get("officers", [])),
                "industry_codes": [
                    {
                        "code": ic.get("industry_code", {}).get("code"),
                        "description": ic.get("industry_code", {}).get("description"),
                        "scheme": ic.get("industry_code", {}).get("code_scheme_name"),
                    }
                    for ic in co.get("industry_codes", [])
                ],
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Company not found: {jurisdiction}/{company_number}")
            else:
                logger.warning(f"OpenCorporates get failed ({e.response.status_code}): {e}")
            return None
        except Exception as e:
            logger.warning(f"OpenCorporates get error: {e}")
            return None
    
    @staticmethod
    def estimate_company_size(officers_count: int) -> Optional[int]:
        """
        Rough employee estimate from officer count.
        
        Heuristic: officers typically represent ~1-5% of total workforce
        for SMEs. This is unreliable for large corps but provides a
        lower-bound signal for small companies.
        """
        if officers_count <= 0:
            return None
        if officers_count <= 3:
            return 15       # Micro/small company
        elif officers_count <= 10:
            return 50       # Small company
        elif officers_count <= 25:
            return 200      # Medium company
        else:
            return 500      # Large company


# Quick test
if __name__ == "__main__":
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        scraper = OpenCorporatesScraper()
        try:
            # Test French company search
            results = await scraper.search_companies("Dassault", "FR")
            for r in results[:3]:
                print(f"  {r['name']} ({r['company_number']}) - {r['current_status']}")
                
                # Get full profile
                if r['company_number'] and r['jurisdiction']:
                    profile = await scraper.get_company(r['jurisdiction'], r['company_number'])
                    if profile:
                        print(f"    Officers: {profile['officers_count']}")
                        print(f"    Est. employees: {scraper.estimate_company_size(profile['officers_count'])}")
                        print(f"    Industry: {profile['industry_codes']}")
        finally:
            await scraper.close()
    
    asyncio.run(main())

"""
Scraper for ISO certifications using UKAS CertCheck and Search Engines.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any

from playwright.async_api import Page

from src.core.data_types import ScraperOutput
from src.core.utils import clean_company_name
from src.core.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ISORegistryScraper(BaseScraper):
    """
    Scraper for UKAS CertCheck and general ISO discovery.
    """
    
    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    async def verify_company(self, company_name: str) -> Dict[str, Any]:
        """
        Verify if a company exists in UKAS CertCheck.
        """
        page = await self.context.new_page()
        try:
            await page.goto("https://certcheck.ukas.com/", wait_until="networkidle")
            
            # Note: UKAS CertCheck might have a specific search input ID. 
            # We would need to inspect the DOM. Assuming generic interaction for now.
            # This is a 'best effort' blind implementation without live DOM inspection.
            
            # Wait for input
            search_input = page.get_by_placeholder("Search by company name", exact=False)
            if await search_input.count() > 0:
                await search_input.first.fill(company_name)
                await search_input.first.press("Enter")
                await page.wait_for_timeout(2000)
                
                # Check results
                # logic to parse results
                content = await page.content()
                if "No results" in content:
                    return {"verified": False}
                else:
                    return {"verified": True, "details": "Match found"}
            
            return {"verified": False, "error": "Search input not found"}
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {"verified": False, "error": str(e)}
        finally:
            await page.close()

    async def scrape_iso9001(self) -> ScraperOutput:
        """
        Discover ISO 9001 companies via Search Engine scraping (since there is no open registry list).
        """
        logger.info("Discovering ISO 9001 companies via Search...")
        results = []
        
        page = await self.context.new_page()
        try:
            # Dork: site:*.co.uk "ISO 9001 certified" -intitle:jobs
            query = 'site:*.co.uk "ISO 9001 certified" -intitle:jobs'
            await page.goto(f"https://www.google.com/search?q={query}")
            await page.wait_for_timeout(2000)
            
            links = await page.locator(".g").all()
            for link in links:
                try:
                    title = await link.locator("h3").first.inner_text()
                    url_elem = link.locator("a").first
                    url = await url_elem.get_attribute("href")
                    
                    if url:
                         results.append({
                             "name": clean_company_name(title), # Heuristic: Title often contains company name
                             "source_url": url, 
                             "certification_type": "ISO 9001 (Detected)"
                         })
                except:
                    continue
                    
        finally:
            await page.close()

        return ScraperOutput(
            source="Search Engine Discovery",
            data_type="certification",
            data=results,
            row_count=len(results),
            metadata={"query": "ISO 9001"}
        )

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with ISORegistryScraper(headless=False) as scraper:
            res = await scraper.scrape_iso9001()
            print(f"Found {res.row_count} items")
            
    asyncio.run(main())

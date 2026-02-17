"""
Scraper for discovering companies in mainland Europe (France, Germany, Benelux).
Uses regional search dorks to identify technical businesses via certifications and registries.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page, Browser

from src.core.data_types import ScraperOutput
from src.core.utils import clean_company_name

logger = logging.getLogger(__name__)

class EuropeanDiscoveryScraper:
    """
    Discovers businesses in mainland Europe using regional keywords and domain-specific search.
    """
    
    REGIONS = {
        "FR": {
            "name": "France",
            "tld": "*.fr",
            "keywords": ['"certifié ISO"', '"société SIRENE"', '"expert technique"'],
            "registry": "SIRENE"
        },
        "DE": {
            "name": "Germany",
            "tld": "*.de",
            "keywords": ['"ISO zertifiziert"', '"Handelsregister B"', '"Maschinenbau"'],
            "registry": "Handelsregister"
        },
        "NL": {
            "name": "Netherlands",
            "tld": "*.nl",
            "keywords": ['"ISO gecertificeerd"', '"KVK inschrijving"', '"technisch bedrijf"'],
            "registry": "KVK"
        },
        "BE": {
            "name": "Belgium",
            "tld": "*.be",
            "keywords": ['"ISO gecertificeerd"', '"certifié ISO"', '"ondernemingsnummer"'],
            "registry": "KBO/CBE"
        },
        "LU": {
            "name": "Luxembourg",
            "tld": "*.lu",
            "keywords": ['"certifié ISO"', '"RCS Luxembourg"'],
            "registry": "LBR"
        }
    }

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def discover_region(self, country_code: str, limit: int = 10) -> ScraperOutput:
        """
        Discover companies in a specific region using search dorks.
        """
        region = self.REGIONS.get(country_code.upper())
        if not region:
            logger.error(f"Region {country_code} not supported.")
            return ScraperOutput(source="EU-Discovery", data_type="company", data=[], row_count=0)

        logger.info(f"Starting discovery for {region['name']}...")
        data = []
        
        page = await self.context.new_page()
        try:
            # Construct a dork: site:*.de "ISO zertifiziert"
            for kw in region['keywords'][:2]: # Just use first two keywords for demo
                query = f"site:{region['tld']} {kw}"
                # Use DuckDuckGo HTML to avoid bot detection/JS issues
                url = f"https://html.duckduckgo.com/html/?q={query}"
                
                await page.goto(url, wait_until="load", timeout=60000)
                await asyncio.sleep(2) 
                
                # DDG HTML selectors
                results = await page.locator(".result__body").all()
                for res in results[:limit]:
                    try:
                        title_elem = await res.locator(".result__a").first()
                        title = await title_elem.inner_text()
                        snippet_elem = await res.locator(".result__snippet").first()
                        snippet = await snippet_elem.inner_text() if await snippet_elem.count() > 0 else ""
                        
                        if title:
                            data.append({
                                "name": clean_company_name(title),
                                "hq_country": country_code.upper(),
                                "discovered_via": f"EU-Discovery ({region['registry']})",
                                "snippet": snippet
                            })
                    except:
                        continue
                
                if len(data) >= limit:
                    break
                    
        except Exception as e:
            logger.error(f"Discovery failed for {country_code}: {e}")
        finally:
            await page.close()

        return ScraperOutput(
            source=f"EU-Discovery-{country_code}",
            data_type="company",
            data=data,
            row_count=len(data),
            metadata={"country": country_code, "keywords": region['keywords']}
        )

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        async with EuropeanDiscoveryScraper(headless=True) as scraper:
            for code in ["FR", "DE", "NL"]:
                result = await scraper.discover_region(code, limit=5)
                print(f"\nResults for {code}:")
                for item in result.data:
                    print(f" - {item['name']}")

    asyncio.run(main())

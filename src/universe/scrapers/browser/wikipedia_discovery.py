"""
Scraper for identifying companies via Wikipedia categories.
Focuses on finding lists of companies by country/industry and extracting their official websites.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import re

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.core.data_types import ScraperOutput
from src.core.utils import clean_company_name

logger = logging.getLogger(__name__)

class WikipediaDiscoveryScraper:
    """
    Discovers companies by crawling Wikipedia categories and lists.
    """
    
    # Starting points for discovery
    BASE_URL = "https://en.wikipedia.org"
    
    CATEGORY_MAP = {
        "FR": [
            "/wiki/Category:Companies_of_France_by_industry",
            "/wiki/Category:Technology_companies_of_France",
            "/wiki/Category:Manufacturing_companies_of_France"
        ],
        "DE": [
            "/wiki/Category:Companies_of_Germany_by_industry",
            "/wiki/Category:Manufacturing_companies_of_Germany",
            "/wiki/Category:Technology_companies_of_Germany"
        ],
        "NL": [
            "/wiki/Category:Companies_of_the_Netherlands_by_industry"
        ],
        "BE": [
             "/wiki/Category:Companies_of_Belgium_by_industry"
        ]
    }

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.results = []

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        from src.core.config import settings
        ctx_kw = {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        if settings.ignore_ssl_errors:
            ctx_kw["ignore_https_errors"] = True
        self.context = await self.browser.new_context(**ctx_kw)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def discover_region(self, country_code: str, limit: int = 20) -> ScraperOutput:
        """
        Discover companies for a specific country code using Wikipedia.
        """
        code = country_code.upper()
        if code not in self.CATEGORY_MAP:
            logger.warning(f"No Wikipedia categories mapped for {code}")
            return ScraperOutput(source="Wikipedia", data=[], row_count=0)

        logger.info(f"Starting Wikipedia discovery for {code}...")
        
        discovered_data = []
        page = await self.context.new_page()
        
        try:
            # 1. Gather Candidate Pages from Categories
            candidate_links = []
            for category_path in self.CATEGORY_MAP[code]:
                url = self.BASE_URL + category_path
                links = await self._scrape_category_links(page, url)
                candidate_links.extend(links)
                
                # If we have enough candidates, break (but we need to deep scrape them)
                if len(candidate_links) > limit * 2: 
                    break
            
            # Deduplicate
            candidate_links = list({v['url']:v for v in candidate_links}.values())
            logger.info(f"Found {len(candidate_links)} candidate company pages for {code}")
            
            # 2. Visit Company Pages to get Website
            for item in candidate_links[:limit]:
                try:
                    details = await self._scrape_company_infobox(page, item['url'])
                    company_data = {
                        "name": clean_company_name(item['title']),
                        "hq_country": code,
                        "discovered_via": "Wikipedia",
                        "website": details.get("website"),
                        "description": details.get("description", f"Company found in Wikipedia category: {item['category']}")
                    }
                    discovered_data.append(company_data)
                    logger.info(f"Scraped {company_data['name']} -> {company_data['website']}")
                    
                    # Be polite
                    await asyncio.sleep(0.5) 
                    
                except Exception as e:
                    logger.warning(f"Failed to scrape detail for {item['title']}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Global Wiki Scrape failed: {e}")
        finally:
            await page.close()

        return ScraperOutput(
            source=f"Wikipedia-{code}",
            data_type="company",
            data=discovered_data,
            row_count=len(discovered_data),
            metadata={"country": code}
        )

    async def _scrape_category_links(self, page: Page, url: str) -> List[Dict[str, str]]:
        """
        Extract links to actual company pages from a category page.
        Identifies 'Pages in category' section.
        """
        await page.goto(url, wait_until="domcontentloaded")
        
        # Select links in the pages category div
        # typically #mw-pages .mw-category-group ul li a
        links = await page.locator("#mw-pages .mw-category-group ul li a").all()
        
        results = []
        category_name = url.split(":")[-1].replace("_", " ")
        
        for link in links:
            try:
                href = await link.get_attribute("href")
                title = await link.get_attribute("title")
                if href and title and not "Category:" in title:
                    results.append({
                        "url": self.BASE_URL + href,
                        "title": title,
                        "category": category_name
                    })
            except:
                continue
        return results

    async def _scrape_company_infobox(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Visit a company info page and extract website from infobox.
        """
        await page.goto(url, wait_until="domcontentloaded")
        
        details = {"website": None, "description": None}
        
        # 1. Get Description (First paragraph)
        try:
             first_p = await page.locator("#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)").first()
             details["description"] = await first_p.inner_text()
        except:
            pass

        # 2. Get Website from Infobox
        # Look for table.infobox tr th:text("Website") -> next td
        try:
            # Often rows have a header 'Website'
            # Use 'has-text' which is substring match, more robust than 'text-is'
            website_row = page.locator("table.infobox tr:has(th:has-text('Website'))")
            count = await website_row.count()
            if count > 0:
                link = website_row.locator("td a").first
                if await link.count() > 0:
                    details["website"] = await link.get_attribute("href")
                else:
                    logger.warning(f"Wiki: Found Website row for {url} but no link in td")
            else:
                 # Backup strategy: look for URL in any infobox row
                 logger.debug(f"Wiki: No 'Website' row found for {url}")
                 
        except Exception as e:
             logger.warning(f"Wiki infobox parse error for {url}: {e}")
             
        return details

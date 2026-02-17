import asyncio
import logging
from typing import List, Dict, Optional
import urllib.parse

from playwright.async_api import async_playwright
from src.core.data_types import ScraperOutput

logger = logging.getLogger(__name__)

class GoodFirmsDiscoveryScraper:
    """
    Scrapes GoodFirms.co for tech service companies.
    Handles bot protection via manual evasion and search-based navigation.
    """
    
    BASE_URL = "https://www.goodfirms.co"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        # Use existing Chrome installation if possible or bundled chromium
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def discover(self, term: str = "Software Development", country: str = "France", limit: int = 10) -> ScraperOutput:
        """
        Discover companies by searching on GoodFirms.
        Strategy: Go to Home -> Search -> Scrape Results.
        """
        logger.info(f"Starting GoodFirms discovery for '{term}' in '{country}'...")
        discovered_data = []
        
        page = await self.context.new_page()
        # Manual Evasion: Hide WebDriver property
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            # 1. Navigate to Homepage
            logger.info(f"Navigating to {self.BASE_URL}...")
            await page.goto(self.BASE_URL, wait_until="commit", timeout=45000)
            await asyncio.sleep(3)
            await page.wait_for_load_state("domcontentloaded")
            
            # Simple check for bot block
            title = await page.title()
            if "Just a moment" in title or "Access denied" in title:
                logger.error("Blocked by GoodFirms bot protection on homepage.")
                return ScraperOutput(source="GoodFirms", data=[])
                
            # 2. Search
            # Locate search input - Agent found .live-category-search in the banner
            search_input = page.locator("input.live-category-search, input[name='query']").first
            
            if await search_input.count() > 0:
                query = f"{term} {country}"
                logger.info(f"Searching for: {query}")
                await search_input.fill(query)
                await asyncio.sleep(1)
                
                # User feedback: "click the arrow to proceed"
                # Agent found: .banner-search-action
                search_btn = page.locator(".banner-search-action, button[class*='search']").first
                
                if await search_btn.count() > 0:
                    logger.info(f"Clicking search button: {await search_btn.get_attribute('class')}...")
                    # Force click via JS since element might be reported as hidden
                    # or covered by the input itself
                    try:
                        await search_btn.click(timeout=2000, force=True)
                    except:
                        logger.info("Standard click failed, trying JS click...")
                        await search_btn.evaluate("b => b.click()")
                else:
                    logger.info("Search button not found, pressing Enter...")
                    await search_input.press("Enter")
                
                await asyncio.sleep(5)
                await page.wait_for_load_state("domcontentloaded")
            else:
                logger.warning("Could not find search bar on GoodFirms homepage.")
                return ScraperOutput(source="GoodFirms", data_type="discovery", data=[])
            
            # 3. Scrape Results
            # Wait for listings
            try:
                # firm-wrapper-item is the specific item class seen in diagnostic
                await page.wait_for_selector(".firm-wrapper-item", timeout=15000)
            except:
                logger.warning("No results found or timed out waiting for listings.")
                await page.screenshot(path="data/debug/goodfirms_debug.png")
                
            cards = await page.locator(".firm-wrapper-item").all()
            # Fallback to older wrapper if new one fail
            if not cards:
                 cards = await page.locator(".firm-wrapper").all()
                 
            logger.info(f"Found {len(cards)} listings.")
            
            for i, card in enumerate(cards[:limit]):
                try:
                    # Name & Profile URL
                    name_el = card.locator("h3 a").first
                    if await name_el.count() == 0:
                        continue
                        
                    name = await name_el.inner_text()
                    profile_url = await name_el.get_attribute("href")
                    if profile_url and not profile_url.startswith("http"):
                        profile_url = self.BASE_URL + profile_url
                        
                    # Website Link (Direct!)
                    # GoodFirms often has a 'Visit Website' button with direct link + UTM
                    website = None
                    visit_btn = card.locator("a.visit-website").first
                    if await visit_btn.count() > 0:
                        raw_href = await visit_btn.get_attribute("href")
                        if raw_href:
                            website = raw_href
                            
                    item = {
                        "name": name.strip(),
                        "hq_country": country, # Derived from search context
                        "discovered_via": "GoodFirms",
                        "website": website,
                        "source_url": profile_url,
                        "description": f"Discovered via GoodFirms search for '{term}' in '{country}'"
                    }
                    
                    # Dedupe by website or name if needed upstream
                    discovered_data.append(item)
                    logger.info(f"Found: {name} ({website})")
                    
                except Exception as e:
                    logger.warning(f"Error processing card {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"GoodFirms scrape failed: {e}")
            await page.screenshot(path="data/debug/goodfirms_error.png")
        finally:
            await page.close()
            
        return ScraperOutput(source="GoodFirms", data_type="discovery", data=discovered_data)

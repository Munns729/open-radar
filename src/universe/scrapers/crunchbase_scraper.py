"""
Scraper for discovering companies via Crunchbase public search/listings.
"""
import asyncio
import logging
import random
import urllib.parse
from typing import List, Dict, Optional

from src.core.base_scraper import BaseScraper
from src.core.data_types import ScraperOutput
from src.core.utils import clean_company_name

logger = logging.getLogger(__name__)

class CrunchbaseDiscoveryScraper(BaseScraper):
    """
    Discovers companies by crawling Crunchbase public search results.
    
    Note: Crunchbase is very aggressive with anti-botting (Cloudflare).
    We use public search URLs and try to emulate human behavior.
    """
    
    BASE_URL = "https://www.crunchbase.com"
    
    # Map regions to Crunchbase location paths
    # These are illustrative - public search URLs change often
    REGION_MAP = {
        "UK": "United Kingdom",
        "FR": "France",
        "DE": "Germany",
        "NL": "Netherlands",
        "SE": "Sweden",
        "Europe": "Europe"
    }

    async def discover_companies(self, region_code: str = "Europe", limit: int = 15) -> ScraperOutput:
        """
        Discover companies in a specific region using Crunchbase public search.
        """
        region_name = self.REGION_MAP.get(region_code, region_code)
        
        # Construct a search URL that mimics a public search
        # Filtering by Revenue and Actively Hiring or similar if possible via URL params
        # For free tier, we often have to start with a broad search and filter manually
        # specific to "Software" and "Information Technology"
        
        # Example public search URL pattern (often changes, may need adjustment)
        # https://www.crunchbase.com/hub/europe-software-companies
        
        search_path = "/hub/europe-software-companies"
        if region_code == "UK":
            search_path = "/hub/united-kingdom-software-companies"
        elif region_code == "FR":
            search_path = "/hub/france-software-companies"
        elif region_code == "DE":
            search_path = "/hub/germany-software-companies"
            
        url = self.BASE_URL + search_path
        
        logger.info(f"Starting Crunchbase discovery for {region_name} at {url}...")
        
        discovered_data = []
        
        # Ensure context is ready
        if not self.context:
            await self.create_browser_context() # If inline
            
        page = await self.context.new_page()
        
        try:
            # 1. Navigate to Search Page
            success = await self.safe_goto_with_retry(page, url)
            if not success:
               logger.error(f"Failed to reach Crunchbase URL: {url}")
               return ScraperOutput(source="Crunchbase", data=[], row_count=0)

            # Wait for list to load
            try:
                # Crunchbase uses various selectors, often material-ui or custom
                # We look for the main grid or list
                await page.wait_for_selector('identifier-multi-formatter', timeout=15000)
            except:
                logger.warning("Timeout waiting for Crunchbase list. Capturing screenshot...")
                # await page.screenshot(path="debug_cb_fail.png")
                # Likely Cloudflare block or unexpected layout
                pass
                
            # 2. Extract Companies
            # Locate rows
            rows = await page.locator('grid-row').all()
            if not rows:
                 # Try alternative selector for different layouts
                 rows = await page.locator('tr.ng-star-inserted').all()
            
            logger.info(f"Found {len(rows)} potential rows on Crunchbase page.")
            
            for row in rows[:limit*2]: # Scrape more then filter
                if len(discovered_data) >= limit:
                    break
                    
                try:
                    # Name & Profile URL
                    name_el = row.locator('identifier-multi-formatter a').first
                    if await name_el.count() == 0:
                         continue
                         
                    name = (await name_el.inner_text()).strip()
                    profile_url = await name_el.get_attribute('href')
                    
                    if not profile_url:
                        continue
                        
                    if not profile_url.startswith("http"):
                        profile_url = self.BASE_URL + profile_url
                        
                    # Quick description/industry check
                    # Often in adjacent columns
                    desc_el = row.locator('column-description').first
                    description = ""
                    if await desc_el.count() > 0:
                        description = (await desc_el.inner_text()).strip()
                    
                    # Revenue/Financials are usually obscured/locked in free tier
                    # We rely on "Software" context of the Hub
                    
                    company_data = {
                        "name": clean_company_name(name),
                        "hq_country": region_code,
                        "discovered_via": "Crunchbase (Public Hub)",
                        "sector": "Software",
                        "description": description,
                        "source_url": profile_url,
                        # Website is often on profile, not list view in new UI
                        # We will skip deep profile scraping for now to avoid blocking
                        # The enrichment agent will find the website given the name/context
                    }
                    
                    # Basic exclusion
                    lower_desc = description.lower()
                    if "acquisition" in lower_desc or "acquired" in lower_desc:
                         # Skip acquired companies if obvious
                         pass
                    else:
                        discovered_data.append(company_data)
                        
                except Exception as e:
                    # logger.warning(f"Error parsing CB row: {e}")
                    continue
            
            logger.info(f"Extracted {len(discovered_data)} companies from Crunchbase.")

        except Exception as e:
            logger.error(f"Crunchbase Discovery failed: {e}")
            # await page.screenshot(path="debug_cb_error.png")
        finally:
            await page.close()
            
        return ScraperOutput(
            source=f"Crunchbase-{region_code}",
            data_type="company",
            data=discovered_data,
            row_count=len(discovered_data),
            metadata={"region": region_code}
        )

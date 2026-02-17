"""
Scraper for discovering companies via Clutch.co directories.
Focuses on "Tech Services", "IT Services", and "Development" verticals to find smaller/niche firms.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import random
import urllib.parse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.core.data_types import ScraperOutput
from src.core.utils import clean_company_name

logger = logging.getLogger(__name__)

class ClutchDiscoveryScraper:
    """
    Discovers companies by crawling Clutch.co listings.
    """
    
    BASE_URL = "https://clutch.co"
    
    # Map country codes to Clutch sub-paths
    # e.g. https://clutch.co/fr/it-services
    COUNTRY_MAP = {
        "FR": "/fr/it-services",
        "DE": "/de/it-services",
        "UK": "/uk/it-services",
        "NL": "/nl/it-services",
        "PL": "/pl/it-services" # Poland has many devs
    }

    def __init__(self, headless: bool = True):
        # Clutch often blocks headless, so we might need headless=False for debugging or advanced evasion
        # But let's try with our standard stealth context first
        self.headless = headless 
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def _extract_website_from_redirect(self, redirect_url: str) -> Optional[str]:
        """
        Extracts the actual provider website from a Clutch redirect URL.
        Example: https://r.clutch.co/redirect?...&provider_website=wearenotch.com&...
        """
        if not redirect_url:
            return None
        
        try:
            parsed = urllib.parse.urlparse(redirect_url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'provider_website' in params:
                domain = params['provider_website'][0]
                if not domain.startswith("http"):
                    return f"https://{domain}"
                return domain
        except Exception as e:
            logger.warning(f"Failed to parse Clutch redirect URL {redirect_url}: {e}")
            
        return None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def discover_tech_services(self, country_code: str, limit: int = 15) -> ScraperOutput:
        """
        Discover 'Tech Enabled Services' companies in a specific country.
        """
        code = country_code.upper()
        if code not in self.COUNTRY_MAP:
            logger.warning(f"No Clutch path mapped for {code}")
            return ScraperOutput(source="Clutch", data=[], row_count=0)

        path = self.COUNTRY_MAP[code]
        url = self.BASE_URL + path
        
        logger.info(f"Starting Clutch discovery for {code} at {url}...")
        
        discovered_data = []
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await asyncio.sleep(5) # Let JS settle / anti-bot
            
            # 1. Gather Listings
            # Listings are typically .provider-row
            # Gather unique h3 links first
            h3_links = await page.locator("h3 a").all()
            unique_links = []
            seen_hrefs = set()
            
            for link in h3_links:
                href = await link.get_attribute("href")
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_links.append(link)
            
            logger.info(f"Found {len(unique_links)} unique listings on Clutch page.")
            
            for name_link in unique_links[:limit]:
                try:
                    name = await name_link.inner_text()
                    profile_url = await name_link.get_attribute("href")
                    
                    if not profile_url:
                        continue
                        
                    # Find the container listing item (usually an li) using robust relative xpath
                    item = name_link.locator("xpath=./ancestor::li").first
                    
                    if not profile_url.startswith("http"):
                        profile_url = self.BASE_URL + profile_url
                        
                    # Exhaustive check of all links in the container for a redirect
                    website = None
                    if item and await item.count() > 0:
                        all_item_links = await item.locator("a").all()
                        for l in all_item_links:
                            l_href = await l.get_attribute("href")
                            if l_href and ("r.clutch.co/redirect" in l_href or "provider_website=" in l_href):
                                website = await self._extract_website_from_redirect(l_href)
                                if website:
                                    break
                    else:
                        logger.warning(f"Could not find container li for {name}")
                    
                    if website:
                        logger.info(f"Extracted website during directory scan for {name}: {website}")

                    # Add to list
                    company_data = {
                        "name": clean_company_name(name.strip()),
                        "hq_country": code,
                        "discovered_via": "Clutch (Tech Services)",
                        "sector": "Technology Services",
                        "description": f"Discovered on Clutch.co {code} IT Services list.",
                        "website": website,
                        "source_url": profile_url
                    }
                    
                    discovered_data.append(company_data)
                    # logger.info(f"Found {company_data['name']}")
                    
                except Exception as e:
                    # logger.warning(f"Error parsing Clutch item: {e}")
                    continue
            
            # 3. Visit Profiles for Websites (Batched/Slowly) to succeed
            # If we didn't get a clean website, let's try visiting a few
            # (Limit to 5 deep scrapes per run to stay under radar?)
            # Actually, let's return what we have. The Enrichment step will try to find the site via Search/Clearbit/etc.
            # *However*, our Search is fragile. 
            # Let's try to grab the website from the profile if we can.
            
            for company in discovered_data:
                # If we already got the website from the directory page (sponsors), skip profile visit
                if company.get("website"):
                    logger.info(f"Skipping profile visit for {company['name']} (Website already found)")
                    continue
                
                profile_url = company.get("source_url")
                if not profile_url:
                    continue

                # Use a fresh page for each profile to avoid 'interrupted navigation' errors
                profile_page = await self.context.new_page()
                try:
                    logger.info(f"Visiting Clutch profile for {company['name']}...")
                    response = await profile_page.goto(profile_url, wait_until="load", timeout=45000)
                    await asyncio.sleep(5)
                    
                    current_url = profile_page.url
                    # If we were redirected off Clutch (check domain, not full url string due to utm params)
                    parsed_url = urllib.parse.urlparse(current_url)
                    if "clutch.co" not in parsed_url.netloc:
                        company["website"] = current_url
                        logger.info(f"Successfully captured website via redirect for {company['name']}: {current_url}")
                        continue

                    title = await profile_page.title()
                    logger.info(f"Page Title: {title} | URL: {current_url}")
                    
                    # Brute force: Scan all links like the debug script did
                    links = await profile_page.locator("a").all()
                    logger.info(f"Found {len(links)} links on profile page.")
                    website = None
                    
                    for l in links:
                        try:
                            text = (await l.inner_text() or "").strip()
                            aria = (await l.get_attribute("aria-label") or "").strip()
                            cls = (await l.get_attribute("class") or "").strip()
                            href = (await l.get_attribute("href") or "").strip()
                            
                            if "Visit" in text or "Visit" in aria or "website" in cls or "redirect" in href:
                                if href and ("r.clutch.co/redirect" in href or "provider_website=" in href):
                                    website = await self._extract_website_from_redirect(href)
                                    if website:
                                        break
                                elif href and "clutch.co" not in href and href.startswith("http"):
                                    website = href
                                    break
                        except:
                            continue
                    
                    if website:
                        company["website"] = website
                        logger.info(f"Successfully extracted website for {company['name']}: {website}")
                    else:
                        logger.warning(f"No website link found on Clutch profile for {company['name']}")
                except Exception as e:
                    # Check if we were redirected to a direct site even on exception
                    current_url = profile_page.url
                    parsed_url = urllib.parse.urlparse(current_url)
                    if "clutch.co" not in parsed_url.netloc:
                        company["website"] = current_url
                        logger.info(f"Captured website after navigation error/redirect: {current_url}")
                    else:
                        logger.warning(f"Error scraping Clutch profile for {company['name']}: {e}")
                finally:
                    await profile_page.close()
                    await asyncio.sleep(random.uniform(2, 4)) # Evasion delay

        except Exception as e:
            logger.error(f"Clutch Discovery failed: {e}")
        finally:
            await page.close()

        return ScraperOutput(
            source=f"Clutch-{code}",
            data_type="company",
            data=discovered_data,
            row_count=len(discovered_data),
            metadata={"country": code}
        )

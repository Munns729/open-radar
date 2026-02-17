"""LinkedIn Scraper using Playwright"""
import asyncio
import logging
import base64
import time
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page, BrowserContext, Browser

from src.core.config import settings
from src.core.data_types import ScraperOutput

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_dir = settings.data_dir / "linkedin_session"
        self.screenshots: List[str] = []  # List of base64 strings

    async def setup_session(self):
        """Initialize Playwright and load session"""
        self.playwright = await async_playwright().start()
        
        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        launch_args = {
            "headless": self.headless,
            "args": ["--start-maximized"]  # Start maximized
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        # Load storage state if it exists
        storage_state_path = self.session_dir / "storage_state.json"
        
        if storage_state_path.exists():
            logger.info("Loading existing session...")
            self.context = await self.browser.new_context(
                storage_state=str(storage_state_path),
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        else:
            logger.info("Starting new session...")
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
        self.page = await self.context.new_page()
        
        # Go to LinkedIn to check login status
        await self.page.goto("https://www.linkedin.com/feed/")
        await asyncio.sleep(2)  # Wait for load checking

    async def check_session_validity(self) -> bool:
        """Check if the current session is valid (logged in)"""
        if not self.page:
            return False
            
        try:
            logger.info("Checking session validity...")
            # Navigate to feed if not already there
            if "feed" not in self.page.url:
                await self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                await asyncio.sleep(3)

            # Check for common logged-in elements (nav bar, profile icon, etc.)
            # A simple check is to see if we are redirected to login/signup
            if "login" in self.page.url or "signup" in self.page.url:
                logger.warning("Session appears invalid: redirected to login/signup.")
                return False
                
            # Stronger check: Look for the global nav
            nav_visible = await self.page.locator(".global-nav__content").is_visible()
            if nav_visible:
                 logger.info("Session is valid.")
                 return True
                 
            # Fallback check for feed container
            feed_visible = await self.page.locator(".scaffold-layout__main").is_visible()
            if feed_visible:
                logger.info("Session is valid (feed visible).")
                return True

            logger.warning("Session might be invalid: nav/feed not found.")
            return False
            
        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False

    async def login(self):
        """
        Attempt to login using saved session. 
        If valid, proceed.
        If invalid and headless, RAISE ERROR.
        If invalid and NOT headless, prompt manual login.
        """
        if not self.page:
            raise RuntimeError("Session not setup. Call setup_session() first.")

        # 1. Check if we are already logged in via session
        if await self.check_session_validity():
            logger.info("Successfully resumed session.")
            return

        # 2. If not logged in and headless, we can't do anything
        if self.headless:
            logger.error("Session invalid and running in headless mode. Cannot login manually.")
            # Take a screenshot for debugging
            try:
                await self.page.screenshot(path="login_failed_headless.png")
            except: 
                pass
            raise RuntimeError("LinkedIn session expired or invalid. Please run with headless=False to re-authenticate manually.")

        # 3. Manual Login Flow
        logger.info("Session invalid/missing. Please login manually in the browser window...")
        
        # Check if we are on the login page or feed
        if "login" in self.page.url or "signup" in self.page.url or "guest" in self.page.url:
             logger.info("Waiting for user to login...")
             # Wait until we see the feed or a specific element that indicates logged in state
             try:
                 # 5 minutes to login
                 await self.page.wait_for_url("**/feed/**", timeout=300000) 
                 logger.info("Login detected!")
                 
                 # Wait a bit for cookies to set
                 await asyncio.sleep(3)
                 await self.save_session()
                 
             except Exception as e:
                 logger.error(f"Login timed out or failed: {e}")
                 raise RuntimeError("Manual login timed out") from e
        else:
            # Maybe we are on some other page? Redirect to login to be safe?
            # Or assume we are just lost?
            logger.info("Already logged in or unknown state. Saving session just in case.")
            await self.save_session()

    async def save_session(self):
        """Save browser session"""
        if self.context:
            await self.context.storage_state(path=str(self.session_dir / "storage_state.json"))
            logger.info("Session saved.")

    async def scrape_feed(self, scrolls: int = 30) -> ScraperOutput:
        """Scroll feed and capture screenshots"""
        if not self.page:
            raise RuntimeError("Session not setup")

        logger.info(f"Starting feed scrape ({scrolls} scrolls)...")
        
        if "feed" not in self.page.url:
            await self.page.goto("https://www.linkedin.com/feed/")
            await self.page.wait_for_load_state("networkidle")

        self.screenshots = []
        
        try:
            for i in range(scrolls):
                # Scroll down
                await self.page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)  # Rate limit & wait for render
                
                # Take screenshot of the viewport
                # We save as base64 to pass to AI directly
                screenshot_bytes = await self.page.screenshot(
                    type='jpeg',
                    quality=70,
                    full_page=False
                )
                
                # Convert to base64
                b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
                self.screenshots.append(b64_img)
                
                # Print progress
                if (i + 1) % 5 == 0:
                    logger.info(f"Scrolled {i + 1}/{scrolls} times")
                    
                # Random jitter to look human
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            
        return ScraperOutput(
            source="linkedin_feed",
            data_type="screenshots_base64",
            data=[{"image": img} for img in self.screenshots],
            metadata={"scroll_count": scrolls, "image_count": len(self.screenshots)}
        )

    async def follow_company(self, company_name: str):
        """Search for a company and follow it"""
        if not self.page:
            return
            
        logger.info(f"Searching for {company_name}...")
        try:
            # Search for company
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={company_name}"
            await self.page.goto(search_url)
            
            # networkidle is too flaky on LinkedIn, use domcontentloaded + fixed wait for hydration
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3) 

            # Try to find the first search result's interaction button
            # Search results are usually in a list. We target the "Follow" button specifically.
            # Using a more permissive selector logic
            
            # 1. Look for a button with exact text "Follow"
            follow_btn = self.page.locator("button", has_text="Follow").first
            
            # 2. Check if we are already following (button says "Following")
            following_btn = self.page.locator("button", has_text="Following").first
            
            if await following_btn.is_visible():
                 logger.info(f"Already following {company_name}")
                 return

            if await follow_btn.is_visible():
                await follow_btn.click()
                logger.info(f"Clicked Follow for {company_name}")
            else:
                # Fallback: Sometimes it is "Follow + name" or icon
                # Let's try to find the primary action button in the first entity result
                logger.warning(f"Standard 'Follow' button not found for {company_name}. functionality might be restricted or UI changed.")
                
        except Exception as e:
            logger.error(f"Error following {company_name}: {e}")

    async def get_employee_count(self, company_name: str) -> Optional[int]:
        """
        Search for company and extract employee count from header.
        """
        if not self.page:
            return None
            
        logger.info(f"Getting employee count for {company_name}...")
        try:
            # 1. Search for company
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={company_name}"
            await self.page.goto(search_url)
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            # 2. Click first result
            # We want the main link to the company page
            first_result = self.page.locator(".search-results-container .entity-result__title-text a").first
            if not await first_result.is_visible():
                logger.warning(f"No company results found for {company_name}")
                return None
                
            await first_result.click()
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            # 3. Extract logic
            # Look for "See all X employees on LinkedIn" link usually in the hero or about section
            # Pattern: "See all 1,234 employees on LinkedIn"
            
            # Try multiple selectors
            count = None
            
            # Selector A: The link in the hero
            employee_link = self.page.locator("a[href*='/people/']", has_text="employees").first
            if await employee_link.is_visible():
                text = await employee_link.inner_text() # e.g. "See all 42 employees on LinkedIn"
                count = self._parse_employee_text(text)
                
            # Selector B: Check 'About' tab if A fails
            if not count:
                # Go to About tab
                current_url = self.page.url
                if "/about" not in current_url:
                    if current_url.endswith("/"):
                        about_url = current_url + "about/"
                    else:
                        about_url = current_url + "/about/"
                    await self.page.goto(about_url)
                    await self.page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(2)
                    
                # Look for dl/dt/dd structure in About
                # Often "Company size" -> "11-50 employees" (Band)
                # Or "associated members" -> "123"
                
                # We prioritize exact match from the People link if available on About page too
                employee_link = self.page.locator("a[href*='/people/']", has_text="employees").first
                if await employee_link.is_visible():
                    text = await employee_link.inner_text()
                    count = self._parse_employee_text(text)
            
            if count:
                logger.info(f"Found {count} employees for {company_name}")
                return count
                
            logger.warning(f"Could not extract employee count for {company_name}")
            return None

        except Exception as e:
            logger.error(f"Error getting employee count for {company_name}: {e}")
            return None

    def _parse_employee_text(self, text: str) -> Optional[int]:
        """Extract number from string like 'See all 1,234 employees'"""
        import re
        try:
            # Remove commas
            clean_text = text.replace(",", "")
            # Find integer
            match = re.search(r'(\d+)', clean_text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None


    async def close(self):
        """Cleanup resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Scraper closed.")


if __name__ == "__main__":
    # Test run
    async def main():
        scraper = LinkedInScraper(headless=False)
        await scraper.setup_session()
        await scraper.login_manual()
        output = await scraper.scrape_feed(scrolls=5)
        print(f"Captured {len(output.data)} screenshots")
        await scraper.close()
        
    asyncio.run(main())

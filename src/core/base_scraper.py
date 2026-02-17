"""
Base Scraper class for all Playwright-based scrapers in RADAR.
Provides shared browser lifecycle management, user agent rotation, 
safe navigation, and retry logic.
"""
import asyncio
import logging
import random
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

# Realistic user agents for anti-detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class BaseScraper:
    """
    Base class for all Playwright-based scrapers.
    
    Provides:
    - Browser lifecycle management (async context manager)
    - Randomized user agent selection
    - Safe navigation with retry logic
    - Common page helpers
    
    Usage as context manager:
        async with MyScraper(headless=True) as scraper:
            result = await scraper.scrape(...)
    
    Usage inline (for scrapers that manage browser per-method):
        scraper = MyScraper()
        browser, context, page = await scraper.create_browser_context()
        try:
            ...
        finally:
            await scraper.close_browser_context(context, browser)
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    def _get_user_agent(self) -> str:
        """Return a random realistic user agent string."""
        return random.choice(USER_AGENTS)

    # --- Context Manager Pattern (persistent browser) ---

    async def __aenter__(self):
        """Start Playwright, launch browser, create context."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = await self.browser.new_context(
            user_agent=self._get_user_agent(),
            viewport={"width": 1280, "height": 800},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # --- Inline Pattern (browser per-method) ---

    async def create_browser_context(self) -> tuple[Browser, BrowserContext, Page]:
        """
        Create a fresh browser context for scrapers that manage browser per-method.
        Caller is responsible for cleanup via close_browser_context().
        """
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=self._get_user_agent(),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        # Stash playwright ref on browser for cleanup
        browser._playwright_ref = pw
        return browser, context, page

    async def close_browser_context(self, context: BrowserContext, browser: Browser):
        """Close a browser context created by create_browser_context()."""
        try:
            await context.close()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass
        try:
            pw = getattr(browser, '_playwright_ref', None)
            if pw:
                await pw.stop()
        except Exception:
            pass

    # --- Common Helpers ---

    async def safe_goto(self, page: Page, url: str, timeout: int = 30000, wait_until: str = "domcontentloaded") -> bool:
        """
        Navigate to a URL with error handling and human-like delay.
        Returns True on success, False on failure.
        """
        try:
            await page.goto(url, timeout=timeout, wait_until=wait_until)
            await asyncio.sleep(random.uniform(1.0, 2.5))  # Human-like pause
            return True
        except Exception as e:
            logger.warning(f"Failed to load {url}: {e}")
            return False

    async def safe_goto_with_retry(self, page: Page, url: str, retries: int = 2, timeout: int = 30000) -> bool:
        """
        Navigate to a URL with retry logic and exponential backoff.
        """
        for attempt in range(retries + 1):
            success = await self.safe_goto(page, url, timeout=timeout)
            if success:
                return True
            if attempt < retries:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.info(f"Retrying {url} in {wait:.1f}s (attempt {attempt + 2}/{retries + 1})")
                await asyncio.sleep(wait)
        return False

"""
Shared bases for scrapers (Playwright and API).

- BaseScraper: Playwright lifecycle, safe_goto, retry.
- ApiScraper: aiohttp session, rate limiting, _get / _post with retry and 429 handling.

Used by universe scrapers and by other modules (e.g. carveout) that need browser-based scraping.
"""
import asyncio
import logging
import random
from typing import Any, Dict, Optional

import aiohttp
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)

# Realistic user agents for anti-detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

__all__ = ["BaseScraper", "ApiScraper"]


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
        from src.core.config import settings
        ctx_kw = {"user_agent": self._get_user_agent(), "viewport": {"width": 1280, "height": 800}}
        if settings.ignore_ssl_errors:
            ctx_kw["ignore_https_errors"] = True
        self.context = await self.browser.new_context(**ctx_kw)
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
        from src.core.config import settings
        ctx_kw = {"user_agent": self._get_user_agent(), "viewport": {"width": 1280, "height": 800}}
        if settings.ignore_ssl_errors:
            ctx_kw["ignore_https_errors"] = True
        context = await browser.new_context(**ctx_kw)
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


class ApiScraper:
    """
    Base for scrapers that call REST/JSON APIs with aiohttp.

    Subclasses set BASE_URL and optionally override default_headers or pass auth.
    Use as async context manager:

        async with MyApiScraper() as scraper:
            data = await scraper._get("/path")
    """

    BASE_URL: str = ""

    def __init__(
        self,
        rate_limit_delay: float = 0.5,
        auth: Optional[aiohttp.BasicAuth] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.rate_limit_delay = rate_limit_delay
        self._auth = auth
        self._headers = headers or {"Accept": "application/json"}
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        kwargs: Dict[str, Any] = {"headers": self._headers}
        if self._auth is not None:
            kwargs["auth"] = self._auth
        self.session = aiohttp.ClientSession(**kwargs)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None
        return False

    async def _rate_limit(self) -> None:
        await asyncio.sleep(self.rate_limit_delay)

    def _full_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http"):
            return path_or_url
        base = (self.BASE_URL or "").rstrip("/")
        path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
        return f"{base}{path}"

    async def _get(
        self,
        path_or_url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        GET request; returns JSON or None. Retries on 429 (waits 60s) and on failure.
        """
        if not self.session:
            raise RuntimeError("Scraper context not entered.")
        url = self._full_url(path_or_url)

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 404:
                        logger.debug(f"404 for {path_or_url}")
                        return None
                    if response.status == 429:
                        logger.warning(
                            f"Rate limited. Waiting 60s. Attempt {attempt + 1}/3"
                        )
                        await asyncio.sleep(60)
                        continue
                    text = await response.text()
                    logger.error(f"GET {url} -> {response.status}: {text[:300]}")
                    return None
            except Exception as e:
                logger.error(f"GET {url} failed: {e}")
                await asyncio.sleep(1)
        return None

    async def _get_text(
        self,
        path_or_url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        GET request; returns response text (e.g. HTML) or None. Same retry/429 logic.
        """
        if not self.session:
            raise RuntimeError("Scraper context not entered.")
        url = self._full_url(path_or_url)

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    if response.status == 429:
                        logger.warning(
                            f"Rate limited. Waiting 60s. Attempt {attempt + 1}/3"
                        )
                        await asyncio.sleep(60)
                        continue
                    logger.error(f"GET {url} -> {response.status}")
                    return None
            except Exception as e:
                logger.error(f"GET {url} failed: {e}")
                await asyncio.sleep(2)
        return None

    async def _post(
        self,
        path_or_url: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        POST request (JSON body); returns JSON or None. Same retry/429 logic.
        """
        if not self.session:
            raise RuntimeError("Scraper context not entered.")
        url = self._full_url(path_or_url)

        for attempt in range(3):
            try:
                await self._rate_limit()
                async with self.session.post(
                    url, json=json or {}, timeout=30
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 429:
                        logger.warning(
                            f"Rate limited. Waiting 60s. Attempt {attempt + 1}/3"
                        )
                        await asyncio.sleep(60)
                        continue
                    text = await response.text()
                    logger.error(f"POST {url} -> {response.status}: {text[:300]}")
                    return None
            except Exception as e:
                logger.error(f"POST {url} failed: {e}")
                await asyncio.sleep(2)
        return None

"""
Website Scraper for Descriptive Content and Keyword Analysis.
Robust version with timeout handling and multiple fallback strategies.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from src.universe.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class WebsiteScraper(BaseScraper):
    """
    Scrapes company homepage for Description and Moat Keywords.
    Uses multiple fallback strategies to ensure content extraction.
    """
    
    MOAT_KEYWORDS = {
        "regulatory": ["certified", "compliance", "regulatory", "audit", "mandated", "standard", "accredited", "approved"],
        "network": ["marketplace", "platform", "connects", "community", "ecosystem", "exchange", "network", "aggregator", "booking"],
        "physical": ["installation", "on-site", "manufacturing", "facility", "hardware", "maintenance", "service", "embedded"],
        "liability": ["testing", "inspection", "assurance", "audit", "certification", "quality", "verification", "laboratory"]
    }

    # Short timeout for individual element lookups (ms)
    ELEMENT_TIMEOUT = 3000
    
    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    async def _safe_get_text(self, page: Page, selector: str, attribute: Optional[str] = None) -> Optional[str]:
        """
        Safely attempt to get text/attribute from a selector with timeout.
        Returns None if element not found or timeout.
        """
        try:
            locator = page.locator(selector).first
            if attribute:
                result = await locator.get_attribute(attribute, timeout=self.ELEMENT_TIMEOUT)
            else:
                result = await locator.inner_text(timeout=self.ELEMENT_TIMEOUT)
            return result.strip() if result else None
        except (PlaywrightTimeout, Exception):
            return None

    async def _extract_description(self, page: Page) -> str:
        """
        Extract description using multiple fallback strategies.
        Priority: meta description > og:description > twitter:description > title + H1 > first paragraph
        """
        # Strategy 1: Meta description
        desc = await self._safe_get_text(page, "meta[name='description']", "content")
        if desc and len(desc) > 20:
            return desc
        
        # Strategy 2: Open Graph description
        desc = await self._safe_get_text(page, "meta[property='og:description']", "content")
        if desc and len(desc) > 20:
            return desc
        
        # Strategy 3: Twitter description
        desc = await self._safe_get_text(page, "meta[name='twitter:description']", "content")
        if desc and len(desc) > 20:
            return desc
        
        # Strategy 4: Title tag
        title = await self._safe_get_text(page, "title")
        
        # Strategy 5: H1 heading
        h1 = await self._safe_get_text(page, "h1")
        
        # Strategy 6: First meaningful paragraph
        # Try multiple selectors for main content area
        paragraph = None
        for selector in ["main p", "article p", ".content p", "#content p", "p"]:
            paragraph = await self._safe_get_text(page, selector)
            if paragraph and len(paragraph) > 30:
                break
        
        # Combine available elements
        parts = []
        if title:
            parts.append(title)
        if h1 and h1 != title:
            parts.append(h1)
        if paragraph:
            parts.append(paragraph[:200])
        
        if parts:
            return " | ".join(parts)[:400]
        
        return ""

    async def _find_nav_links(self, page: Page, base_url: str) -> list[str]:
        """
        Find relevant navigation links (About, Certifications, Technology, etc.)
        """
        relevant_keywords = [
            "about", "who we are", "company", # Identity
            "certification", "accreditation", "quality", "standards", # Regulatory
            "technology", "product", "platform", "solution", # Tech/Product
            "partners", "clients", "customers" # Network
        ]
        
        visited_urls = set()
        to_visit = []
        
        try:
            # Get all links
            links = await page.get_by_role("link").all()

            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    
                    if not href or not text:
                        continue
                        
                    text_lower = text.lower().strip()
                    href_lower = href.lower()
                    
                    # Check if relevant
                    is_relevant = any(kw in text_lower for kw in relevant_keywords)
                    
                    # Prepare full URL
                    if href.startswith("/"):
                        if base_url.endswith("/"):
                            full_url = base_url[:-1] + href
                        else:
                            full_url = base_url + href
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        continue
                        
                    # Filter valid internal links only
                    if base_url in full_url and full_url not in visited_urls and is_relevant:
                        # Avoid duplicates
                        if any(u['url'] == full_url for u in to_visit):
                            continue
                            
                        to_visit.append({"url": full_url, "text": text_lower})
                        visited_urls.add(full_url)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error finding nav links: {e}")
            
        # Prioritize certifications and technology
        to_visit.sort(key=lambda x: 0 if "cert" in x["text"] or "tech" in x["text"] else 1)
        
        return [item["url"] for item in to_visit[:3]] # Limit to top 3

    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrape homepage and key sub-pages for comprehensive moat analysis.
        """
        logger.info(f"Deep Scraping {url}...")
        print(f"[FLOW] Hand-off -> Browser Agent (Playwright/Stealth): {url}")
        
        result = {
            "description": None,
            "keywords_found": {k: False for k in self.MOAT_KEYWORDS},
            "raw_text": ""
        }
        
        browser, context, page = await self.create_browser_context()

        try:
            # 1. Homepage
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            # Extract Description & Basic Metadata
            print("[FLOW] Analyzing HTML Structure (Static + Dynamic)...")
            result["description"] = await self._extract_description(page)

            # Extract Homepage Text
            texts = []
            try:
                home_text = await page.inner_text("body", timeout=5000)
                texts.append(f"--- HOMEPAGE ---\n{home_text[:5000]}")
            except:
                pass

            # 2. Deep Dive: Find and Visit Sub-pages
            try:
                sub_pages = await self._find_nav_links(page, url)
                logger.info(f"Found sub-pages to visit: {sub_pages}")
                if sub_pages:
                    print(f"[FLOW] Agent Strategy: Deep Dive -> Visiting {len(sub_pages)} sub-pages for context")

                for sub_url in sub_pages:
                    try:
                        logger.info(f"Visiting {sub_url}...")
                        await page.goto(sub_url, timeout=15000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(1000) # Wait for hydration

                        sub_text = await page.inner_text("body", timeout=5000)
                        header = f"--- {sub_url.split('/')[-1].upper()} ---"
                        texts.append(f"{header}\n{sub_text[:8000]}") # 8k chars per subpage

                    except Exception as e:
                        logger.warning(f"Failed to scrape sub-page {sub_url}: {e}")

            except Exception as e:
                logger.warning(f"Deep scraping navigation failed: {e}")

            # 3. Compile Result
            full_text = "\n\n".join(texts)
            result["raw_text"] = full_text[:30000] # Cap at 30k chars

            # Check keywords in full text
            text_lower = full_text.lower()
            for category, keywords in self.MOAT_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower:
                        result["keywords_found"][category] = True
                        break

        except PlaywrightTimeout:
            logger.warning(f"Page load timeout for {url}, returning partial data")
            print(f"[FLOW] Fail (Timeout/403) -> {url}")

        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            print(f"[FLOW] Fail (Error) -> {url}. Returning Partial Data.")

        finally:
            await self.close_browser_context(context, browser)

        return result

if __name__ == "__main__":
    async def main():
        scraper = WebsiteScraper(headless=False)
        # Test with a site that has sub-pages
        res = await scraper.scrape("https://www.oxinst.com") # Oxford Instruments (Technical)
        print(f"Description: {res['description']}")
        print(f"Text Length: {len(res['raw_text'])}")
        print(f"Keywords: {res['keywords_found']}")
            
    asyncio.run(main())

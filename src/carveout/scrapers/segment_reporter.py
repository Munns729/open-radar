"""
Segment Report Scraper using Playwright.
Focus: European Annual Reports (LSE, Euronext, DB).
"""
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page, BrowserContext
from datetime import datetime

from src.core.base_scraper import BaseScraper

class SegmentReportScraper(BaseScraper):
    """Scrapes annual reports and extracts segment data."""
    
    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    async def scrape_company_segments(self, ticker: str, exchange: str = "LSE") -> List[Dict]:
        """
        Main entry point to find and parse segment data for a company.
        """
        browser, context, page = await self.create_browser_context()
            
        try:
            # 1. Find IR Page
            ir_url = await self._find_ir_page(page, ticker, exchange)
            if not ir_url:
                print(f"Could not find IR page for {ticker}")
                return []
            
            # 2. Find latest Annual Report URL
            report_url = await self._find_annual_report(page, ir_url)
            if not report_url:
                print(f"Could not find annual report for {ticker}")
                return []
            
            print(f"Index report found at: {report_url} for {ticker}")

            # 3. Download/Parse Report (Simulated extraction for now)
            segments = await self._simulate_segment_extraction(ticker, report_url)
            
            return segments

        except Exception as e:
            print(f"Error scraping {ticker}: {e}")
            return []
        finally:
            await self.close_browser_context(context, browser)

    async def _find_ir_page(self, page: Page, ticker: str, exchange: str) -> Optional[str]:
        """Search Bing (often easier for bots) for the IR page."""
        # Fallback for testing to avoid search engine blocks
        known_urls = {
            "BARC": "https://home.barclays/investor-relations/",
            "HSBA": "https://www.hsbc.com/investors"
        }
        if ticker in known_urls:
            return known_urls[ticker]

        query = f"{ticker} {exchange} investor relations annual report"
        await page.goto(f"https://www.bing.com/search?q={query}")
        
        # Bing organic results often have class 'b_algo' with an 'h2 a' inside
        try:
            await page.wait_for_selector("li.b_algo h2 a", timeout=10000)
            first_result = await page.query_selector("li.b_algo h2 a")
            if first_result:
                return await first_result.get_attribute("href")
        except:
             print("Could not find results on Bing")
             
        return None

    async def _find_annual_report(self, page: Page, ir_url: str) -> Optional[str]:
        """Navigate IR page to find latest annual report."""
        await page.goto(ir_url)
        # Heuristic to find report links
        # Look for "Annual Report 2025", "2024", "Results", etc.
        # This is a simplification.
        
        # Check for PDF links with "annual report" in text
        links = await page.query_selector_all("a")
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if text and "annual report" in text.lower() and href and href.endswith(".pdf"):
                 return href
        return ir_url # Return IR page if specific PDF not found, maybe it is HTML

    async def _simulate_segment_extraction(self, ticker: str, report_url: str) -> List[Dict]:
        """
        Mock extraction of segment data. 
        In production, this would use a PDF parser (PyPDF2, pdfplumber) or HTML parser.
        """
        # Mock data return
        return [
            {
                "division_name": "Core Banking",
                "revenue_eur": 500000000,
                "ebitda_eur": 120000000,
                "ebitda_margin": 24.0,
                "description": "Main banking operations."
            },
            {
                "division_name": "Legacy Insurance",
                "revenue_eur": 50000000,
                "ebitda_eur": 2000000,
                "ebitda_margin": 4.0,
                "description": "Run-off insurance book.", # Low margin, potential carveout
            }
        ]

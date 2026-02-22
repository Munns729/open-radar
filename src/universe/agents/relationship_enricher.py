"""
Relationship Enricher Agent.
Identifies Customers, Suppliers, and Partners using Website Analysis and Web Search.
Uses Google (not DuckDuckGo) — DDG rate-limits Playwright more aggressively (~15 reqs).

Status: planned — not yet wired into programs/extraction.py.
When ready, integrate after website scraping via save_relationships() in programs/_shared.py.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Set
from urllib.parse import urlparse, quote_plus

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.universe.ops.rate_limiter import rate_limiter

# Configure logging
logger = logging.getLogger(__name__)

class RelationshipEnricher:
    """
    Agent to discover business relationships (Customers, Suppliers).
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        
        # Keywords to identify relationship sections
        self.CUSTOMER_KEYWORDS = ["our customers", "trusted by", "clients", "who we work with", "case studies", "testimonials"]
        self.PARTNER_KEYWORDS = ["our partners", "strategic partners", "collaborators"]
        self.SUPPLIER_KEYWORDS = ["suppliers", "supply chain", "vendors"]

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        from src.core.config import settings
        ctx_kw = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        if settings.ignore_ssl_errors:
            ctx_kw["ignore_https_errors"] = True
        self.context = await self.browser.new_context(**ctx_kw)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _safe_goto(self, page: Page, url: str) -> bool:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.warning(f"Failed to load {url}: {e}")
            return False

    async def find_relationships(self, company_name: str, website_url: str) -> List[Dict[str, Any]]:
        """
        Main entry point to find relationships for a company.
        """
        logger.info(f"Enriching relationships for {company_name}...")
        relationships = []
        
        page = await self.context.new_page()
        
        # 1. Analyze Website
        if website_url:
            web_rels = await self._analyze_website(page, website_url, company_name)
            relationships.extend(web_rels)
            
        # 2. Web Search (Contract Awards, Press Releases)
        search_rels = await self._search_for_contracts(page, company_name)
        relationships.extend(search_rels)
        
        await page.close()
        
        # 3. Filter out self-references
        relationships = self._filter_self_references(relationships, company_name)
        
        return relationships

    async def _analyze_website(self, page: Page, url: str, company_name: str) -> List[Dict[str, Any]]:
        """
        Scrape company website for logo walls or text lists of customers/case studies.
        """
        found = []
        if not await self._safe_goto(page, url):
            return []
            
        content = await page.content()
        lower_content = content.lower()
        
        # 1. Extract case study company names from structured sections
        case_study_rels = await self._extract_case_studies(page)
        found.extend(case_study_rels)
        
        # 2. Look for customer logo walls (filter aggressively)
        logo_rels = await self._extract_logo_wall(page, url)
        found.extend(logo_rels)
        
        # 3. Extract customer lists from text (NEW)
        text_rels = await self._extract_customer_text_lists(page)
        found.extend(text_rels)
        
        return found
    
    async def _extract_case_studies(self, page: Page) -> List[Dict[str, Any]]:
        """Extract company names from case study sections."""
        found = []
        
        # Look for headings or links containing case study indicators
        case_study_selectors = [
            'a[href*="case-study"]',
            'a[href*="customer-story"]',
            'a[href*="success-story"]',
            'h2:has-text("Case Study")',
            'h3:has-text("Customer Story")'
        ]
        
        for selector in case_study_selectors:
            try:
                elements = await page.locator(selector).all()
                for elem in elements[:10]:  # Limit to 10 case studies
                    text = await elem.inner_text()
                    # Extract company name - look for capitalized phrases
                    company_name = self._extract_company_from_text(text)
                    if company_name:
                        found.append({
                            "entity_name": company_name,
                            "type": "customer",
                            "source": "case_study",
                            "confidence": 0.9
                        })
            except:
                continue
        
        return found
    
    async def _extract_logo_wall(self, page: Page, url: str) -> List[Dict[str, Any]]:
        """Extract company logos with aggressive filtering."""
        found = []
        seen = set()
        
        # Only look for images with "logo" or "client" in src or alt
        images = await page.locator("img").all()
        for img in images:
            try:
                alt = await img.get_attribute("alt") or ""
                src = await img.get_attribute("src") or ""
                
                # Filter 1: Must have "logo" or "client" in src/alt
                if not ("logo" in src.lower() or "logo" in alt.lower() or 
                        "client" in src.lower() or "client" in alt.lower()):
                    continue
                
                # Filter 2: Clean and validate company name
                clean_name = self._clean_entity_name(alt)
                if not self._is_valid_company_name(clean_name):
                    continue
                
                # Filter 3: Avoid duplicates
                if clean_name.lower() in seen:
                    continue
                seen.add(clean_name.lower())
                
                found.append({
                    "entity_name": clean_name,
                    "type": "customer",
                    "source": "website_logo",
                    "confidence": 0.7
                })
            except:
                continue
        
        return found
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Validate if a string is likely a company name."""
        if not name or len(name) < 3:
            return False
        
        # Blacklist generic terms (expanded)
        blacklist = [
            "logo", "image", "icon", "badge", "photo", "close", "menu", "open",
            "browser", "chrome", "firefox", "safari", "edge", "explorer", "opera",
            "white", "black", "blue", "red", "green", "family", "girl", "boy",
            "person", "people", "lunch", "dinner", "table", "wood", "field",
            "push", "pull", "click", "button", "link", "header", "footer",
            "cover", "background", "foreground", "title", "subtitle", "caption",
            "read", "more", "learn", "news", "article", "blog", "post", "update",
            "sustainability", "audit", "policy", "privacy", "cookies", "terms",
            "conditions", "about", "contact", "career", "job", "work", "team",
            "success", "story", "case", "study", "topic", "hot", "trend",
            "cloud", "migration", "application", "service", "solution",
            "splendour", "unlocking", "regarding", "supported", "language",
            "latest", "area", "accept", "most", "admired", "data", "center",
            "insight", "sector", "planet", "creating", "value", "chain",
            "change", "setting", "workplace", "technology", "our",
            "united", "kingdom", "states", "france", "germany", "spain",
            "china", "japan", "india", "canada", "australia", "brazil",
            "mexico", "south", "africa", "italy", "russia", "netherlands"
        ]
        
        name_lower = name.lower()
        if any(term == name_lower for term in blacklist): # Exact match check might be too strict if part of phrase
             return False

        for term in blacklist:
            if term in name_lower.split(): # Check if term is a whole word in the name
                return False
        
        # Must start with capital letter
        if not name[0].isupper():
            return False
        
        # Reject if too many special characters
        special_count = sum(1 for c in name if not c.isalnum() and c != ' ' and c != '-' and c != '.')
        if special_count > 2:
            return False

        # Reject if overly long (likely a sentence/title)
        if len(name.split()) > 5:
            return False
            
        # Reject generic "Companies" or "Most Admired Companies" types
        if "companies" in name_lower and "admired" in name_lower:
            return False
        
        return True
    
    def _extract_company_from_text(self, text: str) -> str:
        """Extract a company name from case study text."""
        # Simple heuristic: Look for capitalized phrases
        words = text.split()
        candidates = []
        current = []
        
        for word in words:
            if word and word[0].isupper() and len(word) > 1:
                current.append(word)
            else:
                if current and len(current) <= 4:
                    candidates.append(" ".join(current))
                current = []
        
        # Return first valid candidate
        for candidate in candidates:
            if self._is_valid_company_name(candidate):
                return candidate
        
        return ""
    
    async def _extract_customer_text_lists(self, page: Page) -> List[Dict[str, Any]]:
        """Extract customer names from text-based customer lists (<li> elements only)."""
        found = []
        
        # Look for sections with customer keywords
        for keyword in self.CUSTOMER_KEYWORDS:
            try:
                # Find the section/container with the keyword
                # We look for a heading or strong text, then find the parent container
                headers = await page.locator(f"*:has-text('{keyword}')").all()
                
                for header in headers[:3]: # Limit to first 3 headers
                    try:
                        # Get the parent container to scope the search
                        # This is a heuristic - usually the list is a sibling or child of the header's parent
                        # For simplicity/robustness, we just look for <li> elements nearby
                        
                        # Check if this element is a header (h1-h6) or strong
                        tag = await header.evaluate("el => el.tagName")
                        if tag not in ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'STRONG', 'B']:
                            continue
                            
                        # Find lists in the vicinity (next sibling or parent's child)
                        # We'll search the parent for <ul> or <ol>
                        parent = header.locator("..")
                        lists = await parent.locator("ul, ol").all()
                        
                        for lst in lists:
                            items = await lst.locator("li").all()
                            for item in items:
                                text = await item.inner_text()
                                companies = self._extract_companies_from_list(text)
                                for company in companies:
                                    found.append({
                                        "entity_name": company,
                                        "type": "customer",
                                        "source": "customer_list",
                                        "confidence": 0.8
                                    })
                    except:
                        continue
            except:
                continue
        
        return found
    
    def _extract_companies_from_list(self, text: str) -> List[str]:
        """Extract company names from a customer list text block."""
        companies = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and common headers
            if not line or len(line) < 3:
                continue
            if any(word in line.lower() for word in ['our customers', 'clients', 'trusted by', 'case study', 'read more', 'learn more']):
                continue
            
            # Look for capitalized phrases that could be company names
            if line and line[0].isupper():
                # Clean and validate
                clean = line.split('-')[0].strip()  # Remove descriptions after dash
                clean = clean.split(':')[0].strip()  # Remove descriptions after colon
                
                if self._is_valid_company_name(clean) and len(clean) <= 50:
                    companies.append(clean)
        
        # Deduplicate
        return list(set(companies))[:10]  # Max 10 from any single section
    
    def _filter_self_references(self, relationships: List[Dict[str, Any]], company_name: str) -> List[Dict[str, Any]]:
        """Filter out self-references and near-matches to the company itself."""
        filtered = []
        company_lower = company_name.lower()
        company_words = set(company_lower.split())
        
        # Common suffixes to remove when comparing core names
        suffixes = [' plc', ' limited', ' ltd', ' group', ' inc', ' corp', ' corporation', 
                    ' holdings', ' technologies', ' electronics', ' solutions', ' systems']
        
        for rel in relationships:
            entity_lower = rel['entity_name'].lower()
            entity_words = set(entity_lower.split())
            
            # Check for exact match
            if entity_lower == company_lower:
                continue
            
            # Check for substantial word overlap (likely same company)
            overlap = len(company_words & entity_words)
            if overlap >= 2 and overlap >= len(company_words) * 0.6:
                continue
            
            # Check core name matching (remove common suffixes)
            core_entity = entity_lower
            core_company = company_lower
            for suffix in suffixes:
                core_entity = core_entity.replace(suffix, '').strip()
                core_company = core_company.replace(suffix, '').strip()
            
            # If core names match or are very similar, it's a self-reference
            if core_entity == core_company:
                continue
            
            # If the entity is a single word that appears in the company name, likely self-ref
            if len(entity_words) == 1 and entity_lower in company_lower:
                continue
            
            filtered.append(rel)
        
        return filtered

    async def _search_for_contracts(self, page: Page, company_name: str) -> List[Dict[str, Any]]:
        """
        Search Google for 'Company Name contract award' or 'supplier to'.
        Uses rate_limiter to avoid triggering Google's anti-bot (100/hr shared with website_finder).
        Retries with exponential backoff on timeout/rate-limit.
        """
        found = []
        queries = [
            f'"{company_name}" selected by',
            f'"{company_name}" contract award',
            f'"{company_name}" supplier to'
        ]
        max_retries = 3
        base_delay = 2.0
        search_timeout_ms = 30000  # 30s (was 20s; 15s often too short under load)

        for q in queries:
            for attempt in range(max_retries):
                try:
                    await rate_limiter.acquire("google_search")
                    await page.goto(
                        f"https://www.google.com/search?q={quote_plus(q)}&hl=en",
                        timeout=search_timeout_ms,
                        wait_until="domcontentloaded",
                    )
                    await page.wait_for_load_state("domcontentloaded")

                    # Handle cookie consent (EU/UK)
                    try:
                        consent = await page.query_selector('button:has-text("Reject all")')
                        if not consent:
                            consent = await page.query_selector('button:has-text("Accept all")')
                        if consent:
                            await consent.click()
                            await page.wait_for_load_state("networkidle")
                    except Exception:
                        pass

                    # Google organic results: div.g
                    results = await page.locator("div.g").all()
                    for res in results[:5]:  # Top 5
                        text = await res.inner_text()
                        if "selected by" in text.lower():
                            tgt = text.lower().split("selected by")[1].split(" to ")[0].strip()
                            if len(tgt) < 50:
                                found.append({
                                    "entity_name": tgt.title(),
                                    "type": "customer",
                                    "source": "web_search",
                                    "confidence": 0.8
                                })
                        if "supplier to" in text.lower():
                            tgt = text.lower().split("supplier to")[1].split(" for ")[0].strip()
                            if len(tgt) < 50:
                                found.append({
                                    "entity_name": tgt.title(),
                                    "type": "customer",
                                    "source": "web_search",
                                    "confidence": 0.8
                                })
                    break  # Success
                except Exception as e:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Search failed for '{q[:40]}...' (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt + 1 < max_retries:
                        await asyncio.sleep(delay)
                    else:
                        logger.debug(f"Giving up on query after {max_retries} attempts")
            # Inter-query delay to avoid rate limits (300–900ms recommended for search engines)
            if q != queries[-1]:
                await asyncio.sleep(0.5)

        return found
        
    def _clean_entity_name(self, text: str) -> str:
        """Clean alt text to entity name"""
        bad_words = ["logo", "image", "of", "client", "partner", "brand", "icon"]
        parts = text.split()
        clean = [p for p in parts if p.lower() not in bad_words]
        return " ".join(clean).strip()

if __name__ == "__main__":
    # Test
    async def main():
        enricher = RelationshipEnricher(headless=False)
        async with enricher:
            # Example: A known company
            rels = await enricher.find_relationships("Palantir", "https://www.palantir.com")
            print(f"Found: {rels}")
            
    asyncio.run(main())


"""
Universe Enrichment Agent.
Visits company websites to extract general business information.
"""
import asyncio
import re
import logging
from urllib.parse import parse_qs, urlparse
from typing import Dict, Any, Optional, List
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction
from src.universe.ops.website_validator import is_likely_company_site, is_url_acceptable_for_company

logger = logging.getLogger(__name__)

# Registry and directory domains that must never be stored as company websites.
# These return boilerplate (e.g. Companies House pages) instead of business content.
REGISTRY_BLOCKLIST = (
    "company-information.service.gov.uk",
    "find-and-update.company-information",
    "beta.companieshouse.gov.uk",
    "companieshouse.gov.uk",
    "api.company-information.service.gov.uk",
    "opencorporates.com",
)


def _extract_destination_url(href: str) -> Optional[str]:
    """
    Extract the actual destination URL from a link.
    Google wraps organic results in redirect URLs (google.com/url?q=...).
    Returns the destination URL or None if unparseable.
    """
    if not href or not href.startswith("http"):
        return None
    parsed = urlparse(href)
    if "google" in parsed.netloc and "/url" in parsed.path:
        qs = parse_qs(parsed.query)
        targets = qs.get("q", [])
        if targets and targets[0].startswith("http"):
            return targets[0]
    return href


def _is_blocked_url(url: str) -> bool:
    """Return True if URL is a registry/directory page, not a company website."""
    if not url:
        return True
    lower = url.lower()
    return any(bl in lower for bl in REGISTRY_BLOCKLIST)

class WebsiteExtractionAgent(BaseBrowsingAgent):
    """
    Agent that locates and extracts structured data from a company's website.

    Two steps:
      1. find_website_url() — Google search with disambiguating query
      2. run()              — navigate to the URL, validate, and extract via LLM

    Supports async context manager for browser reuse across multiple companies:
        async with WebsiteExtractionAgent() as agent:
            for company in companies:
                url = await agent.find_website_url(company.name)
                data = await agent.run(company.name, url)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._managed = False  # Set True when used as context manager
    
    async def __aenter__(self):
        """Start browser once for the entire batch."""
        await self.start()
        self._managed = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Tear down browser after the batch completes."""
        self._managed = False
        await self.stop()
        return False
    
    def _parse_locality_from_address(self, address: Optional[str]) -> Optional[str]:
        """
        Extract city/locality from address when hq_city is missing.
        UK format: "123 Street, City, Postcode" or "City, County".
        """
        if not address or not address.strip():
            return None
        # UK postcode pattern - remove postcode and trailing parts
        uk_postcode = re.compile(r"\b[A-Z]{1,2}[0-9]{1,2}[A-Z]?\s*[0-9][A-Z]{2}\b", re.I)
        parts = [p.strip() for p in address.split(",") if p.strip()]
        for p in reversed(parts):
            if uk_postcode.search(p) or p.isdigit() or len(p) < 3:
                continue
            if 3 <= len(p) <= 50 and not p.lower().startswith(("unit", "suite", "building", "floor")):
                return p
        return None

    def _build_website_search_query(
        self,
        company_name: str,
        description: Optional[str] = None,
        sector: Optional[str] = None,
        sub_sector: Optional[str] = None,
        certifications: Optional[List[str]] = None,
        hq_city: Optional[str] = None,
        hq_address: Optional[str] = None,
        hq_country: Optional[str] = None,
    ) -> str:
        """
        Build a disambiguating search query using SIC/description, sector, certifications, location.
        Helps surface the actual company site rather than museums, articles, or similarly named firms.
        """
        parts = [company_name]
        # Industry: prefer sub_sector > description > sector
        industry = None
        skip_words = {"ltd", "limited", "plc", "llc", "inc"}
        if sub_sector and len(sub_sector) > 2:
            words = sub_sector.split()[:4]
            industry = " ".join(w for w in words if len(w) > 2 and w.lower() not in skip_words)
        if not industry and description and len(description) > 5:
            if "unknown" not in description.lower() and not description.strip().startswith("SIC "):
                words = description.replace(";", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()[:6]
                industry = " ".join(w for w in words if len(w) > 2 and not w.isdigit() and w.lower() not in skip_words)
        if not industry and sector:
            industry = sector
        if industry:
            parts.append(industry)
        # Certifications (AS9100, ISO9001, etc.) - strong industry signal
        if certifications:
            cert_str = " ".join(c for c in certifications[:3] if c and len(c) > 2)
            if cert_str:
                parts.append(cert_str)
        # Location: hq_city > parsed from address > hq_country
        locality = hq_city or self._parse_locality_from_address(hq_address)
        if locality:
            parts.append(locality)
        elif hq_country:
            country_names = {"GB": "UK", "UK": "UK", "FR": "France", "DE": "Germany", "NL": "Netherlands"}
            parts.append(country_names.get(hq_country, hq_country))
        parts.append("company website")
        return " ".join(p for p in parts if p)

    async def _search_google_for_url(
        self, search_query: str, company_name: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """
        Run one Google search and return (first acceptable URL, None) or (None, stats dict).
        Stats include n_links, skipped_social, skipped_blocklist, skipped_url_check, reason.
        """
        await self.page.goto(f"https://www.google.com/search?q={search_query}&hl=en", timeout=30000)
        await self.page.wait_for_load_state("domcontentloaded")

        # Handle cookie/consent wall — try several selectors Google uses across regions
        for consent_text in ("Reject all", "Accept all", "I agree", "Agree", "Accept"):
            try:
                btn = await self.page.query_selector(f'button:has-text("{consent_text}")')
                if btn and await btn.is_visible():
                    await btn.click()
                    # Wait for search results to appear, not networkidle (which can hang)
                    await self.page.wait_for_selector('#search', timeout=8000)
                    break
            except Exception:
                pass

        # Wait for #search to be present (in case no consent wall)
        try:
            await self.page.wait_for_selector('#search', timeout=8000)
        except Exception:
            # Log page title to help debug (CAPTCHA, redirect, etc.)
            title = await self.page.title()
            logger.warning(f"#search not found after search (page title: {title!r})")

        # Scroll to load any lazily rendered results
        try:
            await self.page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        links = await self.page.query_selector_all('#search a')
        n_links = len(links)
        skipped_social = 0
        skipped_blocklist = 0
        skipped_url_check = 0
        url_check_reason = None
        for link in links:
            href = await link.get_attribute('href')
            if not href or not href.startswith('http'):
                continue
            dest = _extract_destination_url(href)
            if not dest:
                continue
            if any(skip in dest.lower() for skip in ('google.', 'youtube.', 'facebook.', 'linkedin.', 'twitter.', 'instagram.')):
                skipped_social += 1
                continue
            if _is_blocked_url(dest):
                skipped_blocklist += 1
                continue
            ok, reason = is_url_acceptable_for_company(dest, company_name)
            if not ok:
                skipped_url_check += 1
                if url_check_reason is None:
                    url_check_reason = reason
                continue
            return (dest, None)
        stats = {
            "n_links": n_links,
            "skipped_social": skipped_social,
            "skipped_blocklist": skipped_blocklist,
            "skipped_url_check": skipped_url_check,
            "reason": url_check_reason,
        }
        return (None, stats)

    async def find_website_url(
        self,
        company_name: str,
        description: Optional[str] = None,
        sector: Optional[str] = None,
        sub_sector: Optional[str] = None,
        certifications: Optional[List[str]] = None,
        hq_city: Optional[str] = None,
        hq_address: Optional[str] = None,
        hq_country: Optional[str] = None,
    ) -> Optional[str]:
        """
        Use Playwright to search for the company website on Google.
        Uses SIC/description, sector, sub_sector, certifications, and location to disambiguate.
        If the full query finds no acceptable URL, retries with a shorter query to surface more results.
        """
        if not self.page:
            await self.start()

        search_query = self._build_website_search_query(
            company_name, description, sector, sub_sector, certifications,
            hq_city, hq_address, hq_country
        )
        logger.info(f"Searching for website: {search_query}")

        try:
            url, stats = await self._search_google_for_url(search_query, company_name)
            if url:
                logger.info(f"Found URL: {url}")
                return url
            if stats:
                parts = [f"links={stats['n_links']}"]
                if stats.get("skipped_social"):
                    parts.append(f"skipped_social={stats['skipped_social']}")
                if stats.get("skipped_blocklist"):
                    parts.append(f"skipped_blocklist={stats['skipped_blocklist']}")
                if stats.get("skipped_url_check"):
                    parts.append(f"skipped_url_check={stats['skipped_url_check']}")
                    if stats.get("reason"):
                        parts.append(f"reason={stats['reason']}")
                logger.warning("No suitable search results (first query). " + ", ".join(parts))

            # Fallback: shorter query can rank the real company site higher (e.g. "D & K Wiring" + "company website")
            fallback_query = f"{company_name} company website"
            if fallback_query != search_query:
                logger.info(f"Retrying with shorter query: {fallback_query}")
                url, _ = await self._search_google_for_url(fallback_query, company_name)
                if url:
                    logger.info(f"Found URL: {url}")
                    return url

            logger.warning("No suitable search results found on Google (tried full and fallback query).")
            return None

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None
    
    async def run(self, company_name: str, website_url: str) -> Dict[str, Any]:
        """
        Enrich a company by visiting its website.
        """
        data = {
            "description": None,
            "sector": None,
            "employees": None,
            "revenue": None
        }
        
        if not self.page:
            await self.start()
        
        try:
            # URL-level check before navigating (catches institutional domains, wrong URLs)
            ok, reason = is_url_acceptable_for_company(website_url, company_name)
            if not ok:
                logger.info(f"URL rejected for {company_name}: {reason}")
                data["_url_valid"] = False
                return data
            logger.info(f"Navigating to {website_url}...")
            # Go to website
            try:
                await self.page.goto(website_url, timeout=60000)
                await self.page.wait_for_load_state("domcontentloaded")
            except Exception as e:
                logger.warning(f"Failed to load {website_url}: {e}")
                data["_url_valid"] = False  # Fail fast: reject unreachable site
                return data
            
            # Get content
            content = await self.get_page_content()
            
            # Basic website check: is this likely the company's real site?
            valid, reason = is_likely_company_site(company_name, content)
            if not valid:
                logger.info(f"Website validation failed for {company_name}: {reason}")
                data["_url_valid"] = False
                return data
            
            # Prompt LLM - MUST use action "extract" (not click/scroll) so we get data from current page
            goal = f"""
            Goal: Extract general business information for "{company_name}" from their website content.
            
            You MUST return action: "extract" with a "data" object. Do NOT return click, scroll, or wait.
            Extract whatever you can from the CURRENT page content. If a field is not found, use null.
            
            In the "data" object, extract:
            - description: A concise 1-2 sentence description of what the company does.
            - sector: The industry sector (e.g. Fintech, Healthcare, Manufacturing).
            - sub_sector: A more specific niche (e.g. Generative AI, medtech, precision machining).
            - city: The city where the company is headquartered.
            - employees: Actual number of employees/FTEs if stated (integer).
            - revenue: Estimated annual revenue if mentioned (e.g. "$10M", "£5m").
            - moats: List of competitive advantages if evident.
            
            Return JSON: {{"action": "extract", "data": {{...}}, "reasoning": "..."}}
            Content:
            {content[:15000]}
            """
            
            extraction = await self.ask_llm(goal, content[:5000])
            
            # Accept extract; if LLM returned click/scroll, try to salvage any data in "data"
            if extraction.get("action") == AgentAction.EXTRACT or extraction.get("data"):
                extracted = extraction.get("data", {})
                data.update({
                    "description": extracted.get("description"),
                    "sector": extracted.get("sector"),
                    "sub_sector": extracted.get("sub_sector"),
                    "city": extracted.get("city"),
                    "employees": self._parse_int(extracted.get("employees")),
                    "revenue": self._parse_money(extracted.get("revenue")),
                    "moats": extracted.get("moats")
                })
                
        except Exception as e:
            logger.exception(f"Enrichment failed for {company_name}: {e}")
        finally:
            if not self._managed:
                await self.stop()
            
        return data

    def _parse_int(self, val: Any) -> Optional[int]:
        if isinstance(val, int): return val
        if isinstance(val, str) and val.isdigit(): return int(val)
        return None

    def _parse_money(self, val: Any) -> Optional[int]:
        """Parse currency string to integer GBP"""
        if not val or not isinstance(val, str): return None
        try:
            val = val.lower().replace(',', '')
            num_match = re.search(r'[\d\.]+', val)
            if not num_match: return None
            number = float(num_match.group(0))
            
            multiplier = 1
            if 'm' in val or 'million' in val: multiplier = 1_000_000
            elif 'b' in val or 'billion' in val: multiplier = 1_000_000_000
            elif 'k' in val: multiplier = 1_000
            
            # Currency conversion (approximate to GBP)
            rate = 1.0
            if '$' in val or 'usd' in val: rate = 0.8
            elif '€' in val or 'eur' in val or 'euro' in val: rate = 0.85
            
            return int(number * multiplier * rate)
        except:
            return None


"""
Universe Enrichment Agent.
Visits company websites to extract general business information.
"""
import logging
from typing import Dict, Any, Optional
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

logger = logging.getLogger(__name__)

class UniverseEnrichmentAgent(BaseBrowsingAgent):
    """
    Agent that visits a company's website to extract its description, sector, and size.
    
    Supports async context manager for browser reuse across multiple companies:
        async with UniverseEnrichmentAgent() as agent:
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
    
    async def find_website_url(self, company_name: str) -> Optional[str]:
        """
        Use Playwright to search for the company website on Google.
        """
        if not self.page:
            await self.start()
            
        search_query = f"{company_name} official website"
        logger.info(f"Searching for website: {search_query}")
        
        try:
            # Navigate to Google
            await self.page.goto(f"https://www.google.com/search?q={search_query}&hl=en", timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Handle cookie consent if it appears (common on Google EU/UK)
            try:
                # "Reject all" or "Accept all" button
                consent_button = await self.page.query_selector('button:has-text("Reject all")')
                if not consent_button:
                    consent_button = await self.page.query_selector('button:has-text("Accept all")')
                if consent_button:
                    await consent_button.click()
                    await self.page.wait_for_load_state("networkidle")
            except:
                pass

            # Selector for organic results
            # Typically h3 inside a div or a inside the main result block
            # Try to find the first result that is NOT an ad
            
            # Wait for results
            try:
                await self.page.wait_for_selector('#search', timeout=5000)
            except:
                pass
                
            # Get all links in search results
            links = await self.page.query_selector_all('#search a')
            
            for link in links:
                href = await link.get_attribute('href')
                if href and href.startswith('http') and 'google' not in href and 'youtube' not in href:
                    logger.info(f"Found URL: {href}")
                    return href
            
            logger.warning("No suitable search results found on Google.")
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
            logger.info(f"Navigating to {website_url}...")
            # Go to website
            try:
                await self.page.goto(website_url, timeout=60000)
                await self.page.wait_for_load_state("domcontentloaded")
            except Exception as e:
                logger.warning(f"Failed to load {website_url}: {e}")
                return data
            
            # Get content
            content = await self.get_page_content()
            
            # Prompt LLM
            goal = f"""
            Goal: Extract general business information for "{company_name}" from their website content.
            
            EXTRACT:
            - description: A concise 1-2 sentence description of what the company does.
            - sector: The industry sector (e.g. Fintech, Healthcare, Manufacturing).
            - sub_sector: A more specific niche (e.g. Generative AI, medtech, precision machining).
            - city: The city where the company is headquartered.
            - employees: Actual number of employees/FTEs if stated (integer). Look for "About Us" or "Careers" sections.
            - revenue: Estimated annual revenue if mentioned (e.g. "$10M").
            - moats: List of competitive advantages (e.g. "Network Effects", "High Switching Costs", "Regulatory", "Brand", "IP").
            
            Return as structured JSON.
            If not found, return null.
            
            Return as structured JSON.
            If not found, return null.
            
            Content:
            {content[:15000]} 
            """
            
            extraction = await self.ask_llm(goal, content[:5000]) # Truncate for speed/cost if needed, but PageContent usually handles it.
            
            if extraction.get("action") == AgentAction.EXTRACT:
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
            import re
            # Extract number
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

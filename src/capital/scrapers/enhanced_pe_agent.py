"""
Enhanced PE Website Agent that extracts investment theses and deal context.
"""
import asyncio
from typing import List, Dict, Any
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class EnhancedPEWebsiteAgent(BaseBrowsingAgent):
    """
    Enhanced agent to scrape portfolio companies AND their investment theses,
    deal rationales, and other enrichment data from PE firm websites.
    """
    
    async def run(self, url: str, deep_dive: bool = False) -> List[Dict[str, Any]]:
        """
        Scrape portfolio companies with optional deep dive into individual pages.
        
        Args:
            url: PE firm's portfolio page URL
            deep_dive: If True, visit individual company pages for theses
        
        Returns:
            List of companies with enriched data
        """
        companies = []
        await self.start()
        
        try:
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("domcontentloaded")
            
            steps = 0
            max_steps = 10
            
            while steps < max_steps:
                content = await self.get_page_content()
                
                if not deep_dive:
                    # Standard extraction (current behavior)
                    goal = f"""
                    Goal: Extract COMPREHENSIVE portfolio company data for "{url}".
                    
                    FOCUS:
                    - Company Name
                    - Sector / Industry
                    - Business Description
                    - Status (Current vs Realized/Exited)
                    - Investment Year (if available)
                    - Investment Thesis (if shown on cards)
                    - Deal context / why invested (if visible)
                    
                    STRATEGY:
                    1. NAVIGATE: Find "Portfolio", "Investments", or "Our Companies" link.
                    2. EXTRACT: Look for grid/list of companies.
                    3. PAGINATION: If "Load More" or "Next Page" exists, use it.
                    
                    Content to Analyze:
                    {content[:15000]}... (truncated)
                    """
                else:
                    # Enhanced extraction with deep dive
                    goal = f"""
                    Goal: Click into individual company pages to extract investment thesis.
                    
                    IF you see company cards:
                    1. Click on ONE company to view its detail page
                    2. Extract ALL data from the detail page:
                       - Investment thesis
                       - Deal announcement text
                       - Entry/exit dates
                       - Strategic rationale
                       - Any valuation mentions
                    3. Return to portfolio page and repeat
                    
                    IF already on a detail page:
                    - Extract thesis and navigate back
                    
                    Content:
                    {content[:15000]}... (truncated)
                    """
                
                decision = await self.ask_llm(goal, content)
                
                if decision.get("action") == AgentAction.EXTRACT:
                    data = decision.get("data", [])
                    # Normalize to list
                    if isinstance(data, dict):
                         if "companies" in data: data = data["companies"]
                         else: data = [data]
                    
                    companies.extend(data)
                
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                    
                steps += 1
                
        finally:
            await self.stop()
            
        return companies


async def research_pe_website():
    """Test the enhanced agent on Silver Lake"""
    from src.core.config import settings
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Research")
    
    agent = EnhancedPEWebsiteAgent(headless=True, model_name=settings.browsing_model)
    
    logger.info("Testing standard extraction...")
    standard_data = await agent.run("https://www.silverlake.com/", deep_dive=False)
    
    logger.info(f"\n✓ Extracted {len(standard_data)} companies")
    logger.info("\nSample company:")
    if standard_data:
        logger.info(str(standard_data[0]))
    
    # Check what fields we're getting
    if standard_data:
        fields = set()
        for company in standard_data[:5]:
            if isinstance(company, dict):
                fields.update(company.keys())
        
        logger.info(f"\nFields captured: {fields}")

if __name__ == "__main__":
    asyncio.run(research_pe_website())

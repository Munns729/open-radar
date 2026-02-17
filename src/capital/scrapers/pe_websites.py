"""
PE Website Agent for extracting portfolio companies.
"""
import asyncio
from typing import List, Dict, Any
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class PEWebsiteAgent(BaseBrowsingAgent):
    """
    Agent to scrape portfolio companies from a PE firm's website.
    """
    
    async def run(self, url: str) -> List[Dict[str, Any]]:
        companies = []
        await self.start()
        
        try:
            await self.page.goto(url, timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded")
            
            steps = 0
            max_steps = 10
            
            while steps < max_steps:
                content = await self.get_page_content()
                
                goal = f"""
                Goal: Extract COMPREHENSIVE portfolio company data for "{url}".
                
                FOCUS:
                - Company Name
                - Sector / Industry (CRITICAL)
                - Business Description (What do they do?)
                - Status (Current vs Realized/Exited)
                - Investment Year (if available)
                
                STRATEGY:
                1. NAVIGATE: Find "Portfolio", "Investments", or "Our Companies" link.
                   - If a filter exists (e.g. "All", "Realized"), try to view ALL.
                2. EXTRACT: Look for grid/list of companies.
                   - You might need to hover or click a card to see details.
                3. PAGINATION: If "Load More" or "Next Page" exists, use it.
                
                Content to Analyze:
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
                    # Continue to find more?
                    
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                    
                steps += 1
                
        finally:
            await self.stop()
            
        return companies

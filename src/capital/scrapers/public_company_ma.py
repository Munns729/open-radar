"""
Public Market Agent for analyzing 8-K filings.
"""
from typing import Dict, Any, Optional
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class PublicMarketAgent(BaseBrowsingAgent):
    """
    Agent to parse SEC 8-K filings for deal terms.
    Input: URL to specific 8-K filing or list of recent 8-Ks.
    """
    
    async def run(self, filing_url: str) -> Optional[Dict[str, Any]]:
        deal_terms = None
        await self.start()
        
        try:
            await self.page.goto(filing_url, timeout=30000)
            
            # Simple single-pass extraction for 8-Ks usually works
            content = await self.get_page_content()
            
            goal = """
            Goal: Extract M&A deal terms from this 8-K filing.
            Focus on Item 2.01 (Completion of Acquisition) or Item 1.01 (Entry into Material Definitive Agreement).
            Extract:
            - Buyer Name
            - Target Name
            - Purchase Price (if disclosed)
            - Rationale
            - Multiple (if mentioned)
            """
            
            # Helper: For 8-Ks, we might need a larger context window or RAG.
            # BaseAgent truncates to 20k chars, which is often enough for the body, but 8-Ks are long.
            # Here we trust the truncation or assume the relevant parts are near the top/middle.
            
            decision = await self.ask_llm(goal, content)
            
            if decision.get("action") == AgentAction.EXTRACT:
                deal_terms = decision.get("data")
                
        finally:
            await self.stop()
            
        return deal_terms

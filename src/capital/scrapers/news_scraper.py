"""
News Monitoring Agent for M&A.
"""
from typing import List, Dict, Any
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class NewsMonitoringAgent(BaseBrowsingAgent):
    """
    Agent to visual scan news sites (PE Hub, etc) for deal announcements.
    """
    
    async def run(self, source_url: str) -> List[Dict[str, Any]]:
        deals = []
        await self.start()
        
        try:
            await self.page.goto(source_url, timeout=30000)
            
            steps = 0
            max_steps = 8
            
            while steps < max_steps:
                content = await self.get_page_content()
                
                goal = f"""
                Goal: Identify recent deal announcements (last 24 hours).
                1. Look for headlines about "Files", "Acquires", "Invests", "Exits".
                2. Extract: Buyer, Target, Deal Type.
                3. If clicked into article, extract details then go back or finish.
                """
                
                decision = await self.ask_llm(goal, content)
                
                if decision.get("action") == AgentAction.EXTRACT:
                    data = decision.get("data", [])
                    if isinstance(data, list):
                        deals.extend(data)
                    else:
                        deals.append(data)
                
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                    
                steps += 1
                
        finally:
            await self.stop()
            
        return deals

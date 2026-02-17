"""
SEC Edgar Agent for discovering PE firms.
"""
import asyncio
from typing import List, Dict, Any
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class SECEdgarAgent(BaseBrowsingAgent):
    """
    Agent to search SEC IAPD (Investment Adviser Public Disclosure) for PE firms.
    Target URL: https://adviserinfo.sec.gov/
    """
    
    async def run(self, search_term: str = "Private Equity") -> List[Dict[str, Any]]:
        results = []
        await self.start()
        
        try:
            # 1. Navigate to Search
            await self.page.goto("https://adviserinfo.sec.gov/", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # 2. Main Loop
            steps = 0
            max_steps = 15 
            
            while steps < max_steps:
                content = await self.get_page_content()
                
                # Custom goal guidance for the LLM
                goal = f"""
                You are on the SEC Investment Adviser Public Disclosure website (adviserinfo.sec.gov).
                
                GOAL: Find Private Equity firms.
                
                STRATEGY:
                1. SELECT FIRM TAB: The site defaults to "Individual" search. You MUST click the "Firm" tab/button first to search for companies.
                   - Look for a tab/button labeled "Firm" (usually has a building icon).
                   - Action: CLICK it.
                2. SEARCH: Scan the MAIN CENTER AREA for the Firm Name search input. 
                   - Look for `input[aria-label='firm-name']`.
                   - Action: TYPE '{search_term}' into that input.
                   - THEN Action: PRESS "Enter" on that input (or click the "Search" button).
                3. RESULT DETECTION: If you see a list/table, EXTRACT.
                3. EXTRACT: Extract the list of firms. For each firm, get:
                   - Name
                   - SEC Number (if visible)
                   - Location/City (if visible)
                
                IMPORTANT: Return the ACTUAL TEXT VALUES (e.g. "Blackstone", "801-12345"), NOT CSS selectors.
                FORMAT: "data": [ {{ "name": "...", "sec_number": "..." }}, ... ] (List of objects).
                
                STATUS:
                - Current collected items: {len(results)}
                - Steps taken: {steps}
                
                If you have extracted at least 1 firm, you can 'finish'.
                If you cannot find a search bar after 3 steps, 'finish'.
                """
                
                decision = await self.ask_llm(goal, content)
                
                if decision.get("action") == AgentAction.EXTRACT:
                    # Append extracted data
                    data = decision.get("data", {})
                    
                    # Handle common LLM nesting (e.g. { "firms": [...] })
                    if isinstance(data, dict):
                        if "firms" in data:
                            data = data["firms"]
                        elif "data" in data:
                            data = data["data"]
                    
                    # Expect data to be a list of firms or a single firm object
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        results.append(data)
                    
                    # Logic: If we extracted, maybe we page next or finish? 
                    # For simplicity in this demo, we assume one page or finish.
                    steps += 1
                    continue
                    
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                
                steps += 1
                
        finally:
            await self.stop()
            
        return results

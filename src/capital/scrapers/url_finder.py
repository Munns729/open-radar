"""
URL Finder Agent.
Uses a browser to search for a firm's official website.
"""
import asyncio
from typing import Optional
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

class UrlFinderAgent(BaseBrowsingAgent):
    """
    Agent to find the official website of a PE firm.
    Target: Google / DuckDuckGo
    """
    
    async def run(self, firm_name: str) -> Optional[str]:
        website_url = None
        await self.start()
        print(f"[UrlFinder] Searching for {firm_name}...")
        
        try:
            # Use Google Search
            await self.page.goto("https://www.google.com", timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded")

            # Handle cookie consent (EU/UK)
            try:
                consent = await self.page.query_selector('button:has-text("Reject all")')
                if not consent:
                    consent = await self.page.query_selector('button:has-text("Accept all")')
                if consent:
                    await consent.click()
                    await self.page.wait_for_load_state("networkidle")
            except Exception:
                pass

            # Google search input is name="q"
            search_input = "input[name='q']"
            try:
                await self.page.wait_for_selector(search_input, timeout=5000)
                await self.page.fill(search_input, f"{firm_name} private equity official website")
                await self.page.press(search_input, "Enter")
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"[UrlFinder] Search interaction failed: {e}")
                return None
            
            # NOW ASK LLM TO EXTRACT
            goal = f"""
            Goal: Extract the OFFICIAL website URL for "{firm_name}" from the search results.
            
            Strategy:
            1. SCAN the results.
               - Look for the official domain (e.g. blackstone.com).
               - IGNORE aggregators (LinkedIn, Pitchbook, Bloomberg, Wikipedia).
               - Action: EXTRACT the 'href' of the official link.
            2. Return the URL in 'data'.
            """
            
            steps = 0
            while steps < 3: # Fewer steps needed now
                content = await self.get_page_content()
                decision = await self.ask_llm(goal, content[:15000])
                
                print(f"[UrlFinder] decision: {decision.get('action')} - {decision.get('reasoning')}")
                
                if decision.get("action") == AgentAction.EXTRACT:
                    # Expecting data: { "url": "..." } or string
                    data = decision.get("data")
                    if isinstance(data, dict):
                        website_url = data.get("url")
                    elif isinstance(data, str):
                        website_url = data
                    break
                
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                    
                steps += 1
                
                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                    
                steps += 1
                
        except Exception as e:
            # Log error
            print(f"UrlFinder failed for {firm_name}: {e}")
        finally:
            await self.stop()
            
        return website_url

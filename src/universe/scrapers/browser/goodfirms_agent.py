"""
GoodFirms Agent Scraper.
Uses BaseBrowsingAgent to navigate GoodFirms with LLM support.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction
from src.core.config import settings
from src.core.data_types import ScraperOutput

logger = logging.getLogger(__name__)

class GoodFirmsAgentScraper(BaseBrowsingAgent):
    """
    Scraper for GoodFirms that uses an LLM to navigate the UI.
    """
    
    BASE_URL = "https://www.goodfirms.co"
    
    def __init__(self, headless: bool = True):
        # GoodFirms uses browsing model (Qwen 8B)
        super().__init__(model_name=settings.browsing_model, headless=headless)

    async def discover(self, term: str = "Cybersecurity", country: str = "France", limit: int = 20) -> ScraperOutput:
        """
        Discover companies on GoodFirms for a specific term and country.
        """
        logger.info(f"Starting GoodFirms agent discovery for '{term}' in '{country}'")
        print(f"[FLOW] Hand-off -> GoodFirms Browser Agent (Target: {term} in {country})")
        
        discovered_data = []
        
        try:
            await self.start()
            
            # Step 1: Navigate to homepage
            logger.info(f"Navigating to {self.BASE_URL}")
            print(f"[FLOW] Navigating to Entry Point: {self.BASE_URL}")
            await self.page.goto(self.BASE_URL, wait_until="commit", timeout=60000)
            await asyncio.sleep(2)
            
            # Step 2: Agent Loop
            goal = f"Search for {term} companies in {country}. Find the search bar, type '{term} {country}', and click the search/arrow button to see results. Use 'click' or 'type' to navigate - do NOT use 'extract' until you see search results."
            
            max_steps = 10
            step_count = 0
            consecutive_extract = 0  # Break if LLM keeps returning extract (stuck loop)
            
            while step_count < max_steps:
                step_count += 1
                content = await self.get_page_content()
                
                # Check if we are on a results page
                if "directory" in self.page.url or "search" in self.page.url:
                    # Give extra time for listings to load
                    await asyncio.sleep(2)
                    if await self.page.locator(".firm-wrapper-item, .firm-wrapper").count() > 0:
                        logger.info("Listing detected on current page. Proceeding to extraction.")
                        print("[FLOW] Success: Listing Detected. Breaking Agent Loop.")
                        break
                
                decision = await self.ask_llm(goal, content)
                action = decision.get("action")
                print(f"[FLOW] Agent Reasoning -> Action: {action}")
                
                if action == "finish":
                    logger.info(f"Agent finished: {decision.get('reasoning')}")
                    break
                
                # Prevent extract loop: if LLM returns extract 3+ times without reaching results, break
                if action == "extract":
                    consecutive_extract += 1
                    if consecutive_extract >= 3:
                        logger.info("Breaking extract loop (3+ consecutive extract with no results page)")
                        break
                else:
                    consecutive_extract = 0
                    
                continue_running = await self.execute_action(decision)
                if not continue_running:
                    break
                    
                await asyncio.sleep(2)  # Breathing room
                
            # Step 3: Extraction
            # Once we (hopefully) land on the results page, use deterministic selectors for the data
            cards = await self.page.locator(".firm-wrapper-item, .firm-wrapper").all()
            logger.info(f"Found {len(cards)} cards on results page.")
            print(f"[FLOW] Extracting Data from {len(cards)} cards...")
            
            for i, card in enumerate(cards[:limit]):
                try:
                    # Name & Profile URL
                    name_el = card.locator("h3 a").first
                    if await name_el.count() == 0:
                        continue
                        
                    name = await name_el.inner_text()
                    profile_url = await name_el.get_attribute("href")
                    if profile_url and not profile_url.startswith("http"):
                        profile_url = self.BASE_URL + profile_url
                        
                    # Website Link (Direct!)
                    website = None
                    visit_btn = card.locator("a.visit-website").first
                    if await visit_btn.count() > 0:
                        raw_href = await visit_btn.get_attribute("href")
                        if raw_href:
                            website = raw_href
                            
                    item = {
                        "name": name.strip(),
                        "hq_country": country,
                        "discovered_via": "GoodFirms",
                        "website": website,
                        "source_url": profile_url,
                        "description": f"Discovered via GoodFirms agent search for '{term}' in '{country}'",
                        "metadata": {
                            "industry": term,
                            "scraper": "GoodFirmsAgentScraper"
                        }
                    }
                    
                    discovered_data.append(item)
                    logger.info(f"Extracted: {name}")
                    print(f"[FLOW] New Entity Found: {name}")
                    
                except Exception as e:
                    logger.warning(f"Error extracting card {i}: {e}")
                    
        except Exception as e:
            logger.error(f"GoodFirms agent discovery failed: {e}")
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            await self.page.screenshot(path=str(log_dir / "goodfirms_agent_error.png"))
        finally:
            await self.stop()
            
        return ScraperOutput(
            source="GoodFirms",
            data_type="discovery",
            data=discovered_data,
            row_count=len(discovered_data)
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False

    async def run(self, input_data: Dict[str, Any]) -> ScraperOutput:
        """Required by BaseAgent interface"""
        term = input_data.get("term", "Cybersecurity")
        country = input_data.get("country", "France")
        limit = input_data.get("limit", 20)
        return await self.discover(term=term, country=country, limit=limit)

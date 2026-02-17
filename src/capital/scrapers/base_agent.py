"""
Base LLM-based Browsing Agent.
Uses Playwright for browsing and an LLM for decision making.
Designed for low-cost, robust scraping.
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from openai import AsyncOpenAI
from bs4 import BeautifulSoup

from src.core.config import settings
# from src.universe.ops.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)

class AgentAction:
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    EXTRACT = "extract"
    FINISH = "finish"
    PRESS = "press"

class BaseBrowsingAgent(ABC):
    """
    Base class for LLM-driven browsing agents.
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        headless: bool = True
    ):
        self.model_name = model_name or settings.kimi_model
        self.headless = headless
        
        # Configure OpenAI client (works with Groq, Together, etc. if base_url is set)
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=api_base or settings.openai_api_base
        )
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.history: List[str] = [] # Track past actions

    async def start(self):
        """Initialize browser session"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        # Anti-detection scripts
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def stop(self):
        """Cleanup resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_page_content(self) -> str:
        """Get simplified HTML content for the LLM"""
        await self.remove_overlays() # Clean page before reading
        html = await self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove clutter
        for tag in soup(["script", "style", "svg", "noscript", "iframe", "ad", "footer"]):
            tag.decompose()
            
        # Clean attributes
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            allowed_attrs = ['id', 'class', 'href', 'name', 'type', 'placeholder', 'aria-label', 'role']
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag[attr]
                    
        return str(soup) # Return full content, rely on model context window

    async def remove_overlays(self):
        """Aggressively remove headers, footers, and cookie/modal overlays"""
        js = """
        () => {
            const selectors = [
                "header", "footer", 
                "#onetrust-banner-sdk", ".onetrust-banner-sdk", 
                "[id*='cookie']", "[class*='cookie']",
                "[id*='consent']", "[class*='consent']",
                "[id*='modal']", "[class*='modal']",
                "[id*='popup']", "[class*='popup']",
                ".brlbs-cmpnt-dialog-backdrop", "#BorlabsCookieBox",
                "#ccc-overlay", "#ccc", ".ccc-notify-buttons"
            ];
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => el.remove());
            });
            // Also kill fixed position elements that might cover screen
            document.querySelectorAll('*').forEach(el => {
                if (window.getComputedStyle(el).position === 'fixed' && el.clientHeight > 100) {
                     el.remove();
                }
            });
        }
        """
        try:
            await self.page.evaluate(js)
            await asyncio.sleep(0.5)
        except Exception:
            pass

    async def ask_llm(self, goal: str, content: str) -> Dict[str, Any]:
        """Query LLM for next action"""
        prompt = f"""
        You are a browsing agent. Your goal is: {goal}
        
        Past Actions:
        {json.dumps(self.history[-5:], indent=2)}
        
        Current Page HTML (simplified):
        {content}
        
        Return a JSON object with the next action. Format:
        {{
            "action": "click" | "type" | "scroll" | "wait" | "extract" | "press" | "finish",
            "selector": "css_selector (if needed)",
            "text": "text_to_type (if type)",
            "key": "key_to_press (e.g. Enter) (if press)",
            "data": {{ key: value }} (if extract),
            "reasoning": "why did you choose this action"
        }}
        
        If the goal is achieved or impossible, return "finish".
        Only return valid JSON.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4096
            )
            
            # Log Cost
            if response.usage:
                from src.universe.ops.cost_tracker import cost_tracker
                cost_tracker.log_usage(
                     model=self.model_name,
                     input_tokens=response.usage.prompt_tokens,
                     output_tokens=response.usage.completion_tokens,
                     provider="OpenAI/Compatible"
                )
            
            decision = json.loads(response.choices[0].message.content)
            logger.info(f"LLM Decision: {json.dumps(decision, indent=2)}")
            return decision
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return {"action": "finish", "reasoning": "Error calling LLM"}

    async def execute_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute the action decided by LLM. Returns True if task should continue."""
        action = action_data.get("action")
        selector = action_data.get("selector")
        
        logger.info(f"Executing: {action} on {selector} ({action_data.get('reasoning')})")
        
        self.history.append(f"Action: {action}, Selector: {selector}, Reasoning: {action_data.get('reasoning')}")
        
        try:
            if action == AgentAction.CLICK:
                try:
                    await self.page.click(selector, timeout=5000)
                except Exception as e:
                    logger.warning(f"Standard click failed ({e}), trying force click...")
                    try:
                        await self.page.click(selector, timeout=5000, force=True)
                    except Exception as e2:
                        # Fallback: Check if it's a link and navigate directly
                        try:
                            href = await self.page.get_attribute(selector, "href")
                            if href:
                                logger.info(f"Click failed. Fallback: navigating to {href}")
                                if not href.startswith("http"):
                                    # Handle relative paths if needed, but usually absolute
                                    pass 
                                await self.page.goto(href, timeout=60000)
                                await self.page.wait_for_load_state("domcontentloaded")
                                return True
                        except Exception as fb_err:
                            logger.error(f"Fallback navigation failed: {fb_err}")
                        logger.warning(f"Action failed: {e2}")
                        return True # Continue despite error
                
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            
            elif action == AgentAction.TYPE:
                await self.page.fill(selector, action_data.get("text", ""))
            
            elif action == AgentAction.SCROLL:
                await self.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
            
            elif action == AgentAction.WAIT:
                await asyncio.sleep(2)
                
            elif action == AgentAction.PRESS:
                # Press a key, e.g. "Enter"
                key = action_data.get("key", "Enter")
                if selector:
                     await self.page.press(selector, key)
                else:
                     await self.page.keyboard.press(key)
                await self.page.wait_for_load_state("networkidle", timeout=5000)

            elif action == AgentAction.EXTRACT:
                return True # Continue, maybe extract more? Or strictly finish?
                # Usually extract implies we got data, but might need pagination.
                # For now, let's assume extraction is returned to the caller.
            
            elif action == AgentAction.FINISH:
                return False
                
        except Exception as e:
            logger.warning(f"Action failed: {e}")
            # Identify if we should retry or fail? 
            # For this simple versions, we log and continue (likely LLM will try again or fail next turn)
            
        return True

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Main execution loop to be implemented by subclasses"""
        pass

async def search_web(query: str, max_results: int = 3) -> str:
    """
    Simple search helper using googlesearch-python or DuckDuckGo.
    """
    results = []
    
    # 1. Try Google Search (via scraping)
    try:
        from googlesearch import search
        # search() is synchronous, run in executor
        loop = asyncio.get_event_loop()
        # search yields URLs, get first N
        urls = await loop.run_in_executor(None, lambda: list(search(query, num_results=max_results, advanced=True)))
        
        # googlesearch advanced=True yields a SearchResult object with title, url, description
        # But wait, googlesearch-python might just yield strings if advanced=False.
        # Let's check docs: `search(term, num_results=10, lang="en")` yields URLs (strings).
        # Ah I installed `googlesearch-python` which is a wrapper. Let's see.
        
        # If it returns strings:
        if urls and isinstance(urls[0], str):
             results = [{"title": "", "href": u, "body": ""} for u in urls]
        # If it returns objects (some versions do):
        elif urls and hasattr(urls[0], 'url'):
             results = [{"title": u.title, "href": u.url, "body": u.description} for u in urls]

        if results:
            return json.dumps(results)
            
    except Exception as e:
        logger.warning(f"Google search failed: {e}")

    # 2. Fallback to DuckDuckGo
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        # Try text search
        ddg_results = ddgs.text(query, max_results=max_results)
        if ddg_results:
            return json.dumps(ddg_results)
    except Exception as e:
        logger.error(f"DDG search failed: {e}")
        
    return ""

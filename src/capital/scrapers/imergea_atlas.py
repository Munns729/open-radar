"""
IMERGEA PE/VC Atlas scraper for European PE firm discovery.
Free directory at https://imergea.com/atlas/atlas.html
Uses browser agent to filter by Europe and extract firm list.
"""
import logging
from typing import List, Dict, Any

from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

logger = logging.getLogger(__name__)


class IMERGEAAtlasScraper(BaseBrowsingAgent):
    """
    Scrapes the IMERGEA PE/VC Atlas for European PE and VC firms.
    Filters by Region=Europe, Type=PE (or VC), then extracts firm names and countries.
    """

    ATLAS_URL = "https://imergea.com/atlas/atlas.html"

    async def run(
        self,
        region: str = "Europe",
        firm_type: str = "PE",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Scrape European PE/VC firms from IMERGEA Atlas.
        Returns list of dicts with keys: name, country, region, firm_type.
        """
        results = []
        await self.start()

        try:
            await self.page.goto(self.ATLAS_URL, timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(3000)  # Let dynamic content load

            # Try to extract firms from the page
            # The Atlas uses filters - we need to select Europe, then extract the list
            content = await self.get_page_content()

            # Look for firm names in the content - they often appear in list items or cards
            # Fallback: use LLM to extract any firm names from the visible content
            goal = f"""
            You are on the IMERGEA PE/VC Atlas (imergea.com/atlas).
            The page shows a directory of Private Equity and Venture Capital firms.

            GOAL: Extract the list of PE/VC firm names visible on the page.
            - Look for firm names in any list, table, cards, or grid.
            - Each firm should have: name (required), country (if visible), region (if visible).
            - Ignore "Loading..." or placeholder text.
            - If filters are visible (Region, Country, Sector), the user may need to SELECT "Europe" first - but if data is already shown, extract it.

            If you see a Region/Country filter dropdown, your first action should be CLICK to open it and select "Europe".
            If you see firm names in a list, EXTRACT them.

            FORMAT for extract: "data": [ {{ "name": "Firm Name", "country": "UK" }}, ... ]
            Return ONLY actual firm names from the page, not generic labels.
            """

            steps = 0
            max_steps = 12

            while steps < max_steps:
                content = await self.get_page_content()
                decision = await self.ask_llm(goal, content[:25000])

                if decision.get("action") == AgentAction.EXTRACT:
                    data = decision.get("data", {})
                    if isinstance(data, dict):
                        data = data.get("firms", data.get("data", [data]))
                    if not isinstance(data, list):
                        data = [data] if data else []

                    for item in data:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("Name")
                        else:
                            name = str(item)
                        if name and len(name) > 2 and "loading" not in name.lower():
                            results.append({
                                "name": name.strip() if isinstance(name, str) else str(name),
                                "country": item.get("country", item.get("Country", "")) if isinstance(item, dict) else "",
                                "region": region,
                                "hq_country": item.get("country", item.get("Country", "EU")) if isinstance(item, dict) else "EU",
                            })

                    if results:
                        break

                should_continue = await self.execute_action(decision)
                if not should_continue:
                    break
                steps += 1
                await self.page.wait_for_timeout(1500)

            # Deduplicate by name
            seen = set()
            unique = []
            for r in results[:limit]:
                n = (r.get("name") or "").strip()
                if n and n not in seen:
                    seen.add(n)
                    unique.append(r)

            logger.info("IMERGEA Atlas returned %d European firms", len(unique))
            return unique

        except Exception as e:
            logger.warning("IMERGEA Atlas scrape failed: %s", e)
            return []
        finally:
            await self.stop()

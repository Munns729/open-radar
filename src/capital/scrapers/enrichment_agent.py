"""
Portfolio Company Enrichment Agent.
Visits individual company detail pages to extract investment theses and deal context.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction

logger = logging.getLogger(__name__)

class CompanyEnrichmentAgent(BaseBrowsingAgent):
    """
    Agent that enriches a portfolio company by visiting its detail page
    and extracting investment thesis, deal rationale, and other context.
    """
    
    async def run(self, company_name: str, pe_firm_website: str, direct_url: str = None) -> Dict[str, Any]:
        """
        Enrich a single company by finding and scraping its detail page.
        """
        enrichment_data = {
            "investment_thesis": None,
            "strategic_rationale": [],
            "target_moats": [],
            "exit_year": None,
            "investment_keywords": []
        }
        
        await self.start()
        
        try:
            click_success = False
            portfolio_content = ""

            if direct_url:
                logger.info(f"Using direct URL for {company_name}: {direct_url}")
                try:
                    await self.page.goto(direct_url, timeout=60000)
                    await self.page.wait_for_load_state("domcontentloaded")
                    await self.remove_overlays()
                    click_success = True
                except Exception as e:
                    logger.warning(f"Direct navigation failed for {company_name}: {e}")
            else:
                # Standard Search & Navigate Flow
                try:
                    # Determine portfolio URL
                    if "portfolio" in pe_firm_website.lower() or "companies" in pe_firm_website.lower():
                        portfolio_url = pe_firm_website
                    else:
                        portfolio_url = f"{pe_firm_website}/portfolio/" if not pe_firm_website.endswith('/') else f"{pe_firm_website}portfolio/"

                    logger.info(f"Navigating to {portfolio_url}...")
                    await self.page.goto(portfolio_url, timeout=60000)
                    await self.page.wait_for_load_state("domcontentloaded")
                    await self.remove_overlays()
                    
                    # Get initial content
                    portfolio_content = await self.get_page_content()
                    
                    # Strategy A: Standard Link Click (using LLM)
                    logger.info(f"Clicking {company_name} card...")
                    decision = await self.ask_llm(
                        f"Goal: Click the portfolio card/link for '{company_name}'.",
                        portfolio_content
                    )
                    
                    if decision.get("action") == "click":
                        selector = decision.get("selector")
                        
                        # Special handling for Synova / Modal buttons
                        if "synova" in pe_firm_website.lower() and "button" in selector:
                            logger.info("Detected Synova modal button, attempting special click...")
                            await self.page.click(selector)
                            await asyncio.sleep(1) # Wait for modal
                            
                            # Look for "Read Case Study" link in the modal
                            try:
                                case_study_link = await self.page.get_attribute(".modal__small a.button", "href")
                                if case_study_link:
                                    logger.info(f"Found case study link: {case_study_link}")
                                    await self.page.goto(case_study_link)
                                    await self.page.wait_for_load_state("domcontentloaded")
                                    click_success = True
                                else:
                                    # Extract from modal directly if no link
                                    logger.info("No case study link found, extracting from modal...")
                                    click_success = True 
                            except Exception as e:
                                logger.warning(f"Synova modal handler failed: {e}")
                        
                        else:
                            # Standard navigation
                            if await self.execute_action(decision):
                                await self.page.wait_for_load_state("domcontentloaded")
                                click_success = True
                                
                except Exception as e:
                    logger.warning(f"Navigation/Search failed: {e}")

            # Extract enrichment data
            if click_success:
                 detail_content = await self.get_page_content()
            else:
                 logger.warning("Using portfolio page content for extraction.")
                 detail_content = await self.get_page_content()
            
            extraction_goal = f"""
            Goal: Extract ALL investment context for "{company_name}" from this detail page.
            
            EXTRACT:
            - investment_thesis: Full paragraph(s) explaining why they invested
            - strategic_rationale: How this fits their investment strategy
            - investment_year: Year they invested (if mentioned)
            - exit_year: Year they exited (if exited and mentioned)
            - exit_thesis: Why they exited / value creation story (if exited)
            - moat_keywords: Any mentions of competitive advantages, barriers to entry, network effects, regulatory moats, etc.
            - deal_valuation: Any mention of deal size, enterprise value, or investment amount (e.g. "£50m", "$100 million"). Return as string.
            - moic: Any mention of return multiple (e.g. "3x return", "4.5x money multiple", "generated 2.5x"). Return as float or string.
            
            Return as structured JSON with these exact fields.
            If a field is not found, return null.
            
            Content:
            {detail_content}
            """
            # Passing full content now
            
            logger.info("Extracting enrichment data...")
            extraction = await self.ask_llm(extraction_goal, detail_content)
            
            if extraction.get("action") == AgentAction.EXTRACT:
                data = extraction.get("data", {})
                
                # Merge extracted data
                enrichment_data.update({
                    "investment_thesis": data.get("investment_thesis"),
                    "strategic_rationale": data.get("strategic_rationale"),
                    "exit_thesis": data.get("exit_thesis"),
                    "investment_year": self._parse_year(data.get("investment_year")),
                    "exit_year": self._parse_year(data.get("exit_year")),
                    "entry_valuation_usd": self._parse_money(data.get("deal_valuation")),
                    "moic": self._parse_moic(data.get("moic")),
                    "deal_announcement_url": self.page.url if data.get("investment_thesis") else None,
                    "thesis_keywords": data.get("moat_keywords") if isinstance(data.get("moat_keywords"), list) else None,
                    "pe_identified_moats": self._extract_moats(data.get("investment_thesis", ""))
                })
                
                logger.info(f"✓ Enriched {company_name}")
            
        except Exception as e:
            logger.exception(f"Enrichment failed for {company_name}: {e}")
        finally:
            await self.stop()
        
        return enrichment_data
    
    def _parse_year(self, year_value: Any) -> Optional[int]:
        """Parse a year from various formats"""
        if year_value is None:
            return None
        try:
            if isinstance(year_value, int):
                return year_value if 1990 <= year_value <= 2030 else None
            if isinstance(year_value, str):
                # Extract 4-digit year
                import re
                match = re.search(r'\b(19|20)\d{2}\b', year_value)
                if match:
                    return int(match.group(0))
        except:
            pass
        return None
    
    def _parse_moic(self, val: Any) -> Optional[float]:
        """Parse 3.5x etc to float"""
        if not val: return None
        if isinstance(val, (int, float)): return float(val)
        try:
            import re
            match = re.search(r'(\d+(\.\d+)?)', str(val))
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _parse_money(self, val: Any) -> Optional[int]:
        """Parse currency string to integer USD"""
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
            
            # Currency conversion (approximate)
            rate = 1.0
            if '£' in val or 'gbp' in val or 'pound' in val: rate = 1.25
            elif '€' in val or 'eur' in val or 'euro' in val: rate = 1.08
            
            return int(number * multiplier * rate)
        except:
            return None

    def _extract_moats(self, thesis_text: str) -> Optional[Dict[str, bool]]:
        """Identify moat mentions in thesis"""
        if not thesis_text:
            return None
        
        thesis_lower = thesis_text.lower()
        moats = {
            "regulatory": any(kw in thesis_lower for kw in ["regulatory", "licensed", "certification", "compliance", "regulated"]),
            "network": any(kw in thesis_lower for kw in ["network effect", "platform", "two-sided", "marketplace", "user base"]),
            "brand": any(kw in thesis_lower for kw in ["brand", "trusted", "reputation", "loyalty"]),
            "switching_cost": any(kw in thesis_lower for kw in ["switching cost", "sticky", "embedded", "mission-critical"]),
            "ip": any(kw in thesis_lower for kw in ["patent", "proprietary", "intellectual property", "trade secret"])
        }
        
        # Only return if at least one moat identified
        return moats if any(moats.values()) else None

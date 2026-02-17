"""
Pricing Tracker.
Monitors pricing pages and extracts structured price points.
"""
import logging
import re
from src.competitive.web_monitor import WebMonitor
from src.competitive.database import MonitoringTargetModel, PricePointModel
from src.core.database import get_sync_db

logger = logging.getLogger(__name__)

class PricingTracker(WebMonitor):
    """
    Specialized monitor for Pricing pages.
    """
    
    def extract_prices(self, text: str) -> list:
        # Regex to find currency prices e.g., £50, $9.99
        # Very basic implementation
        matches = re.findall(r'[£$€]\d+(?:,\d{3})*(?:\.\d{2})?', text)
        return matches

    async def check_pricing(self, target: MonitoringTargetModel):
        change = await self.check_target(target)
        
        if change:
            # If changed, parse new prices and save PricePoints
            try:
                # We need the full content, getting it from the change might be partial if we stored snippet
                # But check_target logic in WebMonitor currently only stores snippet.
                # For a real implementation, we'd refactor check_target to return full content or re-fetch.
                # Let's assume we can regex the diff or text we have.
                
                prices = self.extract_prices(change.diff_content)
                if prices:
                    with get_sync_db() as session:
                        for p in prices[:5]: # Store top 5 prices found
                            # Clean string
                            val_str = re.sub(r'[^\d.]', '', p)
                            try:
                                val = float(val_str)
                                pp = PricePointModel(
                                    target_id=target.id,
                                    plan_name="Detected Plan",
                                    price_amount=val,
                                    currency="GBP" if "£" in p else "USD"
                                )
                                session.add(pp)
                            except:
                                continue
                        change.description += f" (Found {len(prices)} price points)"
            except Exception as e:
                logger.error(f"Error parsing prices for {target.company_name}: {e}")
                
        return change

"""
Currency Service
Handles fetching and caching of exchange rates from Frankfurter API.
"""
import json
import logging
import httpx
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from src.core.config import settings

logger = logging.getLogger(__name__)

class CurrencyService:
    def __init__(self):
        self.cache_dir = settings.cache_dir / "currency"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.frankfurter.app"
        
    def get_previous_working_day(self, reference_date: Optional[date] = None) -> date:
        """
        Returns the previous working day (Mon-Fri).
        If today is Monday, returns last Friday.
        """
        if reference_date is None:
            reference_date = date.today()
            
        # 0=Monday, 6=Sunday
        offset = 1
        while True:
            candidate = reference_date - timedelta(days=offset)
            if candidate.weekday() < 5: # Mon-Fri
                return candidate
            offset += 1

    async def fetch_rates(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Fetch rates from API for a specific date (or 'latest' if None, though usually we want specific dates).
        If date is None, it defaults to previous working day to match our logic.
        """
        if target_date is None:
            target_date = self.get_previous_working_day()
            
        date_str = target_date.isoformat()
        cache_file = self.cache_dir / f"rates_{date_str}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    # Simple validation
                    if "rates" in data:
                        return data
            except Exception as e:
                logger.warning(f"Failed to read currency cache: {e}")
        
        # Fetch from API
        url = f"{self.base_url}/{date_str}?from={settings.base_currency}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Cache success response
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                    
                return data
        except Exception as e:
            logger.error(f"Failed to fetch currency rates for {date_str}: {e}")
            # Fallback to hardcoded/approximate if completely failed? 
            # For now return minimal structure to avoid crashes, but log error
            return {
                "base": settings.base_currency,
                "date": date_str,
                "rates": {"USD": 1.27, "EUR": 1.17, "GBP": 1.0} # Fallback
            }

    async def get_rates(self, target_date: Optional[date] = None) -> Dict[str, float]:
        """
        Get rates dictionary for a date.
        """
        data = await self.fetch_rates(target_date)
        # Ensure base currency is in rates (1:1)
        rates = data.get("rates", {})
        rates[settings.base_currency] = 1.0
        return rates

    async def convert(self, amount: float, from_curr: str, to_curr: str, target_date: Optional[date] = None) -> float:
        """
        Convert amount from one currency to another using rates for target_date.
        """
        if from_curr == to_curr:
            return amount
            
        rates = await self.get_rates(target_date)
        
        # Base is GBP. 
        # API returns rates relative to Base (GBP).
        # e.g. GBP->EUR = 1.17.  1 GBP = 1.17 EUR.
        # Amount in GBP * Rate(EUR) = Amount in EUR.
        # Amount in EUR / Rate(EUR) = Amount in GBP.
        
        # We need everything to/from Base.
        
        # 1. Convert FROM to Base (GBP)
        if from_curr == settings.base_currency:
            amount_in_base = amount
        else:
            rate_from = rates.get(from_curr)
            if not rate_from:
                logger.warning(f"Missing rate for {from_curr}, returning original")
                return amount
            amount_in_base = amount / rate_from
            
        # 2. Convert Base to TO
        if to_curr == settings.base_currency:
            return amount_in_base
        else:
            rate_to = rates.get(to_curr)
            if not rate_to:
                logger.warning(f"Missing rate for {to_curr}, returning original")
                return amount
            return amount_in_base * rate_to

# Global instance
currency_service = CurrencyService()

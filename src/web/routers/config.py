"""
Config Router
Handles global configuration and preferences.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import date

from src.core.config import settings
from src.core.currency import currency_service
from src.core.thesis import thesis_config

router = APIRouter(
    prefix="/config",
    tags=["Config"]
)

class CurrencyConfig(BaseModel):
    base_currency: str
    preferred_currency: str
    currency_date: Optional[date]
    rates: Dict[str, float]

class UpdateCurrencyConfig(BaseModel):
    preferred_currency: str
    currency_date: Optional[date] = None

@router.get("/currency", response_model=CurrencyConfig)
async def get_currency_config():
    """
    Get current currency configuration and rates.
    """
    # Resolve date
    target_date = None
    if settings.currency_date:
        try:
             target_date = date.fromisoformat(settings.currency_date)
        except:
             pass
    
    # If no date set, use previous working day (default for display)
    resolved_date = target_date or currency_service.get_previous_working_day()
    
    # Fetch rates
    rates = await currency_service.get_rates(resolved_date)
    
    return CurrencyConfig(
        base_currency=settings.base_currency,
        preferred_currency=settings.preferred_currency,
        currency_date=resolved_date,
        rates=rates
    )

@router.get("/thesis")
async def get_thesis_config():
    """
    Get the active investment thesis configuration.
    Returns dimension weights, tier thresholds, and metadata.
    """
    return thesis_config.to_summary()


@router.post("/currency")
async def update_currency_config(config: UpdateCurrencyConfig):
    """
    Update currency preferences.
    """
    settings.preferred_currency = config.preferred_currency
    if config.currency_date:
        settings.currency_date = config.currency_date.isoformat()
    else:
        settings.currency_date = None
        
    return {"status": "updated", "config": config}

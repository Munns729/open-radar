"""Public service interface for the Deal Intelligence module.

Other modules should import from here, not from deal_intelligence.database directly.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.deal_intelligence.database import DealRecord, MarketMetrics, DealProbability


async def get_deal_records(
    sector: Optional[str] = None, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get deal records, optionally filtered by sector. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(DealRecord)
        if sector:
            stmt = stmt.where(DealRecord.sector.ilike(sector))
        stmt = stmt.order_by(DealRecord.deal_date.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return [d.to_dict() for d in result.scalars().all()]


async def get_market_metrics(sector: str) -> List[Dict[str, Any]]:
    """Get market metrics for a specific sector. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(MarketMetrics).where(
            MarketMetrics.sector.ilike(sector)
        ).order_by(MarketMetrics.time_period.desc())
        
        result = await session.execute(stmt)
        return [m.to_dict() for m in result.scalars().all()]


async def get_deal_probability(company_id: int) -> Optional[Dict[str, Any]]:
    """Get deal probability score for a target company by ID. Returns dict or None."""
    async with get_async_db() as session:
        stmt = select(DealProbability).where(
            DealProbability.target_company_id == company_id
        )
        result = await session.execute(stmt)
        prob = result.scalar_one_or_none()
        return prob.to_dict() if prob else None

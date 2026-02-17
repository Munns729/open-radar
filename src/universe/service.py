"""Public service interface for the Universe module.

Other modules should import from here, not from universe.database directly.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.universe.database import CompanyModel
from src.core.models import CompanyTier


async def get_company_by_id(company_id: int) -> Optional[Dict[str, Any]]:
    """Get a single company by ID. Returns dict or None."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        company = result.scalar_one_or_none()
        return company.to_dict() if company else None


async def get_companies_by_tier(
    tiers: List[str], 
    limit: int = 50, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get companies filtered by tier. Returns list of dicts."""
    tier_enums = []
    for t in tiers:
        if t == "1A": tier_enums.append(CompanyTier.TIER_1A)
        elif t == "1B": tier_enums.append(CompanyTier.TIER_1B)
        elif t == "2": tier_enums.append(CompanyTier.TIER_2)
    
    async with get_async_db() as session:
        stmt = select(CompanyModel)
        if tier_enums:
            stmt = stmt.where(CompanyModel.tier.in_(tier_enums))
        stmt = stmt.limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return [c.to_dict() for c in result.scalars().all()]


async def get_company_count(tier: Optional[str] = None) -> int:
    """Get count of companies, optionally filtered by tier."""
    async with get_async_db() as session:
        stmt = select(func.count(CompanyModel.id))
        if tier:
            tier_map = {"1A": CompanyTier.TIER_1A, "1B": CompanyTier.TIER_1B, "2": CompanyTier.TIER_2}
            if tier in tier_map:
                stmt = stmt.where(CompanyModel.tier == tier_map[tier])
        result = await session.execute(stmt)
        return result.scalar() or 0


async def search_companies(
    query: str, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search companies by name. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(CompanyModel).where(
            CompanyModel.name.ilike(f"%{query}%")
        ).limit(limit)
        result = await session.execute(stmt)
        return [c.to_dict() for c in result.scalars().all()]

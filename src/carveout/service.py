"""Public service interface for the Carveout module.

Other modules should import from here, not from carveout.database directly.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import get_async_db
from src.carveout.database import CorporateParent, Division, CarveoutSignal

async def get_corporate_parents(
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get corporate parents. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(CorporateParent).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return [p.to_dict() for p in result.scalars().all()]

async def get_corporate_parent_by_id(parent_id: int) -> Optional[Dict[str, Any]]:
    """Get a single corporate parent by ID. Returns dict or None."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CorporateParent).where(CorporateParent.id == parent_id)
        )
        parent = result.scalar_one_or_none()
        return parent.to_dict() if parent else None

async def get_divisions_by_parent(parent_id: int) -> List[Dict[str, Any]]:
    """Get divisions for a specific parent. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(Division).where(Division.parent_id == parent_id)
        result = await session.execute(stmt)
        return [d.to_dict() for d in result.scalars().all()]

async def get_carveout_candidates(
    min_probability: int = 50,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get divisions with high carveout probability."""
    async with get_async_db() as session:
        stmt = (
            select(Division)
            .where(Division.carveout_probability >= min_probability)
            .order_by(Division.carveout_probability.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return [d.to_dict() for d in result.scalars().all()]

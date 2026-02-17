"""Public service interface for the Capital module.

Other modules should import from here, not from capital.database directly.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.capital.database import PEFirmModel, PEInvestmentModel


async def get_pe_firm_by_id(firm_id: int) -> Optional[Dict[str, Any]]:
    """Get a single PE firm by ID. Returns dict or None."""
    async with get_async_db() as session:
        result = await session.execute(
            select(PEFirmModel).where(PEFirmModel.id == firm_id)
        )
        firm = result.scalar_one_or_none()
        return firm.to_dict() if firm else None


async def get_pe_firms(
    limit: int = 50, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get PE firms. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(PEFirmModel).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return [f.to_dict() for f in result.scalars().all()]


async def get_investments_by_firm(firm_id: int) -> List[Dict[str, Any]]:
    """Get investments for a specific PE firm. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(PEInvestmentModel).where(
            PEInvestmentModel.pe_firm_id == firm_id
        )
        result = await session.execute(stmt)
        return [i.to_dict() for i in result.scalars().all()]


async def get_investment_by_company_name(
    name: str, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search for investments by portfolio company name."""
    async with get_async_db() as session:
        stmt = select(PEInvestmentModel).where(
            PEInvestmentModel.company_name.ilike(f"%{name}%")
        ).limit(limit)
        result = await session.execute(stmt)
        return [i.to_dict() for i in result.scalars().all()]

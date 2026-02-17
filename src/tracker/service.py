"""Public service interface for the Tracker module.

Other modules should import from here, not from tracker.database directly.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.tracker.database import TrackedCompany, CompanyEvent, TrackingAlert


async def get_tracked_companies(
    status: Optional[str] = None, 
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get tracked companies, optionally filtered by status. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(TrackedCompany)
        if status:
            stmt = stmt.where(TrackedCompany.tracking_status == status)
        stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        return [c.to_dict() for c in result.scalars().all()]


async def get_tracked_company(tracked_id: int) -> Optional[Dict[str, Any]]:
    """Get tracked company by ID. Returns dict or None."""
    async with get_async_db() as session:
        result = await session.execute(
            select(TrackedCompany).where(TrackedCompany.id == tracked_id)
        )
        company = result.scalar_one_or_none()
        return company.to_dict() if company else None


async def get_events_for_company(
    tracked_id: int, 
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get events for a specific tracked company. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(CompanyEvent).where(
            CompanyEvent.tracked_company_id == tracked_id
        )
        if since:
            stmt = stmt.where(CompanyEvent.event_date >= since.date())
        stmt = stmt.order_by(CompanyEvent.event_date.desc())
        
        result = await session.execute(stmt)
        return [e.to_dict() for e in result.scalars().all()]


async def get_unread_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """Get unread tracking alerts. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(TrackingAlert).where(
            TrackingAlert.is_read == False
        ).order_by(TrackingAlert.created_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return [a.to_dict() for a in result.scalars().all()]

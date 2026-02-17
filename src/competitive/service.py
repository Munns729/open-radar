"""Public service interface for the Competitive module.

Other modules should import from here, not from competitive.database directly.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.competitive.database import VCAnnouncementModel, ThreatScoreModel


async def get_announcements(
    limit: int = 20, 
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get VC announcements. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(VCAnnouncementModel)
        if since:
            stmt = stmt.where(VCAnnouncementModel.announced_date >= since.date())
        stmt = stmt.order_by(VCAnnouncementModel.announced_date.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return [a.to_dict() for a in result.scalars().all()]


async def get_threat_scores(company_id: int) -> List[Dict[str, Any]]:
    """
    Get threat scores for a specific universe company.
    
    TODO: The current schema for ThreatScoreModel and VCAnnouncementModel does not 
    link back to a universe company_id. This function currently matches nothing 
    to preserve safety until schema migration.
    """
    return [] 
async def get_threats_by_level(levels: List[str]) -> List[Dict[str, Any]]:
    """Get threat scores by level (e.g. ['critical', 'high']). Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(ThreatScoreModel).filter(
            ThreatScoreModel.threat_level.in_(levels)
        ).order_by(ThreatScoreModel.threat_score.desc())
        
        result = await session.execute(stmt)
        return [t.__dict__ for t in result.scalars().all()] # Quick dict conversion for now

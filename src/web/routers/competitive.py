"""Competitive router — VC threat feed and firm tracking."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitive.database import VCAnnouncementModel, ThreatScoreModel, VCFirmModel
from src.core.database import get_db
from src.core.schemas import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/competitive", tags=["Competitive"])


@router.get("/feed", response_model=StandardResponse[list], summary="Competitive Feed")
async def get_competitive_feed(
    limit: int = 50,
    firm_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get feed of competitive threats and announcements."""
    try:
        stmt = (
            select(ThreatScoreModel, VCAnnouncementModel, VCFirmModel)
            .join(VCAnnouncementModel, ThreatScoreModel.announcement_id == VCAnnouncementModel.id)
            .join(VCFirmModel, VCAnnouncementModel.vc_firm_id == VCFirmModel.id)
        )
        if firm_id:
            stmt = stmt.where(VCFirmModel.id == firm_id)
        stmt = stmt.order_by(desc(ThreatScoreModel.created_at)).limit(limit)

        result = await db.execute(stmt)

        data = [
            {
                "id": threat.id,
                "type": "threat",
                "company": announcement.company_name,
                "competitor": firm.name,
                "competitor_id": firm.id,
                "threat_level": threat.threat_level,
                "score": threat.threat_score,
                "description": threat.reasoning,
                "date": threat.created_at,
            }
            for threat, announcement, firm in result.all()
        ]
        return StandardResponse(data=data)
    except Exception:
        logger.exception("Competitive feed error")
        raise HTTPException(status_code=500, detail="Failed to load competitive feed")


@router.get("/firms", response_model=StandardResponse[list], summary="Competitive Firms")
async def get_competitive_firms(db: AsyncSession = Depends(get_db)):
    """Get list of VC firms with their threat stats."""
    try:
        stmt = (
            select(
                VCFirmModel,
                func.count(ThreatScoreModel.id).label("threat_count"),
                func.max(ThreatScoreModel.created_at).label("last_threat"),
            )
            .outerjoin(VCAnnouncementModel, VCFirmModel.id == VCAnnouncementModel.vc_firm_id)
            .outerjoin(ThreatScoreModel, VCAnnouncementModel.id == ThreatScoreModel.announcement_id)
            .group_by(VCFirmModel.id)
            .order_by(desc("last_threat"), VCFirmModel.name)
        )
        result = await db.execute(stmt)

        data = [
            {
                "id": firm.id,
                "name": firm.name,
                "tier": firm.tier,
                "focus_sectors": firm.focus_sectors,
                "threat_count": count,
                "last_activity": last_date,
            }
            for firm, count, last_date in result.all()
        ]
        return StandardResponse(data=data)
    except Exception:
        logger.exception("Error fetching competitive firms")
        raise HTTPException(status_code=500, detail="Failed to load firms")

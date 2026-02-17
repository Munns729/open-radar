"""Dashboard router — stats and activity feed."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, desc

from src.core.database import get_db
from src.core.schemas import StandardResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.universe.database import CompanyModel
from src.competitive.database import ThreatScoreModel, VCAnnouncementModel
from src.capital.database import PEInvestmentModel, PEFirmModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats", response_model=StandardResponse[dict], summary="Dashboard Stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_db)):
    """Get summary statistics for the dashboard."""
    company_count = await session.execute(select(func.count(CompanyModel.id)))
    total_companies = company_count.scalar() or 0

    tracked_stmt = select(func.count(CompanyModel.id)).where(CompanyModel.tier.isnot(None))
    tracked_count = await session.execute(tracked_stmt)
    tracked_companies = tracked_count.scalar() or 0

    try:
        alert_count = await session.execute(select(func.count(ThreatScoreModel.id)))
        active_alerts = alert_count.scalar() or 0
    except Exception:
        active_alerts = 0

    try:
        deal_count = await session.execute(select(func.count(PEInvestmentModel.id)))
        recent_deals = deal_count.scalar() or 0
    except Exception:
        recent_deals = 0

    return StandardResponse(data={
        "total_companies": total_companies,
        "tracked_companies": tracked_companies,
        "active_alerts": active_alerts,
        "recent_deals": recent_deals,
    })


@router.get("/activity", response_model=StandardResponse[list], summary="Recent Activity")
async def get_dashboard_activity(limit: int = 10, session: AsyncSession = Depends(get_db)):
    """Get recent activity feed for the dashboard."""
    activity = []

    try:
        threat_stmt = (
            select(ThreatScoreModel, VCAnnouncementModel)
            .join(VCAnnouncementModel, ThreatScoreModel.announcement_id == VCAnnouncementModel.id)
            .order_by(desc(ThreatScoreModel.created_at))
            .limit(limit // 2)
        )
        threat_result = await session.execute(threat_stmt)
        for threat, announcement in threat_result.all():
            activity.append({
                "id": f"threat-{threat.id}",
                "type": "competitive",
                "title": f"{threat.competitor_name} invested in {announcement.company_name}",
                "description": threat.reasoning[:100] if threat.reasoning else "",
                "timestamp": threat.created_at.isoformat() if threat.created_at else None,
                "icon": "Radio",
                "color": "text-orange-400",
            })
    except Exception:
        pass

    try:
        investment_stmt = (
            select(PEInvestmentModel, PEFirmModel)
            .join(PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id)
            .order_by(desc(PEInvestmentModel.entry_date))
            .limit(limit // 2)
        )
        investment_result = await session.execute(investment_stmt)
        for inv, firm in investment_result.all():
            amount_str = f"${(inv.entry_valuation_usd / 1000000):.1f}M" if inv.entry_valuation_usd else "Undisclosed"
            activity.append({
                "id": f"investment-{inv.id}",
                "type": "capital",
                "title": f"{firm.name} → {inv.company_name}",
                "description": f"{amount_str} investment in {inv.sector or 'Unknown sector'}",
                "timestamp": inv.entry_date.isoformat() if inv.entry_date else None,
                "icon": "Coins",
                "color": "text-emerald-400",
            })
    except Exception:
        pass

    activity.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return StandardResponse(data=activity[:limit])

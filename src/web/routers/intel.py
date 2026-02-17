"""Intel router — market intelligence items, trends, and weekly briefings."""

import logging

from fastapi import APIRouter
from typing import Optional
from sqlalchemy import select, desc

from src.core.database import get_db
from src.core.schemas import StandardResponse
from datetime import datetime
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.market_intelligence.database import IntelligenceItem, MarketTrend, WeeklyBriefing, ScoringConfigRecommendation, RegulatoryChange

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/intel",
    tags=["Market Intel"]
)


@router.get("/items", response_model=StandardResponse[dict], summary="Intelligence Items")
async def get_intelligence_items(
    category: Optional[str] = None, 
    limit: int = 20, 
    session: AsyncSession = Depends(get_db)
):
    """Get intelligence items with optional category filter."""
    stmt = select(IntelligenceItem).order_by(desc(IntelligenceItem.published_date))
    if category:
        stmt = stmt.where(IntelligenceItem.category == category)
    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    items = result.scalars().all()

    return StandardResponse(data={
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "summary": i.summary,
                "category": i.category,
                "relevance_score": i.relevance_score,
                "published_date": i.published_date.isoformat() if i.published_date else None,
                "url": i.url,
            }
            for i in items
        ],
        "total": len(items),
    })


@router.get("/trends", response_model=StandardResponse[dict], summary="Market Trends")
async def get_market_trends(limit: int = 10, session: AsyncSession = Depends(get_db)):
    """Get market trends ordered by recency."""
    stmt = select(MarketTrend).order_by(desc(MarketTrend.created_at)).limit(limit)
    result = await session.execute(stmt)
    trends = result.scalars().all()

    return StandardResponse(data={
        "trends": [
            {
                "id": t.id,
                "name": t.trend_name,
                "sector": t.sector,
                "type": t.trend_type,
                "strength": t.strength,
                "confidence": t.confidence,
                "implications": t.implications_for_thesis,
                "first_detected": t.first_detected.isoformat() if t.first_detected else None,
            }
            for t in trends
        ]
    })


@router.get("/briefing/latest", response_model=StandardResponse[dict], summary="Latest Briefing")
async def get_latest_briefing(session: AsyncSession = Depends(get_db)):
    """Get the most recent weekly briefing."""
    stmt = select(WeeklyBriefing).order_by(desc(WeeklyBriefing.week_starting)).limit(1)
    result = await session.execute(stmt)
    briefing = result.scalar_one_or_none()

    if not briefing:
        return StandardResponse(data=None, status="no_briefing", message="No briefings available yet")

    return StandardResponse(data={
        "week_starting": briefing.week_starting.isoformat(),
        "summary": briefing.executive_summary,
        "emerging_trends": briefing.emerging_trends,
        "action_items": briefing.action_items,
        "generated_at": briefing.generated_at.isoformat() if briefing.generated_at else None,
    })


@router.get("/recommendations", summary="List scoring config recommendations")
async def get_recommendations(
    status: Optional[str] = "pending",
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """
    List scoring config recommendations, filtered by status.
    Default shows pending recommendations awaiting review.
    """
    stmt = select(ScoringConfigRecommendation).order_by(
        desc(ScoringConfigRecommendation.created_at)
    )
    if status:
        stmt = stmt.where(ScoringConfigRecommendation.status == status)
    stmt = stmt.limit(limit)
    
    result = await session.execute(stmt)
    recs = result.scalars().all()
    
    # Enrich with regulatory change context
    items = []
    for rec in recs:
        rec_dict = {
            "id": rec.id,
            "regulatory_change_id": rec.regulatory_change_id,
            "config_target": rec.config_target,
            "action": rec.action,
            "key": rec.key,
            "current_value": rec.current_value,
            "recommended_value": rec.recommended_value,
            "sovereignty_relevant": rec.sovereignty_relevant,
            "reasoning": rec.reasoning,
            "confidence": rec.confidence,
            "status": rec.status,
            "reviewed_by": rec.reviewed_by,
            "reviewed_at": rec.reviewed_at.isoformat() if rec.reviewed_at else None,
            "review_notes": rec.review_notes,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
        }
        # Fetch the linked regulatory change for context
        change = await session.get(RegulatoryChange, rec.regulatory_change_id)
        if change:
            rec_dict["regulatory_change"] = {
                "title": change.title,
                "jurisdiction": change.jurisdiction,
                "regulatory_body": change.regulatory_body,
                "source_url": change.source_url,
                "effective_date": change.effective_date.isoformat() if change.effective_date else None,
            }
        items.append(rec_dict)
    
    return {
        "total": len(items),
        "status_filter": status,
        "recommendations": items,
    }


@router.post("/recommendations/{rec_id}/review", summary="Approve or reject a recommendation")
async def review_recommendation(
    rec_id: int,
    action: str,  # "approve" or "reject"
    notes: Optional[str] = None,
    reviewer: str = "admin",
    session: AsyncSession = Depends(get_db),
):
    """
    Approve or reject a scoring config recommendation.
    
    Approved recommendations are marked for manual implementation.
    """
    rec = await session.get(ScoringConfigRecommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")
    
    if rec.status != "pending":
        raise HTTPException(status_code=400, detail=f"Recommendation already {rec.status}")
    
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    rec.status = "approved" if action == "approve" else "rejected"
    rec.reviewed_by = reviewer
    rec.reviewed_at = datetime.utcnow()
    rec.review_notes = notes
    
    await session.commit()
    
    # If approved, log what the developer needs to do
    if rec.status == "approved":
        logger.info(
            f"[APPROVED] {rec.action} '{rec.key}' in {rec.config_target} "
            f"(value: {rec.recommended_value}). "
            f"Developer: update MoatScorer.{rec.config_target} in moat_scorer.py"
        )
    
    return {
        "id": rec.id,
        "status": rec.status,
        "reviewed_by": rec.reviewed_by,
        "implementation_note": (
            f"Update MoatScorer.{rec.config_target}: {rec.action} '{rec.key}' = {rec.recommended_value}"
            if rec.status == "approved" else None
        ),
    }


@router.get("/recommendations/summary", summary="Recommendation pipeline summary")
async def get_recommendations_summary(session: AsyncSession = Depends(get_db)):
    """Summary counts by status for the recommendations dashboard."""
    from sqlalchemy import func as sqla_func
    
    stmt = select(
        ScoringConfigRecommendation.status,
        sqla_func.count()
    ).group_by(ScoringConfigRecommendation.status)
    
    result = await session.execute(stmt)
    counts = {status: count for status, count in result.all()}
    
    return {
        "pending": counts.get("pending", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "superseded": counts.get("superseded", 0),
        "total": sum(counts.values()),
    }


@router.get("/regulatory-changes", summary="List regulatory changes")
async def get_regulatory_changes(
    jurisdiction: Optional[str] = None,
    moat_relevant: Optional[bool] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """List regulatory changes with optional filters."""
    stmt = select(RegulatoryChange).order_by(desc(RegulatoryChange.created_at))
    
    if jurisdiction:
        stmt = stmt.where(RegulatoryChange.jurisdiction == jurisdiction)
    if moat_relevant is not None:
        stmt = stmt.where(RegulatoryChange.creates_barriers_to_entry == moat_relevant)
    
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    changes = result.scalars().all()
    
    return {
        "total": len(changes),
        "changes": [
            {
                "id": c.id,
                "jurisdiction": c.jurisdiction,
                "regulatory_body": c.regulatory_body,
                "change_type": c.change_type,
                "title": c.title,
                "effective_date": c.effective_date.isoformat() if c.effective_date else None,
                "creates_barriers_to_entry": c.creates_barriers_to_entry,
                "source_url": c.source_url,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in changes
        ],
    }

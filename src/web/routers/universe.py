"""Universe router — company discovery, graph, and scanning."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import StandardResponse, PaginatedResponse
from src.universe.database import CompanyModel, CompanyRelationshipModel
from src.universe.workflow import build_universe
from src.web.dependencies import get_current_username

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/universe",
    tags=["Universe"]
)


class ScanRequest(BaseModel):
    mode: str = "full"
    sources: List[str] = ["Wikipedia", "Clutch", "GoodFirms"]
    enrichment_level: str = "full"
    countries: List[str] = ["FR", "DE"]
    min_revenue: Optional[int] = None
    limit: Optional[int] = 15


@router.post("/scan", summary="Trigger Universe Scan")
async def trigger_universe_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(get_current_username),
):
    """Trigger a universe scan in the background. Requires Auth."""
    async def run_scan():
        try:
            logger.info(f"Starting remote scan with sources={request.sources}, countries={request.countries}")
            await build_universe(
                mode=request.mode,
                sources=request.sources,
                min_revenue=request.min_revenue,
                countries=request.countries,
                limit=request.limit or 15,
            )
            logger.info("Remote scan completed successfully")
        except Exception as e:
            logger.error(f"Remote scan failed: {e}", exc_info=True)

    background_tasks.add_task(run_scan)
    return {"status": "success", "message": "Scan started in background"}


@router.get("/companies", response_model=PaginatedResponse[dict], summary="List Universe Companies")
async def get_companies(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    sector: Optional[str] = None,
    country: Optional[str] = None,
    min_moat: Optional[int] = None,
    is_enriched: Optional[bool] = None,
    is_scored: Optional[bool] = None,
    discovered_since_hours: Optional[int] = None,
    enriched_since_hours: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
):
    """List companies in the universe with advanced filters."""
    # Build query filters
    filters = []
    if search:
        filters.append(CompanyModel.name.ilike(f"%{search}%"))
    if tier:
        filters.append(CompanyModel.tier == tier)
    if sector:
        filters.append(CompanyModel.sector.ilike(f"%{sector}%"))
    if country:
        filters.append(CompanyModel.hq_country == country)
    if min_moat is not None:
        filters.append(CompanyModel.moat_score >= min_moat)
    if is_enriched is True:
        filters.append(and_(
            CompanyModel.description.isnot(None), 
            ~CompanyModel.description.startswith("Discovered on")
        ))
    elif is_enriched is False:
        filters.append(or_(
            CompanyModel.description.is_(None),
            CompanyModel.description.startswith("Discovered on")
        ))
    
    if is_scored is True:
        filters.append(CompanyModel.moat_score > 0)
    elif is_scored is False:
        # "not scored" = score is 0, NULL (insufficient data), or has insufficient_data status
        filters.append(or_(
            CompanyModel.moat_score.is_(None),
            CompanyModel.moat_score == 0,
        ))

    now = datetime.now(timezone.utc)
    if discovered_since_hours is not None:
        cutoff = (now - timedelta(hours=discovered_since_hours)).replace(tzinfo=None)
        filters.append(CompanyModel.created_at >= cutoff)
    if enriched_since_hours is not None:
        cutoff = (now - timedelta(hours=enriched_since_hours)).replace(tzinfo=None)
        filters.append(CompanyModel.last_updated >= cutoff)
        filters.append(CompanyModel.description.isnot(None))
        filters.append(~CompanyModel.description.startswith("Discovered on"))

    # Get total count
    count_stmt = select(func.count()).select_from(CompanyModel)
    if filters:
        count_stmt = count_stmt.where(*filters)
    
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get data
    stmt = select(CompanyModel)
    if filters:
        stmt = stmt.where(*filters)

    stmt = stmt.order_by(desc(CompanyModel.moat_score)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    companies = result.scalars().all()
    
    return PaginatedResponse(
        data=[c.to_dict() for c in companies],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/companies/{company_id}/scoring-history", summary="Get scoring audit trail")
async def get_scoring_history(
    company_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """
    Return the scoring history for a company, most recent first.
    Each event includes the full pillar breakdown, weights used,
    and a per-pillar diff showing what changed since the previous scoring.
    """
    from src.universe.database import ScoringEvent
    
    # Verify company exists
    company = await session.get(CompanyModel, company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    
    stmt = (
        select(ScoringEvent)
        .where(ScoringEvent.company_id == company_id)
        .order_by(desc(ScoringEvent.scored_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    events = result.scalars().all()
    
    moat_analysis = company.moat_analysis or {}
    scoring_status = moat_analysis.get("scoring_status") if isinstance(moat_analysis, dict) else None

    return {
        "company_id": company_id,
        "company_name": company.name,
        "current_score": company.moat_score,
        "current_tier": company.tier.value if company.tier else None,
        "scoring_status": scoring_status,  # "insufficient_data" or None (scored)
        "total_events": len(events),
        "events": [e.to_dict() for e in events],
    }


@router.get("/graph", response_model=StandardResponse[dict], summary="Universe Network Graph")
async def get_universe_graph(
    limit: int = 50,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    country: Optional[str] = None,
    min_moat: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
):
    """Get graph data (nodes and links) for the universe. Hub & Spoke retrieval."""
    stmt = select(CompanyModel)
    if search:
        stmt = stmt.where(CompanyModel.name.ilike(f"%{search}%"))
    if tier:
        stmt = stmt.where(CompanyModel.tier == tier)
    if country:
        stmt = stmt.where(CompanyModel.hq_country == country)
    if min_moat:
        stmt = stmt.where(CompanyModel.moat_score >= min_moat)

    stmt = stmt.order_by(desc(CompanyModel.moat_score)).limit(limit)
    hub_result = await session.execute(stmt)
    hubs = hub_result.scalars().all()
    hub_ids = [c.id for c in hubs]

    if not hub_ids:
        return StandardResponse(data={"nodes": [], "links": []})

    rel_stmt = select(CompanyRelationshipModel).where(
        or_(
            CompanyRelationshipModel.company_a_id.in_(hub_ids),
            CompanyRelationshipModel.company_b_id.in_(hub_ids),
        )
    )
    rel_result = await session.execute(rel_stmt)
    relationships = rel_result.scalars().all()

    all_ids = set(hub_ids)
    links = []
    for r in relationships:
        all_ids.add(r.company_a_id)
        all_ids.add(r.company_b_id)
        links.append({
            "source": r.company_a_id,
            "target": r.company_b_id,
            "type": r.relationship_type,
            "confidence": float(r.confidence or 0.5),
        })

    if not all_ids:
        return StandardResponse(data={"nodes": [], "links": []})

    nodes_stmt = select(CompanyModel).where(CompanyModel.id.in_(all_ids))
    nodes_result = await session.execute(nodes_stmt)
    all_companies = nodes_result.scalars().all()

    nodes = []
    for c in all_companies:
        is_hub = c.id in hub_ids
        nodes.append({
            "id": c.id,
            "name": c.name,
            "sector": c.sector,
            "sub_sector": c.sub_sector,
            "tier": c.tier,
            "hq_country": c.hq_country,
            "hq_city": c.hq_city,
            "moat_score": c.moat_score,
            "revenue": c.revenue_gbp,
            "is_hub": is_hub,
            "color": "#a855f7" if is_hub else "#64748b",
        })

    return StandardResponse(data={"nodes": nodes, "links": links})


@router.get("/recent-stats", response_model=StandardResponse[dict], summary="Recently Discovered & Enriched")
async def get_recent_stats(session: AsyncSession = Depends(get_db)):
    """Count companies discovered or enriched in the last 24h, 5 days, 30 days."""
    now = datetime.now(timezone.utc)
    windows = [
        ("24h", timedelta(hours=24)),
        ("5d", timedelta(days=5)),
        ("30d", timedelta(days=30)),
    ]
    result = {}
    for label, delta in windows:
        cutoff = now - delta
        # Naive datetime for DB columns that may be naive
        cutoff_naive = cutoff.replace(tzinfo=None) if cutoff.tzinfo else cutoff
        discovered_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.created_at >= cutoff_naive)
        discovered_res = await session.execute(discovered_stmt)
        result[f"discovered_{label}"] = discovered_res.scalar() or 0
        # Enriched = last_updated in window AND has real description (not placeholder)
        enriched_stmt = (
            select(func.count())
            .select_from(CompanyModel)
            .where(CompanyModel.last_updated >= cutoff_naive)
            .where(CompanyModel.description.isnot(None))
            .where(~CompanyModel.description.startswith("Discovered on"))
        )
        enriched_res = await session.execute(enriched_stmt)
        result[f"enriched_{label}"] = enriched_res.scalar() or 0
    return StandardResponse(data=result)


@router.get("/status", summary="Get Universe Scan Status")
async def get_status():
    """Get the current status of the universe scanner."""
    from src.universe.status import reporter
    return reporter.state


@router.get("/stats", summary="Get Universe Funnel Statistics")
async def get_stats(session: AsyncSession = Depends(get_db)):
    """Get statistics for the sourcing funnel."""
    # 1. Total Discovery
    total_stmt = select(func.count()).select_from(CompanyModel)
    total_result = await session.execute(total_stmt)
    total_discovery = total_result.scalar() or 0

    # 2. Excluded
    excluded_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.exclusion_reason.isnot(None))
    excluded_result = await session.execute(excluded_stmt)
    excluded = excluded_result.scalar() or 0

    # 3. Enriched
    enriched_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.description.isnot(None))
    enriched_result = await session.execute(enriched_stmt)
    enriched = enriched_result.scalar() or 0

    # 4. Scored
    scored_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.moat_score > 0)
    scored_result = await session.execute(scored_stmt)
    scored = scored_result.scalar() or 0

    # 5. Exclusion Breakdown
    exclusion_stmt = select(CompanyModel.exclusion_reason, func.count()).where(CompanyModel.exclusion_reason.isnot(None)).group_by(CompanyModel.exclusion_reason)
    exclusion_result = await session.execute(exclusion_stmt)
    exclusion_breakdown = {reason: count for reason, count in exclusion_result.all()}

    # 6. Tier Breakdown
    tier_stmt = select(CompanyModel.tier, func.count()).group_by(CompanyModel.tier)
    tier_result = await session.execute(tier_stmt)
    tier_breakdown = {tier: count for tier, count in tier_result.all()}

    # 7. Moat Range Breakdown
    # Exclude 0 (un-enriched/unscored)
    moat_ranges = [
        {"label": "1-20", "min": 1, "max": 20},
        {"label": "21-40", "min": 21, "max": 40},
        {"label": "41-60", "min": 41, "max": 60},
        {"label": "61-80", "min": 61, "max": 80},
        {"label": "81-100", "min": 81, "max": 100},
    ]
    moat_range_breakdown = {}
    for r in moat_ranges:
        stmt = select(func.count()).select_from(CompanyModel).where(
            CompanyModel.moat_score >= r["min"],
            CompanyModel.moat_score <= r["max"]
        )
        res = await session.execute(stmt)
        moat_range_breakdown[r["label"]] = res.scalar() or 0

    # 8. Sector Breakdown (Top 5 + Other)
    sector_stmt = select(CompanyModel.sector, func.count()).group_by(CompanyModel.sector).order_by(desc(func.count()))
    sector_result = await session.execute(sector_stmt)
    all_sectors = sector_result.all()
    
    top_sectors = {}
    other_sectors_count = 0
    for i, (sector, count) in enumerate(all_sectors):
        if i < 5:
            top_sectors[sector or "Unknown"] = count
        else:
            other_sectors_count += count
    if other_sectors_count > 0:
        top_sectors["Other"] = other_sectors_count

    # 9. Enrichment Status Granular
    # Enriched & Scored
    e_s_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.description.isnot(None), CompanyModel.moat_score > 0)
    e_s_res = await session.execute(e_s_stmt)
    
    # Enriched & Unscored (includes NULL/insufficient_data)
    e_u_stmt = select(func.count()).select_from(CompanyModel).where(
        CompanyModel.description.isnot(None),
        or_(CompanyModel.moat_score.is_(None), CompanyModel.moat_score == 0),
    )
    e_u_res = await session.execute(e_u_stmt)
    
    # Not Enriched (Pending)
    n_e_p_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.description.is_(None), CompanyModel.exclusion_reason.is_(None))
    n_e_p_res = await session.execute(n_e_p_stmt)
    
    # Not Enriched (Excluded)
    n_e_x_stmt = select(func.count()).select_from(CompanyModel).where(CompanyModel.description.is_(None), CompanyModel.exclusion_reason.isnot(None))
    n_e_x_res = await session.execute(n_e_x_stmt)

    return {
        "totalDiscovery": total_discovery,
        "excluded": excluded,
        "enriched": enriched,
        "scored": scored,
        "exclusionBreakdown": exclusion_breakdown,
        "tierBreakdown": tier_breakdown,
        "moatRangeBreakdown": moat_range_breakdown,
        "sectorBreakdown": top_sectors,
        "enrichmentStatus": {
            "Enriched & Scored": e_s_res.scalar() or 0,
            "Enriched & Unscored": e_u_res.scalar() or 0,
            "Pending": n_e_p_res.scalar() or 0,
            "Excluded": n_e_x_res.scalar() or 0
        }
    }

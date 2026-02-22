"""Thesis Validator router — interactive thesis validation and company analysis."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import StandardResponse
from src.core.thesis import thesis_config
from src.universe.database import CompanyModel, CertificationModel, ScoringEvent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/thesis",
    tags=["Thesis Validator"],
)


@router.get("/config", response_model=StandardResponse[dict], summary="Full Thesis Config")
async def get_thesis_config():
    """
    Return the active thesis configuration with full detail
    including pillar prompts, certification scores, and keywords.
    """
    pillars = {}
    for key, p in thesis_config.pillars.items():
        pillars[key] = {
            "name": p.name,
            "weight": p.weight,
            "description": p.description,
            "max_raw_score": p.max_raw_score,
            "evidence_threshold": p.evidence_threshold,
        }

    return StandardResponse(data={
        "name": thesis_config.name,
        "version": thesis_config.version,
        "description": thesis_config.description,
        "pillars": pillars,
        "tier_thresholds": thesis_config.tier_thresholds.model_dump(),
        "business_filters": {
            "min_revenue": thesis_config.business_filters.min_revenue,
            "max_revenue": thesis_config.business_filters.max_revenue,
            "min_employees": thesis_config.business_filters.min_employees,
            "max_employees": thesis_config.business_filters.max_employees,
        },
        "certification_count": len(thesis_config.certification_scores),
        "sovereignty_cert_count": len(thesis_config.sovereignty_certs),
    })


@router.get(
    "/validate/{company_id}",
    response_model=StandardResponse[dict],
    summary="Validate Company Against Thesis",
)
async def validate_company(
    company_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Run a company through the active thesis and return the full breakdown:
    pillar scores, evidence, deal screening, tier assignment, and scoring history.
    """
    # Fetch company
    company = await session.get(CompanyModel, company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    # Fetch certifications
    cert_stmt = select(CertificationModel).where(
        CertificationModel.company_id == company_id
    )
    cert_result = await session.execute(cert_stmt)
    certifications = cert_result.scalars().all()

    # Fetch scoring history (last 5)
    history_stmt = (
        select(ScoringEvent)
        .where(ScoringEvent.company_id == company_id)
        .order_by(desc(ScoringEvent.scored_at))
        .limit(5)
    )
    history_result = await session.execute(history_stmt)
    scoring_events = history_result.scalars().all()

    # --- Build pillar breakdown ---
    moat_attrs = company.moat_attributes or {}
    moat_analysis = company.moat_analysis or {}

    pillar_breakdown = []
    raw_scores = moat_analysis.get("raw_dimension_scores", {})
    weighted_contributions = moat_analysis.get("weighted_contributions", {})

    for key, pillar in thesis_config.pillars.items():
        attr = moat_attrs.get(key, {})
        pillar_breakdown.append({
            "key": key,
            "name": pillar.name,
            "weight": pillar.weight,
            "max_raw_score": pillar.max_raw_score,
            "evidence_threshold": pillar.evidence_threshold,
            "raw_score": raw_scores.get(key, 0),
            "weighted_contribution": weighted_contributions.get(key, 0),
            "present": attr.get("present", False),
            "justification": attr.get("justification", ""),
            "score": attr.get("score", 0),
        })

    # --- Deal screening ---
    deal_screening = moat_attrs.get("deal_screening", {})
    financial_fit = deal_screening.get("financial_fit", {"score": 0, "factors": []})
    competitive_pos = deal_screening.get("competitive_position", {"score": 0, "factors": []})

    # --- Risk ---
    risk_data = moat_attrs.get("risk_penalty", {})

    # --- Tier thresholds for visual ---
    thresholds = thesis_config.tier_thresholds.model_dump()

    return StandardResponse(data={
        "company": {
            "id": company.id,
            "name": company.name,
            "sector": company.sector,
            "sub_sector": company.sub_sector,
            "hq_country": company.hq_country,
            "hq_city": company.hq_city,
            "website": company.website,
            "revenue_gbp": company.revenue_gbp,
            "revenue_source": company.revenue_source,
            "ebitda_gbp": company.ebitda_gbp,
            "ebitda_margin": float(company.ebitda_margin) if company.ebitda_margin else None,
            "employees": company.employees,
            "moat_score": company.moat_score,
            "tier": company.tier.value if company.tier else None,
            "description": (company.description or "")[:500],
        },
        "thesis": {
            "name": thesis_config.name,
            "version": thesis_config.version,
        },
        "pillar_breakdown": pillar_breakdown,
        "deal_screening": {
            "financial_fit": financial_fit,
            "competitive_position": competitive_pos,
            "total_score": financial_fit.get("score", 0) + competitive_pos.get("score", 0),
        },
        "risk": {
            "present": risk_data.get("present", False),
            "justification": risk_data.get("justification", ""),
            "penalty": risk_data.get("score", 0),
        },
        "tier_thresholds": thresholds,
        "certifications": [
            {
                "type": c.certification_type,
                "issuing_body": c.issuing_body,
                "thesis_score": thesis_config.get_cert_score(c.certification_type or ""),
            }
            for c in certifications
        ],
        "scoring_history": [e.to_dict() for e in scoring_events],
        "analysis_metadata": {
            "thesis_name": moat_analysis.get("thesis"),
            "thesis_version": moat_analysis.get("thesis_version"),
            "reasoning": moat_analysis.get("reasoning", ""),
            "penalties_applied": moat_analysis.get("penalties_applied", 0),
        },
    })


@router.get("/leaderboard", response_model=StandardResponse[list], summary="Thesis Leaderboard")
async def get_leaderboard(
    limit: int = 20,
    tier: Optional[str] = None,
    sector: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Top companies ranked by thesis score with pillar highlights.
    Used by the leaderboard tab on the Thesis Validator page.
    """
    stmt = (
        select(CompanyModel)
        .where(CompanyModel.moat_score > 0)
        .order_by(desc(CompanyModel.moat_score))
    )

    if tier:
        stmt = stmt.where(CompanyModel.tier == tier)
    if sector:
        stmt = stmt.where(CompanyModel.sector.ilike(f"%{sector}%"))

    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    companies = result.scalars().all()

    data = []
    for c in companies:
        attrs = c.moat_attributes or {}
        analysis = c.moat_analysis or {}
        raw_scores = analysis.get("raw_dimension_scores", {})

        # Find strongest pillar
        strongest_pillar = None
        strongest_score = 0
        for key in thesis_config.pillar_names:
            s = raw_scores.get(key, 0)
            if s > strongest_score:
                strongest_score = s
                strongest_pillar = key

        data.append({
            "id": c.id,
            "name": c.name,
            "sector": c.sector,
            "hq_country": c.hq_country,
            "moat_score": c.moat_score,
            "tier": c.tier.value if c.tier else None,
            "revenue_gbp": c.revenue_gbp,
            "strongest_pillar": strongest_pillar,
            "strongest_pillar_score": strongest_score,
            "pillar_scores": raw_scores,
        })

    return StandardResponse(data=data)


@router.get(
    "/distribution",
    response_model=StandardResponse[dict],
    summary="Pillar Score Distribution",
)
async def get_pillar_distribution(session: AsyncSession = Depends(get_db)):
    """
    Aggregate pillar score distribution across all scored companies.
    Shows the average score per pillar and the percentage of companies
    where each pillar is 'present' (above evidence threshold).
    """
    stmt = select(CompanyModel).where(CompanyModel.moat_score > 0)
    result = await session.execute(stmt)
    companies = result.scalars().all()

    if not companies:
        return StandardResponse(data={
            "total_scored": 0,
            "pillars": {},
        })

    pillar_totals = {key: {"sum": 0, "present_count": 0} for key in thesis_config.pillar_names}

    for c in companies:
        analysis = c.moat_analysis or {}
        raw_scores = analysis.get("raw_dimension_scores", {})
        for key in thesis_config.pillar_names:
            score = raw_scores.get(key, 0)
            pillar_totals[key]["sum"] += score
            pillar = thesis_config.pillars[key]
            if score >= pillar.evidence_threshold:
                pillar_totals[key]["present_count"] += 1

    total = len(companies)
    pillar_stats = {}
    for key, data in pillar_totals.items():
        pillar_stats[key] = {
            "name": thesis_config.pillars[key].name,
            "weight": thesis_config.pillars[key].weight,
            "avg_score": round(data["sum"] / total, 1) if total else 0,
            "present_pct": round(data["present_count"] / total * 100, 1) if total else 0,
            "present_count": data["present_count"],
        }

    return StandardResponse(data={
        "total_scored": total,
        "pillars": pillar_stats,
    })

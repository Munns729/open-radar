"""AI Resilience router — assessments, automated scoring, portfolio matrix, flags."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import StandardResponse
from src.resilience import service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resilience", tags=["AI Resilience"])


class ManualAssessBody(BaseModel):
    capability_level: int
    substitution_score: int
    disintermediation_score: int
    amplification_score: int
    cost_disruption_score: int
    scarcity_classification: Optional[str] = None
    scarcity_rationale: Optional[str] = None
    assessment_notes: Optional[str] = None


class AssessAutomatedBody(BaseModel):
    capability_level: int


class AssessPortfolioBody(BaseModel):
    company_ids: list[int]


def _assessment_to_data(a):
    if a is None:
        return None
    return {
        "id": a.id,
        "company_id": a.company_id,
        "capability_level": a.capability_level,
        "assessed_at": a.assessed_at.isoformat() if a.assessed_at else None,
        "substitution_score": a.substitution_score,
        "disintermediation_score": a.disintermediation_score,
        "amplification_score": a.amplification_score,
        "cost_disruption_score": a.cost_disruption_score,
        "composite_score": a.composite_score,
        "overall_verdict": a.overall_verdict,
        "scarcity_classification": a.scarcity_classification,
        "scarcity_rationale": a.scarcity_rationale,
        "assessed_by": a.assessed_by,
        "assessment_notes": a.assessment_notes,
    }


def _flag_to_data(f):
    return {
        "id": f.id,
        "company_id": f.company_id,
        "capability_level": f.capability_level,
        "previous_verdict": f.previous_verdict,
        "new_verdict": f.new_verdict,
        "composite_delta": f.composite_delta,
        "flag_reason": f.flag_reason,
        "reviewed": f.reviewed,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("/{company_id}", response_model=StandardResponse[dict])
async def get_company_assessments(
    company_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Current assessments across all four levels."""
    levels = {}
    for level in (1, 2, 3, 4):
        a = await service.get_current_assessment(company_id, level)
        levels[str(level)] = _assessment_to_data(a)
    return StandardResponse(data={"company_id": company_id, "levels": levels})


@router.get("/{company_id}/trajectory", response_model=StandardResponse[dict])
async def get_company_trajectory(company_id: int):
    """Score history per level."""
    trajectory = await service.get_resilience_trajectory(company_id)
    return StandardResponse(data={"company_id": company_id, "trajectory": trajectory})


@router.post("/{company_id}/assess", response_model=StandardResponse[dict])
async def post_manual_assess(
    company_id: int,
    body: ManualAssessBody,
):
    """Record a manual assessment. composite_score and overall_verdict are computed server-side."""
    if body.capability_level not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="capability_level must be 1, 2, 3, or 4")
    for score in (
        body.substitution_score,
        body.disintermediation_score,
        body.amplification_score,
        body.cost_disruption_score,
    ):
        if not (1 <= score <= 5):
            raise HTTPException(status_code=400, detail="All dimension scores must be 1–5")
    try:
        assessment = await service.record_assessment(
            company_id=company_id,
            capability_level=body.capability_level,
            scores={
                "substitution_score": body.substitution_score,
                "disintermediation_score": body.disintermediation_score,
                "amplification_score": body.amplification_score,
                "cost_disruption_score": body.cost_disruption_score,
                "scarcity_classification": body.scarcity_classification,
                "scarcity_rationale": body.scarcity_rationale,
                "assessment_notes": body.assessment_notes,
            },
            assessed_by="manual",
        )
        return StandardResponse(data=_assessment_to_data(assessment))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{company_id}/assess-automated", response_model=StandardResponse[dict])
async def post_assess_automated(
    company_id: int,
    body: AssessAutomatedBody,
    background_tasks: BackgroundTasks,
):
    """Trigger automated LLM assessment for one company at one level. Returns immediately."""
    if body.capability_level not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="capability_level must be 1, 2, 3, or 4")

    async def run():
        try:
            await service.run_automated_assessment(company_id, body.capability_level)
        except Exception:
            logger.exception("Automated resilience assessment failed company_id=%s level=%s", company_id, body.capability_level)

    background_tasks.add_task(run)
    return StandardResponse(data={"status": "processing"})


@router.post("/assess-portfolio", response_model=StandardResponse[dict])
async def post_assess_portfolio(
    body: AssessPortfolioBody,
    background_tasks: BackgroundTasks,
):
    """Trigger full portfolio assessment (all companies × L1–L4). Returns immediately."""
    async def run():
        try:
            await service.run_full_portfolio_assessment(body.company_ids)
        except Exception:
            logger.exception("Portfolio resilience assessment failed")

    background_tasks.add_task(run)
    return StandardResponse(data={"status": "processing"})


@router.get("/portfolio/matrix", response_model=StandardResponse[list])
async def get_portfolio_matrix():
    """Portfolio resilience matrix: company name, moat score, L1–L4 verdicts, L2 composite."""
    data = await service.get_portfolio_resilience_matrix()
    return StandardResponse(data=data)


@router.get("/flags", response_model=StandardResponse[list])
async def get_flags(reviewed: bool = False, limit: int = 50):
    """Unreviewed (or reviewed) resilience flags."""
    flags = await service.get_resilience_flags(reviewed=reviewed, limit=limit)
    return StandardResponse(data=[_flag_to_data(f) for f in flags])


@router.patch("/flags/{flag_id}/reviewed", response_model=StandardResponse[dict])
async def patch_flag_reviewed(flag_id: int):
    """Mark a flag as reviewed."""
    flag = await service.mark_flag_reviewed(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return StandardResponse(data=_flag_to_data(flag))

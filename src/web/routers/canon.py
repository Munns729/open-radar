"""Canon router — canonical company context, thesis summary, moat history, audit log."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from src.core.schemas import StandardResponse
from src.canon.service import (
    get_canon,
    get_canon_history,
    get_recent_changes,
    get_current_moat_scores,
    get_moat_score_history,
    update_canon,
    get_coverage_manifest,
    get_pending_proposals,
    approve_proposal,
    reject_proposal,
)


router = APIRouter(
    prefix="/api/canon",
    tags=["Canon"],
)


def _canon_to_dict(canon) -> dict:
    """Serialize CompanyCanon to JSON-safe dict."""
    d = canon.to_dict()
    return d


def _entry_to_dict(entry) -> dict:
    """Serialize CanonEntry to JSON-safe dict."""
    return entry.to_dict()


def _moat_row_to_dict(row) -> dict:
    """Serialize MoatScoreHistory row to JSON-safe dict."""
    return row.to_dict()


def _proposal_to_dict(p) -> dict:
    """Serialize CanonProposal to JSON-safe dict."""
    return p.to_dict()


# --- Endpoints (literal paths before path params) ---

@router.get("/coverage", response_model=StandardResponse[list])
async def get_coverage():
    """Coverage manifest by sector: company counts, active/stale, tier breakdown, last activity, recent signals."""
    data = await get_coverage_manifest()
    return StandardResponse(data=data)


@router.get("/recent-changes", response_model=StandardResponse[list])
async def recent_changes(limit: int = 20):
    """Recent canon changes across all companies."""
    entries = await get_recent_changes(limit=limit)
    return StandardResponse(data=[_entry_to_dict(e) for e in entries])


@router.get("/proposals", response_model=StandardResponse[list])
async def list_proposals():
    """All pending (non-expired) canon proposals."""
    proposals = await get_pending_proposals()
    return StandardResponse(data=[_proposal_to_dict(p) for p in proposals])


@router.get("/{company_id}/proposals", response_model=StandardResponse[list])
async def list_company_proposals(company_id: int):
    """Pending proposals for a single company."""
    proposals = await get_pending_proposals(company_id=company_id)
    return StandardResponse(data=[_proposal_to_dict(p) for p in proposals])


@router.post("/proposals/{proposal_id}/approve", response_model=StandardResponse[dict])
async def approve_proposal_endpoint(proposal_id: int, body: dict | None = None):
    """Approve a proposal: apply the change to canon and create CanonEntry."""
    body = body or {}
    try:
        proposal = await approve_proposal(proposal_id, reviewer_note=body.get("reviewer_note"))
        return StandardResponse(data=_proposal_to_dict(proposal))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/proposals/{proposal_id}/reject", response_model=StandardResponse[dict])
async def reject_proposal_endpoint(proposal_id: int, body: dict | None = None):
    """Reject a proposal."""
    body = body or {}
    try:
        proposal = await reject_proposal(proposal_id, reviewer_note=body.get("reviewer_note"))
        return StandardResponse(data=_proposal_to_dict(proposal))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{company_id}", response_model=StandardResponse[dict])
async def get_company_canon(company_id: int):
    """Get canon state for a company merged with current moat scores. 404 if no canon exists."""
    canon = await get_canon(company_id)
    if canon is None:
        raise HTTPException(status_code=404, detail="Canon not found for this company")
    scores = await get_current_moat_scores(company_id)
    data = _canon_to_dict(canon)
    data["current_moat_scores"] = scores
    return StandardResponse(data=data)


@router.get("/{company_id}/history", response_model=StandardResponse[list])
async def get_company_canon_history(company_id: int, limit: int = 50):
    """Canon audit log for the company."""
    entries = await get_canon_history(company_id, limit=limit)
    return StandardResponse(data=[_entry_to_dict(e) for e in entries])


@router.get("/{company_id}/moat-history", response_model=StandardResponse[list])
async def get_company_moat_history(
    company_id: int,
    pillar: Optional[str] = None,
    limit: int = 50,
):
    """Moat score history for the company, optionally filtered by pillar."""
    rows = await get_moat_score_history(company_id, pillar=pillar, limit=limit)
    return StandardResponse(data=[_moat_row_to_dict(r) for r in rows])


@router.patch("/{company_id}", response_model=StandardResponse[dict])
async def patch_company_canon(company_id: int, body: dict[str, Any]):
    """Update canon fields. Creates canon if missing. Records audit entries for changes."""
    canon = await update_canon(
        company_id,
        body,
        source_module="manual",
        triggered_by="user",
    )
    return StandardResponse(data=_canon_to_dict(canon))

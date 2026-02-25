"""Capability Tracker API — L1–L4 levels, signal definitions, and observations."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import StandardResponse
from src.capability import service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capability", tags=["Capability Tracker"])


class ObservationCreate(BaseModel):
    signal_key: str
    headline: str
    source_url: Optional[str] = None
    source_type: Optional[str] = "manual"
    confidence: float = 1.0


@router.get("/levels", response_model=StandardResponse[list])
async def get_levels(session: AsyncSession = Depends(get_db)):
    """All four levels with status, weighted score, and signal coverage summary per level."""
    levels = await service.get_all_levels()
    data = []
    for lev in levels:
        coverage = await service.get_signal_coverage(lev.level)
        data.append({
            "id": lev.id,
            "level": lev.level,
            "label": lev.label,
            "description": lev.description,
            "estimated_timeline": lev.estimated_timeline,
            "investment_implication": lev.investment_implication,
            "status": lev.status,
            "current_weighted_score": lev.current_weighted_score,
            "approach_threshold": lev.approach_threshold,
            "reached_threshold": lev.reached_threshold,
            "updated_at": lev.updated_at.isoformat() if lev.updated_at else None,
            "signal_coverage": coverage,
        })
    return StandardResponse(data=data)


@router.get("/levels/{level:int}/observations", response_model=StandardResponse[list])
async def get_level_observations(
    level: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """Recent observations for the given level; limit via query param."""
    if level < 1 or level > 4:
        raise HTTPException(status_code=404, detail="Level must be 1–4")
    observations = await service.get_level_observations(level=level, limit=limit)
    data = [
        {
            "id": o.id,
            "signal_key": o.signal_key,
            "headline": o.headline,
            "source_url": o.source_url,
            "source_type": o.source_type,
            "observed_at": o.observed_at.isoformat() if o.observed_at else None,
            "confidence": o.confidence,
            "logged_by": o.logged_by,
        }
        for o in observations
    ]
    return StandardResponse(data=data)


@router.get("/signals", response_model=StandardResponse[list])
async def get_signals(session: AsyncSession = Depends(get_db)):
    """All signal definitions with observation counts."""
    from sqlalchemy import select
    from src.capability.database import CapabilitySignalDefinition

    result = await session.execute(
        select(CapabilitySignalDefinition).order_by(
            CapabilitySignalDefinition.level.asc(),
            CapabilitySignalDefinition.signal_key.asc(),
        )
    )
    definitions = result.scalars().all()
    data = [
        {
            "id": d.id,
            "level": d.level,
            "signal_key": d.signal_key,
            "label": d.label,
            "description": d.description,
            "weight": d.weight,
            "observation_count": d.observation_count,
            "first_observed_at": d.first_observed_at.isoformat() if d.first_observed_at else None,
            "last_observed_at": d.last_observed_at.isoformat() if d.last_observed_at else None,
        }
        for d in definitions
    ]
    return StandardResponse(data=data)


@router.post("/observations", response_model=StandardResponse[dict])
async def create_observation(
    body: ObservationCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Record a signal observation. Updates observation_count and recalculates level status.
    Returns the new observation and the updated level.
    """
    try:
        observation, updated_level = await service.record_signal_observation(
            signal_key=body.signal_key,
            headline=body.headline,
            source_url=body.source_url,
            source_type=body.source_type or "manual",
            confidence=body.confidence,
            logged_by="manual",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    level_data: Optional[dict[str, Any]] = None
    if updated_level is not None:
        level_data = {
            "level": updated_level.level,
            "label": updated_level.label,
            "status": updated_level.status,
            "current_weighted_score": updated_level.current_weighted_score,
        }

    return StandardResponse(
        data={
            "observation": {
                "id": observation.id,
                "signal_key": observation.signal_key,
                "headline": observation.headline,
                "source_url": observation.source_url,
                "source_type": observation.source_type,
                "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                "confidence": observation.confidence,
                "logged_by": observation.logged_by,
            },
            "updated_level": level_data,
        }
    )

"""
Capability level service: record observations, recompute level status, and query levels/signals.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.capability.database import (
    CapabilityLevel,
    CapabilitySignalDefinition,
    CapabilitySignalObservation,
)


async def record_signal_observation(
    signal_key: str,
    headline: str,
    source_url: str | None = None,
    source_type: str = "manual",
    confidence: float = 1.0,
    logged_by: str = "manual",
) -> tuple[CapabilitySignalObservation, CapabilityLevel | None]:
    """
    Insert an observation, update the signal definition counts/dates,
    recompute level status, commit, and return the observation and updated level.
    """
    updated_level: CapabilityLevel | None = None
    async with get_async_db() as session:
        observation = CapabilitySignalObservation(
            signal_key=signal_key,
            headline=headline,
            source_url=source_url,
            source_type=source_type,
            confidence=confidence,
            logged_by=logged_by,
        )
        session.add(observation)
        await session.flush()

        result = await session.execute(
            select(CapabilitySignalDefinition).where(
                CapabilitySignalDefinition.signal_key == signal_key
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            await session.rollback()
            raise ValueError(f"Unknown signal_key: {signal_key}")

        now = datetime.utcnow()
        definition.observation_count += 1
        definition.last_observed_at = now
        if definition.first_observed_at is None:
            definition.first_observed_at = now

        await _recompute_level_status(definition.level, session)
        level_result = await session.execute(
            select(CapabilityLevel).where(CapabilityLevel.level == definition.level)
        )
        updated_level = level_result.scalar_one()
        await session.commit()
        await session.refresh(observation)
    return observation, updated_level


async def _recompute_level_status(level: int, session: AsyncSession) -> None:
    """
    Load all signal definitions for the level, compute weighted score
    (weight * 1 if observation_count >= 1 else 0), update CapabilityLevel
    score and status. Caller is responsible for commit.
    """
    result = await session.execute(
        select(CapabilitySignalDefinition).where(
            CapabilitySignalDefinition.level == level
        )
    )
    definitions = result.scalars().all()
    weighted_score = sum(
        d.weight if d.observation_count >= 1 else 0.0 for d in definitions
    )

    level_result = await session.execute(
        select(CapabilityLevel).where(CapabilityLevel.level == level)
    )
    level_row = level_result.scalar_one_or_none()
    if not level_row:
        return
    level_row.current_weighted_score = weighted_score
    if weighted_score >= level_row.reached_threshold:
        level_row.status = "reached"
    elif weighted_score >= level_row.approach_threshold:
        level_row.status = "approaching"
    else:
        level_row.status = "active"


async def get_signal_coverage(level: int) -> dict[str, Any]:
    """Return {signal_key: {label, weight, observation_count, last_observed_at}} for all signals at level."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CapabilitySignalDefinition).where(
                CapabilitySignalDefinition.level == level
            )
        )
        definitions = result.scalars().all()
    return {
        d.signal_key: {
            "label": d.label,
            "weight": d.weight,
            "observation_count": d.observation_count,
            "last_observed_at": d.last_observed_at.isoformat() if d.last_observed_at else None,
        }
        for d in definitions
    }


async def get_all_levels() -> list[CapabilityLevel]:
    """All four levels ordered by level asc."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CapabilityLevel).order_by(CapabilityLevel.level.asc())
        )
        return list(result.scalars().all())


async def get_level_observations(
    level: int, limit: int = 20
) -> list[CapabilitySignalObservation]:
    """Observations for signals at this level, join with definitions, order by observed_at desc."""
    async with get_async_db() as session:
        subq = (
            select(CapabilitySignalDefinition.signal_key).where(
                CapabilitySignalDefinition.level == level
            )
        )
        result = await session.execute(
            select(CapabilitySignalObservation)
            .where(CapabilitySignalObservation.signal_key.in_(subq))
            .order_by(CapabilitySignalObservation.observed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

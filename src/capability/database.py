"""
Database models for the Capability Level Tracker.

Tracks L1–L4 AI capability thresholds and observable signals for
frontier crossing detection and company resilience reassessment.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Float, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


class CapabilityLevel(Base):
    """
    One row per capability level (1–4). Tracks weighted score and status
    (active / approaching / reached) derived from signal observations.
    """
    __tablename__ = "capability_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_timeline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    investment_implication: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_weighted_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    approach_threshold: Mapped[float] = mapped_column(Float, default=0.4, nullable=False)
    reached_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CapabilitySignalDefinition(Base):
    """
    Signal definitions per level. Weights per level must sum to 1.0.
    observation_count and last_observed_at are updated when observations are recorded.
    """
    __tablename__ = "capability_signal_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    signal_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# APPEND-ONLY. Never UPDATE or DELETE rows from this table.
class CapabilitySignalObservation(Base):
    """
    Append-only log of observed signals. Each row is one observation event.
    """
    __tablename__ = "capability_signal_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    logged_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_capability_signal_observations_signal_observed", "signal_key", "observed_at"),
    )

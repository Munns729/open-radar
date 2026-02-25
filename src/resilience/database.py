"""
Database models for AI Resilience Scoring.
Companies are scored across four dimensions at each of four AI capability levels.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


# APPEND-ONLY. Current assessment per company+level = most recent row. Never UPDATE or DELETE.
class AIResilienceAssessment(Base):
    """
    One row per assessment event. Latest row per (company_id, capability_level) is current.
    """
    __tablename__ = "ai_resilience_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    capability_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, or 4
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    substitution_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    disintermediation_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    amplification_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    cost_disruption_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5

    composite_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    scarcity_classification: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scarcity_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessed_by: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    llm_prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessment_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_ai_resilience_company_level_assessed",
            "company_id",
            "capability_level",
            "assessed_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIResilienceAssessment(id={self.id}, company_id={self.company_id}, "
            f"level={self.capability_level}, verdict={self.overall_verdict})>"
        )


class AIResilienceFlag(Base):
    """
    Flag created when composite score moves >= 10 or verdict changes.
    """
    __tablename__ = "ai_resilience_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    capability_level: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    composite_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AIResilienceFlag(id={self.id}, company_id={self.company_id}, "
            f"level={self.capability_level}, {self.previous_verdict} -> {self.new_verdict})>"
        )

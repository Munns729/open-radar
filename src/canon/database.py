"""
Canonical context layer for RADAR.
Persistent, append-only record of thesis evolution and moat history per company.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CompanyCanon(Base):
    """
    One canonical record per company: current tier, thesis summary, moat snapshot, open questions.
    """
    __tablename__ = "company_canons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)  # references companies.id

    current_tier: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # CompanyTier.value as plain string
    thesis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moat_assessment: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {pillar_name: score} snapshot
    open_questions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of strings

    coverage_status: Mapped[str] = mapped_column(String(20), default="active")  # active | stale | archived

    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CompanyCanon(id={self.id}, company_id={self.company_id}, tier={self.current_tier})>"


# APPEND-ONLY. Never UPDATE or DELETE rows from this table.
class CanonEntry(Base):
    """
    Append-only audit log of changes to company canon fields.
    """
    __tablename__ = "canon_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # references companies.id

    field_changed: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "thesis_summary", "current_tier"
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)

    source_module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. "competitive", "manual"
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<CanonEntry(id={self.id}, company_id={self.company_id}, field={self.field_changed})>"


# APPEND-ONLY. Current score per company+pillar = most recent row. Never UPDATE or DELETE.
class MoatScoreHistory(Base):
    """
    Append-only per-pillar moat score history. Latest row per (company_id, pillar) is current score.
    """
    __tablename__ = "moat_score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # references companies.id

    pillar: Mapped[str] = mapped_column(String(100), nullable=False)  # free-form pillar name from thesis config
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–100
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "llm_scoring", "manual", "document_extract"
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_moat_score_history_company_pillar_created", "company_id", "pillar", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<MoatScoreHistory(id={self.id}, company_id={self.company_id}, pillar={self.pillar}, score={self.score})>"


class CanonProposal(Base):
    """
    Human-approval queue for proposed canon field changes (e.g. tier).
    Pending proposals expire after 14 days; approve applies the change and creates a CanonEntry.
    """
    __tablename__ = "canon_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # references companies.id

    proposed_field: Mapped[str] = mapped_column(String(100), nullable=False)
    current_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)

    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signals: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of signal strings

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending | approved | rejected | auto-expired
    source_module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # created_at + 14 days

    def __repr__(self) -> str:
        return f"<CanonProposal(id={self.id}, company_id={self.company_id}, field={self.proposed_field}, status={self.status})>"

"""
Document ingestion and extraction models.
DocumentIngestion links to companies.id (not tracked_companies.id).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, JSON, Index, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentIngestion(Base):
    """
    One row per uploaded document per company.
    Links to companies.id via company_id.
    """
    __tablename__ = "document_ingestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # FK to companies.id
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # cim | mgmt_call | expert_call | customer_ref | financial_model | news | other
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 hex digest
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending | processing | complete | failed
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "file_hash", name="uq_company_document_hash"),
    )

    def __repr__(self) -> str:
        return f"<DocumentIngestion(id={self.id}, company_id={self.company_id}, status={self.processing_status})>"


# APPEND-ONLY. One extract per document. Never UPDATE or DELETE.
class DocumentExtract(Base):
    """
    One row per document: structured intelligence extracted by LLM.
    """
    __tablename__ = "document_extracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)  # FK to document_ingestions.id
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    moat_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # {pillar: {direction, evidence, confidence, key_quote}}
    resilience_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # {level_str: {dimension: {direction, confidence}}}
    thesis_elements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    tier_signal: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # {direction, rationale, confidence}
    scarcity_signals: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    open_questions_raised: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    red_flags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    proposals_generated: Mapped[int] = mapped_column(Integer, default=0)
    llm_prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<DocumentExtract(id={self.id}, document_id={self.document_id})>"

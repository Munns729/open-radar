"""
VC Portfolio Intelligence models.

Single company entity (companies table) + minimal junction for fund holdings.
  company_vc_holdings — (company_id, vc_firm_id) + source_url, last_scraped_at
  vc_exit_signals     — one per holding (exit-readiness + deal quality)
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date,
    ForeignKey, Float, Boolean, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class CompanyVCHoldingModel(Base):
    """
    Junction: a company (universe) is in a VC fund's portfolio.
    One row per (company_id, vc_firm_id). Company attributes live on companies table.
    """
    __tablename__ = "company_vc_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    vc_firm_id = Column(Integer, ForeignKey("vc_firms.id", ondelete="CASCADE"), nullable=False, index=True)

    source_url = Column(String(500))
    source = Column(String(100), default="website")
    first_seen_at = Column(DateTime, nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)

    company = relationship("CompanyModel", foreign_keys=[company_id])
    vc_firm = relationship("VCFirmModel", foreign_keys=[vc_firm_id])
    exit_signals = relationship("VCExitSignalModel", back_populates="holding", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "vc_firm_id", name="uq_company_vc_holding"),
        Index("idx_company_vc_holdings_company", "company_id"),
        Index("idx_company_vc_holdings_firm", "vc_firm_id"),
    )

    def __repr__(self):
        return f"<CompanyVCHolding(company_id={self.company_id}, vc_firm_id={self.vc_firm_id})>"


class VCExitSignalModel(Base):
    """
    Computed exit-readiness and quality signals for a VC holding (company + fund).
    One record per holding (upserted by vc_signal_scorer.py).
    """
    __tablename__ = "vc_exit_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    holding_id = Column(
        Integer, ForeignKey("company_vc_holdings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    exit_readiness_score = Column(Float, default=0.0)
    years_held = Column(Float, nullable=True)
    fund_vintage_year = Column(Integer, nullable=True)
    fund_exit_pressure = Column(Boolean, default=False)

    vc_quality_tier = Column(Integer, default=3)
    nato_lp_backed = Column(Boolean, default=False)
    eif_lp_backed = Column(Boolean, default=False)
    co_investor_count = Column(Integer, default=0)
    top_co_investors = Column(JSON)

    regulatory_moat_confirmed = Column(Boolean, default=False)
    diana_cohort = Column(Boolean, default=False)
    edf_grantee = Column(Boolean, default=False)
    gov_contract_value_est_eur = Column(Float, nullable=True)

    deal_quality_score = Column(Float, default=0.0)
    priority_tier = Column(String(10), default="C")

    notes = Column(Text)
    scored_at = Column(DateTime, default=datetime.utcnow)

    holding = relationship("CompanyVCHoldingModel", back_populates="exit_signals")

    __table_args__ = (
        Index("idx_vc_exit_priority", "priority_tier"),
        Index("idx_vc_exit_quality", "deal_quality_score"),
    )

    def __repr__(self):
        return (
            f"<VCExitSignal(holding_id={self.holding_id}, "
            f"quality={self.deal_quality_score:.1f}, tier={self.priority_tier})>"
        )

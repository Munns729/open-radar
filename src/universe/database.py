"""
Database models for Module 1 - Universe Scanner.
"""
import sys

# Standardize module naming to prevent dual-import split of SQLAlchemy Base registry
if 'universe.database' in sys.modules and 'src.universe.database' not in sys.modules:
    sys.modules['src.universe.database'] = sys.modules['universe.database']
elif 'src.universe.database' in sys.modules and 'universe.database' not in sys.modules:
    sys.modules['universe.database'] = sys.modules['src.universe.database']

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, BigInteger, DECIMAL, Float, Enum as SQLEnum, Index, JSON
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.core.models import CompanyTier

class CompanyModel(Base):
    """
    SQLAlchemy model for companies.
    Maps to the 'companies' table.
    """
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    registration_number = Column(String(100), index=True) # For non-UK companies (SIREN, HRB, etc)
    companies_house_number = Column(String(50), unique=True, index=True) # UK Only
    website = Column(String(500), index=True)
    hq_country = Column(String(2))  # ISO 3166-1 alpha-2
    hq_city = Column(String(100), index=True) # NEW: City of HQ
    hq_address = Column(Text)
    description = Column(Text) # Short business description
    sub_sector = Column(String(100), index=True) # NEW: More granular sector
    raw_website_text = Column(Text, nullable=True)  # Full website content for LLM analysis
    semantic_enriched_at = Column(DateTime, nullable=True)
    extraction_complete_at = Column(DateTime, nullable=True)  # Set when Extraction & Enrichment has run
    
    # Financials
    revenue_gbp = Column(BigInteger)
    revenue_source = Column(String(50), nullable=True)  # ch_filing, ch_band_midpoint, llm_website, eu_band_midpoint, other_registry
    ebitda_gbp = Column(BigInteger)
    ebitda_margin = Column(DECIMAL(5, 2))
    gross_margin = Column(DECIMAL(5, 2))
    revenue_growth = Column(DECIMAL(5, 2)) # YoY Growth %
    employees = Column(Integer)
    financial_year = Column(Integer)
    
    # Competitive Position (NEW)
    market_share = Column(DECIMAL(5, 2)) # Percentage
    competitor_count = Column(Integer)
    market_growth_rate = Column(DECIMAL(5, 2)) # Percentage
    
    # Classification
    sector = Column(String(100), index=True)
    sic_codes = Column(JSON)  # JSON is usually better for portability (SQLite/Postgres) than PG-specific ARRAY
    
    # Moat & Analysis
    moat_type = Column(String(100), default="none")  # Thesis-driven, not enum-constrained
    moat_score = Column(Integer, default=0, index=True) # 0-100
    moat_attributes = Column(JSON, nullable=True) # Regulatory, Network, etc. status + justification
    moat_analysis = Column(JSON, nullable=True) # 5-pillar breakdown with justifications
    tier = Column(SQLEnum(CompanyTier), default=CompanyTier.TIER_2, index=True)
    discovered_via = Column(String(100))
    exclusion_reason = Column(Text, nullable=True) # Reason why company was excluded from enrichment

    # VC/portfolio-sourced company-level facts (optional; also used by universe pipeline)
    first_funding_date = Column(Date, nullable=True)
    is_dual_use = Column(Boolean, default=False)
    dual_use_confidence = Column(Float, nullable=True)  # 0-1
    has_gov_contract = Column(Boolean, default=False)
    gov_contract_notes = Column(Text, nullable=True)
    has_export_cert = Column(Boolean, default=False)
    regulatory_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    certifications = relationship("CertificationModel", back_populates="company", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_moat_score_desc', moat_score.desc()),
    )

    def __repr__(self):
        return f"<Company(name='{self.name}', tier='{self.tier}', moat='{self.moat_score}')>"


class CertificationModel(Base):
    """
    SQLAlchemy model for company certifications.
    Maps to the 'certifications' table.
    """
    __tablename__ = 'certifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    
    certification_type = Column(String(100)) # 'AS9100', 'ISO9001', etc.
    certification_number = Column(String(255))
    issuing_body = Column(String(255))
    issue_date = Column(Date)
    expiry_date = Column(Date)
    scope = Column(Text)
    source_url = Column(String(500))

    company = relationship("CompanyModel", back_populates="certifications")

    def __repr__(self):
        return f"<Certification(type='{self.certification_type}', company_id={self.company_id})>"


class CompanyRelationshipModel(Base):
    """
    SQLAlchemy model for relationships between companies.
    Maps to the 'company_relationships' table.
    """
    __tablename__ = 'company_relationships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_a_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    company_b_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    
    relationship_type = Column(String(50)) # 'supplier', 'customer', 'partner', 'competitor'
    confidence = Column(DECIMAL(3, 2)) # 0.00 to 1.00
    discovered_via = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Relationship(a={self.company_a_id}, b={self.company_b_id}, type='{self.relationship_type}')>"


class ScoringEvent(Base):
    """
    Records each time a company is scored/rescored, enabling audit trail.
    Stores a full snapshot of the scoring result plus a per-pillar diff
    against the previous scoring, so humans can challenge any score.
    """
    __tablename__ = 'scoring_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    
    # Snapshot of the scoring result
    moat_score = Column(Integer, nullable=False)
    tier = Column(String(10), nullable=False)
    moat_attributes = Column(JSON, nullable=False)
    weights_used = Column(JSON, nullable=False)
    
    # What changed vs. previous scoring
    previous_score = Column(Integer, nullable=True)       # null on first scoring
    score_delta = Column(Integer, nullable=True)           # +/- change
    changes = Column(JSON, nullable=True)                  # Per-pillar diff
    
    # Context
    trigger = Column(String(50), nullable=False, default="rescan")
    scored_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    company = relationship("CompanyModel", backref="scoring_events")

    def __repr__(self):
        return f"<ScoringEvent(company_id={self.company_id}, score={self.moat_score}, delta={self.score_delta})>"

# Late-binding relationships: CompanyRelationshipModel must be fully defined before
# these can be declared, so they cannot live inside the CompanyModel class body.
CompanyModel.relationships_as_a = relationship(
    "CompanyRelationshipModel",
    primaryjoin=CompanyModel.id == CompanyRelationshipModel.company_a_id,
    foreign_keys=[CompanyRelationshipModel.company_a_id],
    back_populates="company_a",
    viewonly=True,
    overlaps="company_a"
)
CompanyModel.relationships_as_b = relationship(
    "CompanyRelationshipModel",
    primaryjoin=CompanyModel.id == CompanyRelationshipModel.company_b_id,
    foreign_keys=[CompanyRelationshipModel.company_b_id],
    back_populates="company_b",
    viewonly=True,
    overlaps="company_b"
)
CompanyRelationshipModel.company_a = relationship(
    "CompanyModel",
    foreign_keys=[CompanyRelationshipModel.company_a_id],
    back_populates="relationships_as_a",
    overlaps="relationships_as_a"
)
CompanyRelationshipModel.company_b = relationship(
    "CompanyModel",
    foreign_keys=[CompanyRelationshipModel.company_b_id],
    back_populates="relationships_as_b",
    overlaps="relationships_as_b"
)

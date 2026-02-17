"""
Database models for Module 10 - Capital Flows Scanner.
"""
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, BigInteger, DECIMAL, Enum as SQLEnum, Index, JSON, Float
from sqlalchemy.orm import relationship
from src.core.database import Base
# MoatType removed — moat types are now thesis-driven strings

class PEFirmModel(Base):
    """
    Private Equity Firm.
    """
    __tablename__ = 'pe_firms'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    hq_country = Column(String(255))
    aum_usd = Column(BigInteger)
    fund_count = Column(Integer)
    founding_year = Column(Integer)
    typical_check_size_usd = Column(BigInteger)
    investment_strategy = Column(String(100)) # 'buyout', 'growth', 'venture'
    sector_focus = Column(JSON) # Array of strings
    geography_focus = Column(JSON) # Array of strings
    website = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    investments = relationship("PEInvestmentModel", back_populates="pe_firm")
    sponsored_consolidators = relationship("ConsolidatorModel", back_populates="pe_sponsor")

    def __repr__(self):
        return f"<PEFirm(name='{self.name}', aum={self.aum_usd})>"


class PEInvestmentModel(Base):
    """
    Portfolio company investment by a PE firm.
    """
    __tablename__ = 'pe_investments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pe_firm_id = Column(Integer, ForeignKey('pe_firms.id'), nullable=False)
    
    # Link to global universe company if matched
    company_id = Column(Integer, index=True, nullable=True) 
    company_name = Column(String(255), nullable=False)
    
    entry_date = Column(Date)
    exit_date = Column(Date, nullable=True)
    is_exited = Column(Boolean, default=False)
    
    # Enrichment Fields
    description = Column(Text) # Business description
    investment_year = Column(Integer)
    exit_year = Column(Integer)

    entry_valuation_usd = Column(BigInteger)
    entry_multiple = Column(DECIMAL(5, 2)) # EBITDA multiple
    
    exit_valuation_usd = Column(BigInteger)
    exit_multiple = Column(DECIMAL(5, 2))
    
    moic = Column(DECIMAL(5, 2))
    irr = Column(DECIMAL(5, 2))
    
    sector = Column(String(100))
    moat_type = Column(String(50)) # Stored as string to allow flexible scraping, or map to enum
    
    # Investment Context & Thesis (from PE firm website)
    investment_thesis = Column(Text)  # PE firm's stated reason for investment
    deal_announcement_url = Column(String(500))  # Link to press release
    exit_thesis = Column(Text)  # Why they exited / value created
    strategic_rationale = Column(Text)  # How it fits their strategy
    
    # Moat Analysis from PE perspective
    pe_identified_moats = Column(JSON)  # What moats PE firm highlighted
    thesis_keywords = Column(JSON)  # Keywords extracted from thesis
    
    # Enrichment metadata
    is_enriched = Column(Boolean, default=False)  # Has detail page been scraped
    enriched_at = Column(DateTime, nullable=True)  # When enrichment occurred
    
    source = Column(String(100)) # 'website', 'pitchbook', 'news'
    source_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    pe_firm = relationship("PEFirmModel", back_populates="investments")

    __table_args__ = (
        Index('idx_pe_inv_moat', 'moat_type'),
        Index('idx_pe_inv_entry_date', 'entry_date'),
    )


class ConsolidatorModel(Base):
    """
    Consolidator / Platform Company / Serial Acquirer.
    """
    __tablename__ = 'consolidators'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50)) # 'pe_backed_platform', 'independent_serial', 'public_rollup'
    
    pe_sponsor_id = Column(Integer, ForeignKey('pe_firms.id'), nullable=True)
    
    is_public = Column(Boolean, default=False)
    ticker = Column(String(10))
    
    sector_focus = Column(String(100))
    typical_target_size_min_usd = Column(BigInteger)
    typical_target_size_max_usd = Column(BigInteger)
    acquisition_budget_usd = Column(BigInteger)
    
    acquisitions_last_12mo = Column(Integer, default=0)
    
    website = Column(String(500))
    acquisition_page_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    pe_sponsor = relationship("PEFirmModel", back_populates="sponsored_consolidators")
    acquisitions = relationship("ConsolidatorAcquisitionModel", back_populates="consolidator")


class ConsolidatorAcquisitionModel(Base):
    """
    Acquisition made by a consolidator.
    """
    __tablename__ = 'consolidator_acquisitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    consolidator_id = Column(Integer, ForeignKey('consolidators.id'), nullable=False)
    
    target_company_id = Column(Integer, nullable=True)
    target_name = Column(String(255), nullable=False)
    
    announcement_date = Column(Date)
    close_date = Column(Date)
    
    purchase_price_usd = Column(BigInteger)
    target_revenue_usd = Column(BigInteger)
    target_ebitda_usd = Column(BigInteger)
    ebitda_multiple = Column(DECIMAL(5, 2))
    
    is_platform = Column(Boolean, default=False)
    platform_number = Column(Integer)
    
    source = Column(String(100))
    source_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    consolidator = relationship("ConsolidatorModel", back_populates="acquisitions")


class StrategicAcquirerModel(Base):
    """
    Strategic Acquirer (Corporate).
    """
    __tablename__ = 'strategic_acquirers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    ticker = Column(String(10))
    
    category = Column(String(50)) # 'defense_prime', 'healthcare_system', etc.
    revenue_usd = Column(BigInteger)
    market_cap_usd = Column(BigInteger)
    
    acquisition_budget_annual_usd = Column(BigInteger)
    typical_multiple_paid = Column(DECIMAL(5, 2))
    
    values_regulatory_moats = Column(Boolean, default=False)
    values_network_effects = Column(Boolean, default=False)
    
    acquisitions_last_24mo = Column(Integer, default=0)
    
    website = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    acquisitions = relationship("StrategicAcquisitionModel", back_populates="acquirer")


class StrategicAcquisitionModel(Base):
    """
    Acquisition made by a strategic acquirer.
    """
    __tablename__ = 'strategic_acquisitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    acquirer_id = Column(Integer, ForeignKey('strategic_acquirers.id'), nullable=False)
    
    target_company_id = Column(Integer, nullable=True)
    target_name = Column(String(255))
    
    announcement_date = Column(Date)
    close_date = Column(Date)
    
    purchase_price_usd = Column(BigInteger)
    target_revenue_usd = Column(BigInteger)
    target_ebitda_usd = Column(BigInteger)
    ebitda_multiple = Column(DECIMAL(5, 2))
    
    strategic_rationale = Column(Text)
    target_moat_type = Column(String(50))
    
    source = Column(String(100))
    source_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    acquirer = relationship("StrategicAcquirerModel", back_populates="acquisitions")

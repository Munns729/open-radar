"""
Database models for Module 11: Carveout Scanner.
Focus: European corporate parents and their divisions.
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, BigInteger, DECIMAL, Text, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from src.core.database import Base

class CorporateParent(Base):
    """Parent company for potential carveouts."""
    __tablename__ = "corporate_parents"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    is_public = Column(Boolean, default=True)
    ticker = Column(String(10))
    exchange = Column(String(50))  # e.g., 'LSE', 'Euronext', 'Xetra'
    hq_country = Column(String(2))
    revenue_eur = Column(BigInteger)
    market_cap_eur = Column(BigInteger)
    ceo_name = Column(String(255))
    ceo_tenure_months = Column(Integer)
    has_divested_before = Column(Boolean)
    activist_pressure = Column(Boolean)
    activist_investor = Column(String(255))
    last_strategic_review_date = Column(Date)
    website = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    divisions = relationship("Division", back_populates="parent")

class Division(Base):
    """A division within a corporate parent."""
    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("corporate_parents.id"))
    division_name = Column(String(255), nullable=False)
    legal_entity = Column(String(255))
    companies_house_number = Column(String(50))
    
    revenue_eur = Column(BigInteger)
    revenue_gbp = Column(BigInteger) # Explicit GBP for scoring
    ebitda_eur = Column(BigInteger)
    ebitda_gbp = Column(BigInteger) # Explicit GBP for scoring
    ebitda_margin = Column(DECIMAL(5, 2))
    employees = Column(Integer)
    percent_of_parent_revenue = Column(DECIMAL(5, 2))
    
    hq_location = Column(String(255))
    business_description = Column(Text)
    
    # Structural traits
    autonomy_level = Column(String(20)) # 'standalone', 'semi_autonomous', 'integrated'
    strategic_autonomy = Column(String(20)) # 'non_core', 'peripheral', 'core'
    moat_type = Column(String(50))
    moat_strength = Column(Integer) # 0-100
    
    # Competitive Dynamics
    market_share = Column(DECIMAL(5, 2)) # Percentage
    competitor_count = Column(Integer)
    market_growth_rate = Column(DECIMAL(5, 2)) # Percentage
    
    # Scoring
    carveout_probability = Column(Integer) # 0-100
    carveout_timeline = Column(String(50)) # 'imminent', '6-12mo', '12-24mo', '24mo+'
    attractiveness_score = Column(Integer) # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)

    parent = relationship("CorporateParent", back_populates="divisions")
    signals = relationship("CarveoutSignal", back_populates="division")
    processes = relationship("CarveoutProcess", back_populates="division")

    __table_args__ = (
        Index("idx_carveout_probability", "carveout_probability", mysql_length=None),
        Index("idx_attractiveness_score", "attractiveness_score", mysql_length=None),
    )

class CarveoutSignal(Base):
    """Explicit or implicit signal of potential divestiture."""
    __tablename__ = "carveout_signals"

    id = Column(Integer, primary_key=True)
    division_id = Column(Integer, ForeignKey("divisions.id"))
    signal_type = Column(String(50)) # 'explicit', 'implicit', 'early'
    signal_category = Column(String(100)) # 'strategic_review', 'activist_pressure', etc.
    signal_date = Column(Date)
    confidence = Column(String(20)) # 'high', 'medium', 'low'
    evidence = Column(Text)
    source = Column(String(100))
    source_url = Column(String(500))
    increases_probability = Column(Integer) # Points added to probability
    created_at = Column(DateTime, default=datetime.utcnow)

    division = relationship("Division", back_populates="signals")

class CarveoutProcess(Base):
    """Tracking an active or past divestiture process."""
    __tablename__ = "carveout_processes"

    id = Column(Integer, primary_key=True)
    division_id = Column(Integer, ForeignKey("divisions.id"))
    announced_date = Column(Date)
    expected_close_date = Column(Date)
    actual_close_date = Column(Date)
    process_type = Column(String(50)) # 'bilateral', 'managed_auction', 'public_spin'
    banker = Column(String(255))
    estimated_valuation_eur = Column(BigInteger)
    estimated_multiple = Column(DECIMAL(5, 2))
    buyer = Column(String(255))
    final_price_eur = Column(BigInteger)
    final_multiple = Column(DECIMAL(5, 2))
    process_status = Column(String(50)) # 'announced', 'bidding', 'closed', 'failed'
    fund_participated = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)

    division = relationship("Division", back_populates="processes")

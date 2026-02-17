"""
Database models for Module 4 - Deal Intelligence.
PE transaction analysis, valuation comparables, and deal probability scoring.
"""
from typing import List, Optional
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, 
    ForeignKey, Text, BigInteger, Float, Index, JSON
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class DealType(str, PyEnum):
    """PE deal transaction type."""
    BUYOUT = "buyout"
    GROWTH = "growth"
    CARVEOUT = "carveout"
    SECONDARY = "secondary"
    RECAP = "recap"
    ADD_ON = "add_on"


class DealSource(str, PyEnum):
    """Source of deal information."""
    NEWS = "news"
    FILING = "filing"
    PROPRIETARY = "proprietary"
    DATABASE = "database"


class DealRecord(Base):
    """
    Enhanced PE deal record with valuation and transaction details.
    Primary data model for deal intelligence and comparable analysis.
    """
    __tablename__ = 'deal_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # PE Firm Link
    pe_firm_id = Column(Integer, ForeignKey('pe_firms.id'), nullable=True, index=True)
    
    # Target Company
    target_company_name = Column(String(255), nullable=False)
    target_company_id = Column(Integer, nullable=True, index=True)  # Link to CompanyModel if matched
    
    # Deal Details
    deal_date = Column(Date, nullable=True, index=True)
    deal_type = Column(String(50), default=DealType.BUYOUT.value)  # buyout/growth/carveout/secondary
    announced_date = Column(Date, nullable=True)
    closed_date = Column(Date, nullable=True)
    
    # Classification
    sector = Column(String(100), index=True)
    subsector = Column(String(100))
    geography = Column(String(100), index=True)  # e.g., "UK", "Germany", "France"
    region = Column(String(50))  # e.g., "Western Europe", "Nordics"
    
    # Financials (in GBP for consistency)
    revenue_gbp = Column(BigInteger, nullable=True)
    ebitda_gbp = Column(BigInteger, nullable=True)
    enterprise_value_gbp = Column(BigInteger, nullable=True)
    
    # Valuation Multiples
    ev_revenue_multiple = Column(Float, nullable=True)
    ev_ebitda_multiple = Column(Float, nullable=True)
    
    # Deal Structure
    equity_investment_gbp = Column(BigInteger, nullable=True)
    debt_gbp = Column(BigInteger, nullable=True)
    equity_percentage = Column(Float, nullable=True)  # % equity vs debt
    
    # Metadata
    source = Column(String(50), default=DealSource.NEWS.value)  # news/filing/proprietary
    source_url = Column(String(500), nullable=True)
    confidence_score = Column(Integer, default=50)  # 0-100 confidence in data accuracy
    
    # Processing Status
    is_enriched = Column(Boolean, default=False)
    enrichment_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    comparables_as_source = relationship(
        "DealComparable", 
        foreign_keys="DealComparable.deal_record_id",
        back_populates="source_deal",
        cascade="all, delete-orphan"
    )
    comparables_as_target = relationship(
        "DealComparable", 
        foreign_keys="DealComparable.comparable_deal_id",
        back_populates="comparable_deal"
    )

    __table_args__ = (
        Index('idx_deal_sector_date', 'sector', 'deal_date'),
        Index('idx_deal_ev_range', 'enterprise_value_gbp'),
    )

    def __repr__(self):
        return f"<DealRecord(target='{self.target_company_name}', date={self.deal_date}, ev={self.enterprise_value_gbp})>"


class DealComparable(Base):
    """
    Links two deals as comparable transactions for valuation analysis.
    """
    __tablename__ = 'deal_comparables'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Source deal being analyzed
    deal_record_id = Column(Integer, ForeignKey('deal_records.id'), nullable=False, index=True)
    
    # Comparable deal
    comparable_deal_id = Column(Integer, ForeignKey('deal_records.id'), nullable=False, index=True)
    
    # Similarity Analysis
    similarity_score = Column(Integer, default=0)  # 0-100
    similarity_reasons = Column(JSON, nullable=True)  # {sector_match: true, size_match: 0.85, geography_match: true}
    
    # Breakdown scores
    sector_similarity = Column(Float, default=0)  # 0-1
    size_similarity = Column(Float, default=0)  # 0-1
    geography_similarity = Column(Float, default=0)  # 0-1
    time_similarity = Column(Float, default=0)  # 0-1 (more recent = higher)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_deal = relationship("DealRecord", foreign_keys=[deal_record_id], back_populates="comparables_as_source")
    comparable_deal = relationship("DealRecord", foreign_keys=[comparable_deal_id], back_populates="comparables_as_target")

    __table_args__ = (
        Index('idx_comparable_pair', 'deal_record_id', 'comparable_deal_id', unique=True),
    )

    def __repr__(self):
        return f"<DealComparable(source={self.deal_record_id}, comparable={self.comparable_deal_id}, score={self.similarity_score})>"


class MarketMetrics(Base):
    """
    Aggregated market metrics by sector and time period.
    Used for trend analysis and market intelligence.
    """
    __tablename__ = 'market_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Segmentation
    sector = Column(String(100), nullable=False, index=True)
    geography = Column(String(100), default="Europe")  # "UK", "Germany", "Europe" (aggregate)
    time_period = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    
    # Volume Metrics
    deal_count = Column(Integer, default=0)
    total_value_gbp = Column(BigInteger, default=0)
    average_deal_size_gbp = Column(BigInteger, default=0)
    
    # Valuation Metrics
    median_ev_revenue = Column(Float, nullable=True)
    median_ev_ebitda = Column(Float, nullable=True)
    avg_ev_revenue = Column(Float, nullable=True)
    avg_ev_ebitda = Column(Float, nullable=True)
    min_ev_ebitda = Column(Float, nullable=True)
    max_ev_ebitda = Column(Float, nullable=True)
    
    # Performance Metrics (from targets)
    avg_growth_rate = Column(Float, nullable=True)  # Average revenue growth
    avg_ebitda_margin = Column(Float, nullable=True)
    
    # Trend Indicators
    deal_count_change_pct = Column(Float, nullable=True)  # vs previous period
    value_change_pct = Column(Float, nullable=True)
    multiple_change_pct = Column(Float, nullable=True)
    is_hot_sector = Column(Boolean, default=False)  # Flagged as trending
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_metrics_sector_period', 'sector', 'time_period'),
        Index('idx_metrics_hot', 'is_hot_sector'),
    )

    def __repr__(self):
        return f"<MarketMetrics(sector='{self.sector}', period={self.time_period}, deals={self.deal_count})>"


class DealProbability(Base):
    """
    Deal probability score for a company in the universe.
    Tracks likelihood of becoming a PE transaction target.
    """
    __tablename__ = 'deal_probabilities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Target Company (links to CompanyModel in Universe)
    target_company_id = Column(Integer, nullable=False, index=True)
    target_company_name = Column(String(255), nullable=False)
    
    # Probability Assessment
    probability_score = Column(Integer, default=0)  # 0-100
    probability_tier = Column(String(20))  # "high" (>70), "medium" (40-70), "low" (<40)
    
    # Reasoning
    reasoning = Column(Text, nullable=True)  # LLM-generated explanation
    
    # Signal Breakdown (JSON with boolean/score flags)
    signals = Column(JSON, nullable=True)
    # Expected structure:
    # {
    #   "seller_distress": {"active": true, "score": 30, "evidence": "..."},
    #   "advisor_engaged": {"active": false, "score": 0},
    #   "management_changes": {"active": true, "score": 20, "evidence": "..."},
    #   "declining_growth": {"active": true, "score": 15},
    #   "pe_sector_interest": {"active": true, "score": 25},
    #   "time_since_last_deal": {"years": 5, "score": 10}
    # }
    
    # Individual Signal Scores (for quick querying)
    signal_seller_distress = Column(Boolean, default=False)
    signal_advisor_engaged = Column(Boolean, default=False)
    signal_management_changes = Column(Boolean, default=False)
    signal_declining_growth = Column(Boolean, default=False)
    signal_pe_sector_interest = Column(Boolean, default=False)
    signal_carveout_potential = Column(Boolean, default=False)
    
    # Timeline Estimate
    expected_timeline = Column(String(50))  # "6-12 months", "12-24 months", "2+ years"
    
    # Status
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_stale = Column(Boolean, default=False)  # Needs refresh
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_probability_score', 'probability_score'),
        Index('idx_probability_company', 'target_company_id', unique=True),
    )

    def __repr__(self):
        return f"<DealProbability(company='{self.target_company_name}', score={self.probability_score})>"

    @property
    def tier(self) -> str:
        """Calculate probability tier from score."""
        if self.probability_score >= 70:
            return "high"
        elif self.probability_score >= 40:
            return "medium"
        return "low"

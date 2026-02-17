from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from src.core.database import Base

class NewsSource(Base):
    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))  # 'rss', 'newsletter', 'regulatory_site', 'news_site'
    category: Mapped[str] = mapped_column(String(100))  # 'aerospace', 'healthcare', 'fintech', 'regulatory', 'ma'
    check_frequency: Mapped[str] = mapped_column(String(20))  # 'hourly', 'daily', 'weekly'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[List["IntelligenceItem"]] = relationship("IntelligenceItem", back_populates="source")

class IntelligenceItem(Base):
    __tablename__ = "intelligence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("news_sources.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True)  # SHA256
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    relevance_score: Mapped[Optional[int]] = mapped_column(Integer, index=True) # 0-100
    summary: Mapped[Optional[str]] = mapped_column(Text)
    key_points: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    implications: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source: Mapped["NewsSource"] = relationship("NewsSource", back_populates="items")

class RegulatoryChange(Base):
    __tablename__ = "regulatory_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(50)) # 'UK', 'EU', 'US'
    regulatory_body: Mapped[str] = mapped_column(String(100)) # 'FCA', 'MHRA', 'FAA', etc.
    change_type: Mapped[str] = mapped_column(String(50)) # 'new_regulation', 'amendment', 'guidance', 'enforcement'
    title: Mapped[str] = mapped_column(String(500))
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text)
    affected_sectors: Mapped[Optional[List[str]]] = mapped_column(JSON)
    impact_assessment: Mapped[Optional[str]] = mapped_column(Text)
    creates_barriers_to_entry: Mapped[Optional[bool]] = mapped_column(Boolean)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class MarketTrend(Base):
    __tablename__ = "market_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trend_name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(100))
    trend_type: Mapped[str] = mapped_column(String(50)) # 'technology', 'regulatory', 'business_model', 'consolidation'
    strength: Mapped[str] = mapped_column(String(20)) # 'emerging', 'accelerating', 'mature', 'declining'
    first_detected: Mapped[Optional[date]] = mapped_column(Date)
    supporting_evidence: Mapped[Optional[List[str]]] = mapped_column(JSON)
    implications_for_thesis: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[str]] = mapped_column(String(20)) # 'high', 'medium', 'low'
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

class WeeklyBriefing(Base):
    __tablename__ = "weekly_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_starting: Mapped[date] = mapped_column(Date)
    executive_summary: Mapped[Optional[str]] = mapped_column(Text)
    top_regulatory_changes: Mapped[Optional[List[str]]] = mapped_column(JSON) # Storing IDs or summaries
    top_ma_activity: Mapped[Optional[List[str]]] = mapped_column(JSON)
    emerging_trends: Mapped[Optional[List[str]]] = mapped_column(JSON)
    thesis_implications: Mapped[Optional[str]] = mapped_column(Text)
    action_items: Mapped[Optional[List[str]]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScoringConfigRecommendation(Base):
    """
    A structured recommendation to update moat scoring configuration,
    generated by LLM analysis of regulatory changes. Requires human approval.
    
    Each recommendation targets a specific config constant and action:
    - CERT_SCORES: add/modify/remove a certification and its score
    - SOVEREIGNTY_KEYWORDS: add/remove a keyword
    - SOVEREIGNTY_CERTS: add/remove a cert from the sovereignty set
    - MOAT_WEIGHTS: suggest a weight adjustment (rare, requires strong evidence)
    """
    __tablename__ = 'scoring_config_recommendations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Link to the regulatory change that triggered this
    regulatory_change_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('regulatory_changes.id'), nullable=False, index=True
    )
    
    # What to change
    config_target: Mapped[str] = mapped_column(String(50), nullable=False)
    # One of: 'CERT_SCORES', 'SOVEREIGNTY_KEYWORDS', 'SOVEREIGNTY_CERTS', 'MOAT_WEIGHTS'
    
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # One of: 'add', 'modify', 'remove'
    
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    # The cert name, keyword, or weight key. E.g. "DORA Compliant", "dora", "regulatory"
    
    current_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Current value if modifying (e.g. "35" for NIS2 Essential score)
    
    recommended_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Proposed value (e.g. "45" for elevated score, or null for removals)
    
    sovereignty_relevant: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # If True, cert should also be in SOVEREIGNTY_CERTS (jurisdiction-locked)
    
    # LLM reasoning
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    # One of: 'high', 'medium', 'low'
    
    # Approval workflow
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending', index=True)
    # One of: 'pending', 'approved', 'rejected', 'superseded'
    
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationship
    regulatory_change: Mapped["RegulatoryChange"] = relationship(
        "RegulatoryChange", backref="recommendations"
    )

    def __repr__(self):
        return f"<ScoringConfigRecommendation({self.action} {self.key} in {self.config_target}, status={self.status})>"

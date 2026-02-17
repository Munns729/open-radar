"""
Core lightweight data types for RADAR system.

These are transfer objects (Dataclasses), NOT database models.
For SQLAlchemy ORM models, see src/<module>/database.py.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from src.core.models import CompanyTier, ThreatLevel

@dataclass
class Company:
    """Standard company representation"""
    id: Optional[int] = None
    name: str = ""
    website: Optional[str] = None
    revenue_gbp: Optional[int] = None
    ebitda_gbp: Optional[int] = None
    ebitda_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    revenue_growth: Optional[float] = None # Year-over-year growth percentage
    employees: Optional[int] = None
    description: Optional[str] = None # Short business description
    sector: str = ""
    moat_type: str = "none"  # Thesis-driven pillar name
    moat_score: int = 0 # 0-100
    moat_attributes: Dict[str, Any] = field(default_factory=dict) # Detailed justifications
    tier: CompanyTier = CompanyTier.TIER_2
    certifications: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class ScraperOutput:
    """Standard scraper output"""
    source: str
    data_type: str
    data: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    row_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AIAnalysisOutput:
    """Standard AI analysis output"""
    input_id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    reasoning: str
    tokens_used: int = 0
    cost_usd: float = 0.0

@dataclass
class VCFirm:
    """Venture Capital Firm"""
    name: str
    hq_location: str
    aum_usd: Optional[int] = None
    focus_sectors: List[str] = field(default_factory=list)
    key_partners: List[str] = field(default_factory=list)

@dataclass
class VCAnnouncement:
    """VC Investment Announcement"""
    firm_name: str
    portfolio_company: str
    stage: str
    amount_raised_usd: Optional[int]
    date: datetime
    sector: str

@dataclass
class ThreatScore:
    """Competitive Threat Score"""
    company_id: int
    threat_level: ThreatLevel
    competitor_name: str
    details: str
    score_date: datetime = field(default_factory=datetime.now)

@dataclass
class PEFirm:
    """Private Equity Firm"""
    name: str
    aum_usd: Optional[int]
    strategy: str
    hq_country: str

@dataclass
class PEInvestment:
    """PE Investment Record"""
    firm_id: int
    target_company: str
    deal_date: datetime
    deal_type: str
    equity_ticket_usd: Optional[int]

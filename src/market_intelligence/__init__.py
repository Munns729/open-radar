"""
Market Intelligence Module - News Aggregation & Trend Analysis.
"""

from src.market_intelligence.database import (
    NewsSource,
    IntelligenceItem,
    RegulatoryChange,
    MarketTrend,
    WeeklyBriefing
)
from src.market_intelligence.workflow import run_intel_scan

__all__ = [
    "NewsSource",
    "IntelligenceItem",
    "RegulatoryChange",
    "MarketTrend",
    "WeeklyBriefing",
    "run_intel_scan"
]

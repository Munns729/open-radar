"""Database models for report configurations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    """Configuration for scheduled reports."""
    
    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="Type of report: 'targets', 'hot_targets', 'sector_focus'")
    output_format: str = Field(..., description="Output format: 'html', 'excel', 'table', 'all'")
    schedule: Optional[str] = Field(None, description="Cron schedule string")
    enabled: bool = Field(True, description="Whether report is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None


class ReportMetadata(BaseModel):
    """Metadata about generated report."""
    
    report_id: str
    generated_at: datetime
    total_companies: int
    tier_1a_count: int
    tier_1b_count: int
    hot_count: int
    high_count: int
    med_count: int
    low_count: int
    avg_moat_score: float
    total_revenue_gbp: float
    sectors: list[str]
    output_files: list[str]

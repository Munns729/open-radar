"""Filtering logic for reports."""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.universe.database import CompanyModel


class ReportFilters(BaseModel):
    """Filters for report generation."""
    
    tier: Optional[str] = Field(None, description="Filter by tier: '1A', '1B', 'both', 'all'")
    sector: Optional[List[str]] = Field(None, description="Filter by sectors (list)")
    min_moat: int = Field(50, ge=0, le=100, description="Minimum moat score")
    max_moat: int = Field(100, ge=0, le=100, description="Maximum moat score")
    min_revenue: Optional[float] = Field(None, description="Minimum revenue in GBP millions")
    max_revenue: Optional[float] = Field(None, description="Maximum revenue in GBP millions")
    min_employees: Optional[int] = Field(None, description="Minimum employees")
    max_employees: Optional[int] = Field(None, description="Maximum employees")
    priority: Optional[str] = Field(None, description="Priority level: 'hot', 'high', 'med', 'low', 'all'")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    
    @validator('tier')
    def validate_tier(cls, v):
        if v and v not in ['1A', '1B', 'both', 'all', None]:
            raise ValueError("tier must be '1A', '1B', 'both', or 'all'")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in ['hot', 'high', 'med', 'low', 'all', None]:
            raise ValueError("priority must be 'hot', 'high', 'med', 'low', or 'all'")
        return v
    
    @validator('max_moat')
    def validate_moat_range(cls, v, values):
        if 'min_moat' in values and v < values['min_moat']:
            raise ValueError("max_moat must be >= min_moat")
        return v


async def apply_filters(session: AsyncSession, filters: ReportFilters) -> List[CompanyModel]:
    """
    Apply filters to company query and return results.
    
    Args:
        session: Async database session
        filters: ReportFilters object
    
    Returns:
        List of CompanyModel objects matching filters
    """
    query = select(CompanyModel)
    
    # Tier filter
    if filters.tier and filters.tier != 'all':
        if filters.tier == 'both':
            query = query.filter(CompanyModel.tier.in_(['TIER_1A', 'TIER_1B']))
        else:
            query = query.filter(CompanyModel.tier == f"TIER_{filters.tier}")
    
    # Sector filter
    if filters.sector:
        query = query.filter(CompanyModel.sector.in_(filters.sector))
    
    # Moat score filter
    query = query.filter(
        CompanyModel.moat_score >= filters.min_moat,
        CompanyModel.moat_score <= filters.max_moat
    )
    
    # Priority filter (converts to moat score ranges)
    if filters.priority and filters.priority != 'all':
        if filters.priority == 'hot':
            query = query.filter(CompanyModel.moat_score >= 70)
        elif filters.priority == 'high':
            query = query.filter(CompanyModel.moat_score >= 50, CompanyModel.moat_score < 70)
        elif filters.priority == 'med':
            query = query.filter(CompanyModel.moat_score >= 30, CompanyModel.moat_score < 50)
        elif filters.priority == 'low':
            query = query.filter(CompanyModel.moat_score < 30)
    
    # Revenue filter
    if filters.min_revenue is not None:
        query = query.filter(CompanyModel.revenue_gbp >= filters.min_revenue * 1_000_000)
    if filters.max_revenue is not None:
        query = query.filter(CompanyModel.revenue_gbp <= filters.max_revenue * 1_000_000)
    
    # Employee filter
    if filters.min_employees is not None:
        query = query.filter(CompanyModel.employees >= filters.min_employees)
    if filters.max_employees is not None:
        query = query.filter(CompanyModel.employees <= filters.max_employees)
    
    # Order by moat score descending
    query = query.order_by(CompanyModel.moat_score.desc())
    
    # Limit
    if filters.limit:
        query = query.limit(filters.limit)
    
    # Execute query
    result = await session.execute(query)
    companies = result.scalars().all()
    
    return list(companies)


def get_priority_level(moat_score: int) -> str:
    """
    Get priority level from moat score.
    
    Args:
        moat_score: Moat score (0-100)
    
    Returns:
        Priority level: 'hot', 'high', 'med', or 'low'
    """
    if moat_score is None: # Handle None values safely
        return 'low'
        
    if moat_score >= 70:
        return 'hot'
    elif moat_score >= 50:
        return 'high'
    elif moat_score >= 30:
        return 'med'
    else:
        return 'low'


def get_priority_emoji(moat_score: int) -> str:
    """Get emoji for priority level."""
    priority = get_priority_level(moat_score)
    return {
        'hot': '🔴',
        'high': '🟠',
        'med': '🟡',
        'low': '⚪'
    }[priority]


def get_priority_color(moat_score: int) -> tuple[str, str]:
    """
    Get background and text colors for priority level.
    
    Returns:
        Tuple of (background_color, text_color) as hex codes
    """
    priority = get_priority_level(moat_score)
    colors = {
        'hot': ('#fee2e2', '#991b1b'),    # Red
        'high': ('#fed7aa', '#9a3412'),   # Orange
        'med': ('#fef3c7', '#92400e'),    # Yellow
        'low': ('#f3f4f6', '#4b5563')     # Gray
    }
    return colors[priority]

"""Intelligence router — deal comparables, valuations, market trends, hot sectors."""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc, and_, or_
from dateutil.relativedelta import relativedelta

from src.core.database import get_db
from src.core.schemas import StandardResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.deal_intelligence.database import DealRecord, DealComparable, MarketMetrics, DealProbability
from src.deal_intelligence.analytics import ComparablesEngine, MarketTrendsAnalyzer, DealProbabilityScorer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/intelligence",
    tags=["Deal Intelligence"]
)


@router.get("/deals", response_model=StandardResponse[list], summary="List Deals")
async def get_intelligence_deals(
    limit: int = 50,
    sector: Optional[str] = None,
    deal_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
):
    """List PE deals with optional filters."""
    stmt = select(DealRecord).order_by(desc(DealRecord.deal_date))

    if sector:
        stmt = stmt.where(DealRecord.sector == sector)
    if deal_type:
        stmt = stmt.where(DealRecord.deal_type == deal_type)
    if start_date:
        try:
            from datetime import datetime
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            stmt = stmt.where(DealRecord.deal_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import datetime
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            stmt = stmt.where(DealRecord.deal_date <= end)
        except ValueError:
            pass
    if min_value:
        stmt = stmt.where(DealRecord.enterprise_value_gbp >= min_value)
    if max_value:
        stmt = stmt.where(DealRecord.enterprise_value_gbp <= max_value)

    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    deals = result.scalars().all()

    data = [
        {
            "id": d.id,
            "target_company_name": d.target_company_name,
            "deal_date": d.deal_date.isoformat() if d.deal_date else None,
            "deal_type": d.deal_type,
            "sector": d.sector,
            "subsector": d.subsector,
            "geography": d.geography,
            "revenue_gbp": d.revenue_gbp,
            "ebitda_gbp": d.ebitda_gbp,
            "enterprise_value_gbp": d.enterprise_value_gbp,
            "ev_revenue_multiple": d.ev_revenue_multiple,
            "ev_ebitda_multiple": d.ev_ebitda_multiple,
            "equity_investment_gbp": d.equity_investment_gbp,
            "confidence_score": d.confidence_score,
            "source": d.source
        }
        for d in deals
    ]
    return StandardResponse(data=data)


@router.get("/deal/{deal_id}", response_model=StandardResponse[dict], summary="Deal Detail")
async def get_intelligence_deal_detail(
    deal_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get deal details with comparables."""
    stmt = select(DealRecord).where(DealRecord.id == deal_id)
    result = await session.execute(stmt)
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    comparables_stmt = select(DealComparable, DealRecord).join(
        DealRecord, DealComparable.comparable_deal_id == DealRecord.id
    ).where(
        DealComparable.deal_record_id == deal_id
    ).order_by(desc(DealComparable.similarity_score))

    comp_result = await session.execute(comparables_stmt)
    comparables = comp_result.all()

    return StandardResponse(data={
        "deal": {
            "id": deal.id,
            "target_company_name": deal.target_company_name,
            "deal_date": deal.deal_date.isoformat() if deal.deal_date else None,
            "deal_type": deal.deal_type,
            "sector": deal.sector,
            "subsector": deal.subsector,
            "geography": deal.geography,
            "revenue_gbp": deal.revenue_gbp,
            "ebitda_gbp": deal.ebitda_gbp,
            "enterprise_value_gbp": deal.enterprise_value_gbp,
            "ev_revenue_multiple": deal.ev_revenue_multiple,
            "ev_ebitda_multiple": deal.ev_ebitda_multiple,
            "equity_investment_gbp": deal.equity_investment_gbp,
            "debt_gbp": deal.debt_gbp,
            "confidence_score": deal.confidence_score,
            "source": deal.source,
            "source_url": deal.source_url,
            "notes": deal.notes
        },
        "comparables": [
            {
                "id": comp.id,
                "comparable_deal_id": comp_deal.id,
                "target_company_name": comp_deal.target_company_name,
                "deal_date": comp_deal.deal_date.isoformat() if comp_deal.deal_date else None,
                "sector": comp_deal.sector,
                "ev_ebitda_multiple": comp_deal.ev_ebitda_multiple,
                "ev_revenue_multiple": comp_deal.ev_revenue_multiple,
                "enterprise_value_gbp": comp_deal.enterprise_value_gbp,
                "similarity_score": comp.similarity_score,
                "similarity_reasons": comp.similarity_reasons
            }
            for comp, comp_deal in comparables
        ]
    })


@router.get("/comparables", response_model=StandardResponse[list], summary="Find Comparables")
async def find_deal_comparables(
    sector: str,
    revenue_gbp: Optional[int] = None,
    ebitda_gbp: Optional[int] = None,
    geography: Optional[str] = None,
    limit: int = 10,
    session: AsyncSession = Depends(get_db)
):
    """Find comparable deals for given criteria."""
    stmt = select(DealRecord).where(
        and_(
            DealRecord.sector == sector,
            or_(
                DealRecord.ev_ebitda_multiple.isnot(None),
                DealRecord.ev_revenue_multiple.isnot(None)
            )
        )
    )

    if revenue_gbp:
        min_rev = int(revenue_gbp * 0.5)
        max_rev = int(revenue_gbp * 2.0)
        stmt = stmt.where(DealRecord.revenue_gbp.between(min_rev, max_rev))

    if geography:
        stmt = stmt.where(DealRecord.geography == geography)

    stmt = stmt.order_by(desc(DealRecord.deal_date)).limit(limit)

    result = await session.execute(stmt)
    deals = result.scalars().all()

    data = [
        {
            "id": d.id,
            "target_company_name": d.target_company_name,
            "deal_date": d.deal_date.isoformat() if d.deal_date else None,
            "sector": d.sector,
            "geography": d.geography,
            "revenue_gbp": d.revenue_gbp,
            "enterprise_value_gbp": d.enterprise_value_gbp,
            "ev_ebitda_multiple": d.ev_ebitda_multiple,
            "ev_revenue_multiple": d.ev_revenue_multiple
        }
        for d in deals
    ]
    return StandardResponse(data=data)


@router.get("/market-trends", response_model=StandardResponse[list], summary="Market Trends History")
async def get_market_trends(
    sector: Optional[str] = None,
    months: int = 24,
    session: AsyncSession = Depends(get_db)
):
    """Get market metrics trends over time."""
    stmt = select(MarketMetrics).order_by(MarketMetrics.time_period)

    if sector:
        stmt = stmt.where(MarketMetrics.sector == sector)

    min_period = (date.today() - relativedelta(months=months)).strftime('%Y-%m')
    stmt = stmt.where(MarketMetrics.time_period >= min_period)

    result = await session.execute(stmt)
    metrics = result.scalars().all()

    data = [
        {
            "sector": m.sector,
            "time_period": m.time_period,
            "deal_count": m.deal_count,
            "total_value_gbp": m.total_value_gbp,
            "median_ev_revenue": m.median_ev_revenue,
            "median_ev_ebitda": m.median_ev_ebitda,
            "avg_ev_revenue": m.avg_ev_revenue,
            "avg_ev_ebitda": m.avg_ev_ebitda,
            "avg_growth_rate": m.avg_growth_rate,
            "avg_ebitda_margin": m.avg_ebitda_margin,
            "is_hot_sector": m.is_hot_sector
        }
        for m in metrics
    ]
    return StandardResponse(data=data)


@router.get("/valuation", response_model=StandardResponse[dict], summary="Estimate Valuation")
async def estimate_valuation(
    company_id: Optional[int] = None,
    revenue_gbp: Optional[int] = None,
    ebitda_gbp: Optional[int] = None,
    sector: Optional[str] = None,
    geography: str = "UK",
    session: AsyncSession = Depends(get_db)
):
    """Estimate valuation range for a company or given financial inputs."""
    engine = ComparablesEngine(session)

    result = await engine.calculate_valuation_range(
        company_id=company_id,
        revenue_gbp=revenue_gbp,
        ebitda_gbp=ebitda_gbp,
        sector=sector,
        geography=geography
    )

    return StandardResponse(data=result)


@router.get("/hot-sectors", response_model=StandardResponse[list], summary="Hot Sectors")
async def get_hot_sectors(
    months_lookback: int = 6,
    limit: int = 10,
    session: AsyncSession = Depends(get_db)
):
    """Get sectors with high deal activity and rising multiples."""
    analyzer = MarketTrendsAnalyzer(session)

    hot_sectors = await analyzer.detect_hot_sectors(
        months_lookback=months_lookback
    )

    return StandardResponse(data=hot_sectors[:limit])


@router.get("/deal-probability/{company_id}", response_model=StandardResponse[dict], summary="Deal Probability")
async def get_deal_probability(
    company_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get deal probability score for a company."""
    stmt = select(DealProbability).where(
        DealProbability.target_company_id == company_id
    )
    result = await session.execute(stmt)
    probability = result.scalar_one_or_none()

    if probability:
        return StandardResponse(data={
            "company_id": probability.target_company_id,
            "company_name": probability.target_company_name,
            "probability_score": probability.probability_score,
            "probability_tier": probability.probability_tier,
            "reasoning": probability.reasoning,
            "signals": probability.signals,
            "expected_timeline": probability.expected_timeline,
            "last_updated": probability.last_updated.isoformat() if probability.last_updated else None
        })

    scorer = DealProbabilityScorer(session)
    probability = await scorer.score_deal_likelihood(company_id)

    if not probability:
        raise HTTPException(status_code=404, detail="Company not found")

    session.add(probability)
    await session.commit()

    return StandardResponse(data={
        "company_id": probability.target_company_id,
        "company_name": probability.target_company_name,
        "probability_score": probability.probability_score,
        "probability_tier": probability.probability_tier,
        "reasoning": probability.reasoning,
        "signals": probability.signals,
        "expected_timeline": probability.expected_timeline,
        "last_updated": probability.last_updated.isoformat() if probability.last_updated else None
    })

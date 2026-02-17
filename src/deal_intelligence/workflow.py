"""
Data Enrichment Workflow for Module 4 - Deal Intelligence.
Orchestrates deal enrichment, market metrics calculation, and probability scoring.
"""
import asyncio
import logging
import json
import re
from typing import List, Optional
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory, engine, Base
from src.core.ai_client import ai_client
from src.deal_intelligence.database import (
    DealRecord, DealComparable, MarketMetrics, DealProbability
)
from src.deal_intelligence.analytics import (
    ComparablesEngine, MarketTrendsAnalyzer, DealProbabilityScorer
)
from src.capital.database import PEInvestmentModel, PEFirmModel
from src.universe.database import CompanyModel

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database tables for intelligence module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Intelligence database tables initialized.")


async def enrich_deals(batch_size: int = 20) -> int:
    """
    Enrich deal records with missing valuation data.
    
    Process:
    1. Query PEInvestmentModel records missing valuation data
    2. Use LLM to extract/estimate missing fields from available info
    3. Estimate missing multiples from comparables
    4. Create/update DealRecord entries
    
    Returns count of enriched deals.
    """
    logger.info("Starting deal enrichment workflow...")
    await init_db()
    
    enriched_count = 0
    
    async with async_session_factory() as session:
        # Find PE investments not yet enriched as DealRecords
        stmt = select(PEInvestmentModel, PEFirmModel).join(
            PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id
        ).limit(batch_size)
        
        result = await session.execute(stmt)
        investments = result.all()
        
        logger.info(f"Found {len(investments)} investments to process.")
        
        comparables_engine = ComparablesEngine(session)
        
        for investment, firm in investments:
            # Check if already exists in DealRecord
            existing_stmt = select(DealRecord).where(
                and_(
                    DealRecord.pe_firm_id == firm.id,
                    DealRecord.target_company_name == investment.company_name
                )
            )
            existing = await session.execute(existing_stmt)
            existing_record = existing.scalar_one_or_none()
            
            if existing_record and existing_record.is_enriched:
                continue
            
            # Create or update DealRecord
            if existing_record:
                deal = existing_record
            else:
                deal = DealRecord(
                    pe_firm_id=firm.id,
                    target_company_name=investment.company_name,
                    target_company_id=investment.company_id,
                    deal_date=investment.entry_date,
                    sector=investment.sector,
                    source="database"
                )
            
            # Enrich with available data
            deal.enterprise_value_gbp = investment.entry_valuation_usd  # Simplified; would convert currencies
            deal.ev_ebitda_multiple = float(investment.entry_multiple) if investment.entry_multiple else None
            
            # Try to estimate missing multiples using LLM
            if deal.sector and not deal.ev_ebitda_multiple:
                estimated = await _estimate_multiples_with_llm(
                    company_name=deal.target_company_name,
                    sector=deal.sector,
                    description=investment.description
                )
                
                if estimated:
                    deal.ev_ebitda_multiple = estimated.get('ev_ebitda')
                    deal.ev_revenue_multiple = estimated.get('ev_revenue')
                    deal.confidence_score = estimated.get('confidence', 50)
            
            deal.is_enriched = True
            deal.enrichment_date = datetime.utcnow()
            
            if not existing_record:
                session.add(deal)
            
            enriched_count += 1
        
        await session.commit()
        logger.info(f"Enriched {enriched_count} deal records.")
    
    return enriched_count


async def _estimate_multiples_with_llm(
    company_name: str,
    sector: str,
    description: str = None
) -> Optional[dict]:
    """
    Use LLM to estimate valuation multiples based on company characteristics.
    """
    prompt = f"""Estimate typical PE transaction multiples for this company:

Company: {company_name}
Sector: {sector}
Description: {description or 'Not available'}

Based on typical PE transactions in the {sector} sector, estimate:
1. EV/EBITDA multiple (typical range for this type of business)
2. EV/Revenue multiple (if applicable)
3. Confidence level (0-100)

Respond in JSON format:
{{"ev_ebitda": 8.5, "ev_revenue": 2.0, "confidence": 60, "reasoning": "..."}}

If you cannot estimate, respond: {{"error": "reason"}}"""

    system_prompt = """You are a PE valuation expert. Provide realistic multiple estimates 
based on current market conditions and typical sector valuations. Be conservative 
and always include confidence levels."""

    try:
        response = await ai_client.generate(prompt, system_prompt, temperature=0.3)
        
        # Parse JSON response
        # Robust extraction using regex
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        else:
            # Fallback
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
        
        data = json.loads(response.strip())
        
        if 'error' in data:
            logger.warning(f"LLM could not estimate multiples: {data['error']}")
            return None
        
        return data
    
    except Exception as e:
        logger.error(f"LLM estimation failed: {e}", exc_info=True)
        return None


async def update_market_metrics(months_lookback: int = 24) -> int:
    """
    Aggregate deal data to calculate market metrics by sector and time period.
    
    Process:
    1. Query all deals in lookback window
    2. Group by sector and month
    3. Calculate median multiples, deal counts, volumes
    4. Store in MarketMetrics table
    
    Returns count of metrics records created/updated.
    """
    logger.info(f"Updating market metrics (lookback: {months_lookback} months)...")
    await init_db()
    
    metrics_count = 0
    
    async with async_session_factory() as session:
        analyzer = MarketTrendsAnalyzer(session)
        
        # Get distinct sectors
        sector_stmt = select(DealRecord.sector).where(
            DealRecord.sector.isnot(None)
        ).distinct()
        
        result = await session.execute(sector_stmt)
        sectors = [row[0] for row in result.all()]
        
        logger.info(f"Processing {len(sectors)} sectors...")
        
        end_date = date.today()
        start_date = end_date - relativedelta(months=months_lookback)
        
        for sector in sectors:
            # Calculate metrics for sector
            metrics_list = await analyzer.calculate_sector_metrics(
                sector=sector,
                time_range=(start_date, end_date)
            )
            
            for metric in metrics_list:
                # Upsert logic
                existing_stmt = select(MarketMetrics).where(
                    and_(
                        MarketMetrics.sector == metric.sector,
                        MarketMetrics.time_period == metric.time_period,
                        MarketMetrics.geography == metric.geography
                    )
                )
                existing = await session.execute(existing_stmt)
                existing_record = existing.scalar_one_or_none()
                
                if existing_record:
                    # Update existing
                    existing_record.deal_count = metric.deal_count
                    existing_record.total_value_gbp = metric.total_value_gbp
                    existing_record.median_ev_revenue = metric.median_ev_revenue
                    existing_record.median_ev_ebitda = metric.median_ev_ebitda
                    existing_record.avg_ev_revenue = metric.avg_ev_revenue
                    existing_record.avg_ev_ebitda = metric.avg_ev_ebitda
                    existing_record.deal_count_change_pct = metric.deal_count_change_pct
                    existing_record.updated_at = datetime.utcnow()
                else:
                    session.add(metric)
                
                metrics_count += 1
        
        # Detect and flag hot sectors
        hot_sectors = await analyzer.detect_hot_sectors()
        
        for hot in hot_sectors:
            if hot['is_hot']:
                # Update latest period for this sector
                update_stmt = select(MarketMetrics).where(
                    MarketMetrics.sector == hot['sector']
                ).order_by(MarketMetrics.time_period.desc()).limit(1)
                
                result = await session.execute(update_stmt)
                record = result.scalar_one_or_none()
                
                if record:
                    record.is_hot_sector = True
        
        await session.commit()
        logger.info(f"Created/updated {metrics_count} market metrics records.")
    
    return metrics_count


async def score_deal_probabilities(
    tier_filter: List[str] = None,
    batch_size: int = 50
) -> int:
    """
    Score deal probability for companies in the universe.
    
    Process:
    1. Get companies (optionally filtered by tier)
    2. Run DealProbabilityScorer for each
    3. Save/update DealProbability records
    
    Returns count of companies scored.
    """
    logger.info("Scoring deal probabilities for universe...")
    await init_db()
    
    if tier_filter is None:
        tier_filter = ["1A", "1B"]  # Default to Tier 1 companies
    
    scored_count = 0
    
    async with async_session_factory() as session:
        # Get companies in target tiers
        stmt = select(CompanyModel)
        
        if tier_filter:
            # Filter by tier enum values
            from src.core.models import CompanyTier
            tier_enums = []
            for t in tier_filter:
                if t == "1A":
                    tier_enums.append(CompanyTier.TIER_1A)
                elif t == "1B":
                    tier_enums.append(CompanyTier.TIER_1B)
                elif t == "2":
                    tier_enums.append(CompanyTier.TIER_2)
            
            if tier_enums:
                stmt = stmt.where(CompanyModel.tier.in_(tier_enums))
        
        stmt = stmt.limit(batch_size)
        
        result = await session.execute(stmt)
        companies = result.scalars().all()
        
        logger.info(f"Scoring {len(companies)} companies...")
        
        scorer = DealProbabilityScorer(session)
        
        for company in companies:
            try:
                probability = await scorer.score_deal_likelihood(company.id)
                
                if probability:
                    # Upsert
                    existing_stmt = select(DealProbability).where(
                        DealProbability.target_company_id == company.id
                    )
                    existing = await session.execute(existing_stmt)
                    existing_record = existing.scalar_one_or_none()
                    
                    if existing_record:
                        # Update existing record
                        existing_record.probability_score = probability.probability_score
                        existing_record.probability_tier = probability.probability_tier
                        existing_record.reasoning = probability.reasoning
                        existing_record.signals = probability.signals
                        existing_record.signal_declining_growth = probability.signal_declining_growth
                        existing_record.signal_pe_sector_interest = probability.signal_pe_sector_interest
                        existing_record.expected_timeline = probability.expected_timeline
                        existing_record.last_updated = datetime.utcnow()
                        existing_record.is_stale = False
                    else:
                        session.add(probability)
                    
                    scored_count += 1
                    
            except Exception as e:
                logger.error(f"Error scoring company {company.id}: {e}")
                continue
        
        await session.commit()
        logger.info(f"Scored {scored_count} companies for deal probability.")
    
    return scored_count


async def run_full_intelligence_workflow():
    """
    Run the complete intelligence workflow:
    1. Enrich deals from capital flows
    2. Update market metrics
    3. Score deal probabilities
    """
    logger.info("=" * 50)
    logger.info("Running Full Deal Intelligence Workflow")
    logger.info("=" * 50)
    
    # Step 1: Enrich deals
    logger.info("\n[Step 1/3] Enriching deals...")
    enriched = await enrich_deals()
    
    # Step 2: Update market metrics
    logger.info("\n[Step 2/3] Updating market metrics...")
    metrics = await update_market_metrics()
    
    # Step 3: Score probabilities
    logger.info("\n[Step 3/3] Scoring deal probabilities...")
    scored = await score_deal_probabilities()
    
    logger.info("\n" + "=" * 50)
    logger.info("Workflow Complete")
    logger.info(f"  - Deals enriched: {enriched}")
    logger.info(f"  - Metrics updated: {metrics}")
    logger.info(f"  - Companies scored: {scored}")
    logger.info("=" * 50)
    
    return {
        'deals_enriched': enriched,
        'metrics_updated': metrics,
        'companies_scored': scored
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(run_full_intelligence_workflow())

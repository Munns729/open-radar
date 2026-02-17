import asyncio
import logging
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

# Use absolute imports or assume existing session factory
try:
    from src.core.database import async_session_factory
except ImportError:
    # Fallback/Mock for standalone run capability if core not set up fully in this env
    async_session_factory = None

from src.market_intelligence.sources.news_aggregator import NewsAggregator
from src.market_intelligence.sources.regulatory_monitor import RegulatoryMonitor
from src.market_intelligence.analyzers.relevance_scorer import RelevanceScorer
from src.market_intelligence.synthesizers.weekly_briefing import WeeklyBriefingGenerator
from src.market_intelligence.database import NewsSource
from src.core.notifications import email_client
from sqlalchemy import select

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def run_intel_scan():
    """Daily workflow: fetch, save, score."""
    if not async_session_factory:
        logger.error("Database session factory not available.")
        return

    async with async_session_factory() as session:
        # 1. Fetch & Save
        aggregator = NewsAggregator(session)
        
        # Get active sources
        stmt = select(NewsSource).where(NewsSource.is_active == True)
        result = await session.execute(stmt)
        sources = result.scalars().all()
        
        if not sources:
            logger.info("No sources found. Adding defaults...")
            # Seed some defaults if empty
            await aggregator.add_source("TechCrunch", "http://feeds.feedburner.com/TechCrunch/", "fintech")
            stmt = select(NewsSource).where(NewsSource.is_active == True)
            result = await session.execute(stmt)
            sources = result.scalars().all()

        for source in sources:
            await aggregator.process_source(source)
            
        # 2. Regulatory Monitor (expanded: UK, FR, DE, EU)
        monitor = RegulatoryMonitor(session)
        new_changes = await monitor.run_all_monitors()
        
        # 3. Score News Relevance
        scorer = RelevanceScorer(session)
        await scorer.process_unscored_items()
        
        # 4. Analyze Regulatory Changes for Scoring Impact
        if new_changes:
            from src.market_intelligence.analyzers.scoring_impact_analyzer import ScoringImpactAnalyzer
            impact_analyzer = ScoringImpactAnalyzer(session)
            recommendations = await impact_analyzer.analyze_new_changes(new_changes)
            
            if recommendations:
                logger.info(f"Generated {len(recommendations)} scoring config recommendations")
        
    logger.info("Daily scan complete.")

async def generate_market_briefing():
    """Weekly workflow."""
    if not async_session_factory:
       return

    async with async_session_factory() as session:
        gen = WeeklyBriefingGenerator(session)
        briefing = await gen.generate_briefing(date.today())
        
        # Send Email
        subject = f"Market Intelligence Briefing - Week of {briefing.week_starting}"
        html_content = f"""
        <h1>Market Intelligence Briefing</h1>
        <p><strong>Date:</strong> {briefing.week_starting}</p>
        
        <h2>Executive Summary</h2>
        <p>{briefing.executive_summary}</p>
        
        <h2>Top Regulatory Changes</h2>
        <ul>{''.join([f'<li>{item}</li>' for item in (briefing.top_regulatory_changes or [])])}</ul>
        
        <h2>Emerging Trends</h2>
        <ul>{''.join([f'<li>{item}</li>' for item in (briefing.emerging_trends or [])])}</ul>
        
        <h2>Thesis Implications</h2>
        <p>{briefing.thesis_implications}</p>
        
        <h2>Action Items</h2>
        <ul>{''.join([f'<li>{item}</li>' for item in (briefing.action_items or [])])}</ul>
        """
        
        # Send to team (placeholder email)
        email_client.send_email("team@radar-pe.com", subject, html_content)


if __name__ == "__main__":
    # Barebones test run
    # Note: Requires DB to be set up.
    print("Running intel scan workflow...")
    asyncio.run(run_intel_scan())

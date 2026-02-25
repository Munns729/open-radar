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

        # TODO: wire market_intelligence to capability signal detection
        # When news items are processed, check headlines against CapabilitySignalDefinition labels
        # and auto-log via: from src.capability.service import record_signal_observation
        # Manual logging is available at POST /api/capability/observations in the meantime
        logger.debug("Capability signal auto-detection: not yet wired — use manual endpoint")

        # 4. Analyze Regulatory Changes for Scoring Impact
        if new_changes:
            from src.market_intelligence.analyzers.scoring_impact_analyzer import ScoringImpactAnalyzer
            impact_analyzer = ScoringImpactAnalyzer(session)
            recommendations = await impact_analyzer.analyze_new_changes(new_changes)
            
            if recommendations:
                logger.info(f"Generated {len(recommendations)} scoring config recommendations")
        
    logger.info("Daily scan complete.")

async def generate_market_briefing():
    """Weekly workflow. Generates briefing, saves locally, optionally emails."""
    if not async_session_factory:
        logger.error("No session factory. Cannot generate briefing.")
        return None

    async with async_session_factory() as session:
        gen = WeeklyBriefingGenerator(session)
        briefing = await gen.generate_briefing()
        
        # Save markdown locally (always works, no external deps)
        from pathlib import Path
        md_content = gen.render_markdown(briefing)
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        # Write timestamped version
        ts_path = output_dir / f"briefing_{briefing.week_starting}.md"
        ts_path.write_text(md_content)
        logger.info(f"Briefing saved to {ts_path}")
        
        # Overwrite latest_briefing.md for quick access (in outputs with other briefings)
        latest_path = output_dir / "latest_briefing.md"
        latest_path.write_text(md_content)
        logger.info(f"Latest briefing updated: {latest_path}")
        
        # Email if configured
        if email_client.sg:
            html_content = gen.render_html(briefing)
            subject = f"RADAR Weekly Briefing — {briefing.week_starting}"
            from src.core.config import settings
            to_addr = settings.admin_email or settings.sendgrid_from_email
            if to_addr:
                email_client.send_email(to_addr, subject, html_content)
        
        return briefing


if __name__ == "__main__":
    # Barebones test run
    # Note: Requires DB to be set up.
    print("Running intel scan workflow...")
    asyncio.run(run_intel_scan())

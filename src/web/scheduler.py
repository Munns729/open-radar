import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.database import get_async_db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def run_weekly_briefing():
    """
    Job function to generate the weekly briefing.
    Uses the market_intelligence workflow which handles local save + email.
    """
    logger.info("Running scheduled job: Weekly Briefing")
    try:
        from src.market_intelligence.workflow import generate_market_briefing
        briefing = await generate_market_briefing()
        if briefing:
            logger.info(f"Weekly Briefing generated for {briefing.week_starting}")
        else:
            logger.warning("Briefing generation returned None")
    except Exception as e:
        logger.error(f"Failed to run weekly briefing job: {e}", exc_info=True)

async def run_daily_pipeline():
    """
    Job function: enrichment + scoring + tier detection.
    Runs the pipeline without discovery or briefing (those are separate cadences).
    """
    logger.info("Running scheduled job: Daily Pipeline")
    try:
        from scripts.canonical.run_daily_pipeline import run_pipeline
        await run_pipeline(
            skip_enrich=False,
            skip_scoring=False,
            skip_briefing=True,  # briefing runs weekly
            include_discovery=False,
        )
    except Exception as e:
        logger.error(f"Daily pipeline failed: {e}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the scheduler.
    """
    # Daily: enrich + score + tier detect (6:00 AM)
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=6, minute=0),
        id='daily_pipeline',
        replace_existing=True
    )
    
    # Weekly: full briefing (Monday 8:00 AM, after daily pipeline completes)
    scheduler.add_job(
        run_weekly_briefing,
        CronTrigger(day_of_week='mon', hour=8, minute=0),
        id='weekly_briefing',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started. Daily pipeline at 6am, Weekly briefing Mondays 8am.")

async def stop_scheduler():
    """
    Shutdown the scheduler.
    """
    logger.info("Stopping APScheduler...")
    scheduler.shutdown()

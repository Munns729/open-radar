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


async def run_stale_canon_check():
    """Mark canons not refreshed in 90 days as stale."""
    logger.info("Running scheduled stale Canon check...")
    try:
        from src.canon.service import mark_stale_canons
        count = await mark_stale_canons(stale_days=90)
        logger.info(f"Stale canon check complete: {count} records marked stale")
    except Exception as e:
        logger.error(f"Stale canon check failed: {e}", exc_info=True)


async def run_proposal_expiry():
    """Auto-expire pending canon proposals past their expires_at."""
    logger.info("Running proposal expiry check...")
    try:
        from src.canon.service import expire_stale_proposals
        count = await expire_stale_proposals()
        logger.info(f"Auto-expired {count} stale proposals")
    except Exception as e:
        logger.error(f"Proposal expiry failed: {e}", exc_info=True)


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

    # Daily: mark stale canons (6:30 AM)
    scheduler.add_job(
        run_stale_canon_check,
        CronTrigger(hour=6, minute=30),
        id='stale_canon_check',
        replace_existing=True
    )

    # Daily: expire stale canon proposals (7:00 AM)
    scheduler.add_job(
        run_proposal_expiry,
        CronTrigger(hour=7, minute=0),
        id='proposal_expiry',
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
    logger.info("APScheduler started. Daily pipeline 6am, Stale canon 6:30am, Proposal expiry 7am, Weekly briefing Mondays 8am.")

    import asyncio
    from src.capability.seed import seed_capability_data
    asyncio.ensure_future(seed_capability_data())

async def stop_scheduler():
    """
    Shutdown the scheduler.
    """
    logger.info("Stopping APScheduler...")
    scheduler.shutdown()

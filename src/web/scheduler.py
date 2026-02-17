import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.database import get_async_db
from src.core.config import settings
from src.core.notifications import email_client
from src.market_intelligence.synthesizers.weekly_briefing import WeeklyBriefingGenerator

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def run_weekly_briefing():
    """
    Job function to generate the weekly briefing.
    """
    logger.info("Running scheduled job: Weekly Briefing")
    try:
        async with get_async_db() as session:
            generator = WeeklyBriefingGenerator(session)
            briefing = await generator.generate_briefing()
            
            # Render Markdown for logs
            markdown_report = generator.render_markdown(briefing)
            logger.info(f"Weekly Briefing Generated:\n{markdown_report[:200]}...")
            
            # Send Email
            if settings.admin_email:
                html_report = generator.render_html(briefing)
                subject = f"RADAR Weekly Briefing: {briefing.week_starting}"
                success = email_client.send_email(
                    to_email=settings.admin_email,
                    subject=subject,
                    html_content=html_report
                )
                if success:
                    logger.info(f"Briefing emailed to {settings.admin_email}")
                else:
                    logger.error("Failed to email briefing.")
            else:
                logger.warning("No ADMIN_EMAIL set. Briefing not emailed.")
            
    except Exception as e:
        logger.error(f"Failed to run weekly briefing job: {e}", exc_info=True)

def start_scheduler():
    """
    Initialize and start the scheduler.
    """
    # Schedule Weekly Briefing for Monday at 8:00 AM
    scheduler.add_job(
        run_weekly_briefing,
        CronTrigger(day_of_week='mon', hour=8, minute=0),
        id='weekly_briefing',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started. Weekly Briefing scheduled for Mondays at 8am.")

async def stop_scheduler():
    """
    Shutdown the scheduler.
    """
    logger.info("Stopping APScheduler...")
    scheduler.shutdown()

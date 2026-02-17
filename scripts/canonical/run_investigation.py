"""
Run a competitive investigation loop.
Currently uses manual targets for demonstration.
"""
import asyncio
import logging
from src.competitive.database import MonitoringTargetModel, init_db
from src.core.database import get_sync_db
from src.competitive.web_monitor import WebMonitor
from src.competitive.pricing_tracker import PricingTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Investigation")

TARGETS = [
    {
        "company": "Linear",
        "url": "https://linear.app/pricing",
        "type": "pricing"
    },
    {
        "company": "OpenAI",
        "url": "https://openai.com/about",
        "type": "team"
    }
]

async def run():
    init_db()
    
    # 1. Seed Targets if missing
    with get_sync_db() as session:
        for t in TARGETS:
            exists = session.query(MonitoringTargetModel).filter_by(url=t['url']).first()
            if not exists:
                logger.info(f"Adding target: {t['company']}")
                mt = MonitoringTargetModel(
                    company_name=t['company'],
                    url=t['url'],
                    target_type=t['type']
                )
                session.add(mt)
    
    # 2. Run Monitors
    logger.info("Running Pricing Tracker...")
    async with PricingTracker(headless=True) as tracker:
        await tracker.run_monitor_loop()
        
    logger.info("Investigation Complete.")

if __name__ == "__main__":
    asyncio.run(run())

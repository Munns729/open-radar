import asyncio
import sys
import os
import logging
from sqlalchemy import select

# Add src to path
sys.path.append(os.getcwd())

from src.core.database import async_session_factory
from src.market_intelligence.analyzers.trend_detector import TrendDetector
from src.market_intelligence.database import MarketTrend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_detection():
    async with async_session_factory() as session:
        logger.info("Initializing TrendDetector...")
        detector = TrendDetector(session)
        
        logger.info("Running detection (looking back 30 days)...")
        trends = await detector.detect_trends(lookback_days=30)
        
        if trends:
            logger.info(f"Successfully detected {len(trends)} trends:")
            for t in trends:
                logger.info(f" - {t['trend_name']} ({t['strength']}): {t['trend_type']}")
        else:
            logger.info("No trends detected (possibly insufficient high-relevance data or API issue).")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_detection())

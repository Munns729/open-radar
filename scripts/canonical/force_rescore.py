import asyncio
import sys
import os
import logging
from sqlalchemy import select, update, func

sys.path.append(os.getcwd())

from src.core.database import async_session_factory
from src.market_intelligence.database import IntelligenceItem
from src.market_intelligence.analyzers.relevance_scorer import RelevanceScorer
from src.market_intelligence.analyzers.trend_detector import TrendDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    async with async_session_factory() as session:
        # 1. Reset scores for testing (limit to 10 most recent to save tokens)
        logger.info("Resetting scores for top 10 recent items...")
        
        # Get IDs of recent items
        recent_items = await session.execute(
            select(IntelligenceItem.id)
            .order_by(IntelligenceItem.published_date.desc())
            .limit(10)
        )
        ids = recent_items.scalars().all()
        
        if not ids:
            logger.info("No items found.")
            return

        # Set score to None so scorer picks them up
        await session.execute(
            update(IntelligenceItem)
            .where(IntelligenceItem.id.in_(ids))
            .values(relevance_score=None, summary=None)
        )
        await session.commit()
        
        # 2. Run Scorer
        logger.info("Running RelevanceScorer with Kimi...")
        scorer = RelevanceScorer(session)
        await scorer.process_unscored_items(limit=10)
        
        # 3. Verify Scores
        scored_items = await session.execute(
            select(IntelligenceItem)
            .where(IntelligenceItem.id.in_(ids))
        )
        for item in scored_items.scalars():
            logger.info(f"[{item.relevance_score}] {item.title[:50]}...")

        # 4. Run Trend Detection
        logger.info("Running TrendDetector...")
        detector = TrendDetector(session)
        trends = await detector.detect_trends(lookback_days=30)
        
        if trends:
            logger.info(f"Detected {len(trends)} trends!")
            for t in trends:
                logger.info(f" > {t['trend_name']}")
        else:
            logger.info("No trends detected yet.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

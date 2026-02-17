"""
Backfill scoring data for existing companies and divisions.
Populates new fields required for the refactored MoatScorer and OperationalAutonomyScorer.
"""
import asyncio
import logging
import random
from sqlalchemy import select
from src.core.database import async_session_factory, Base, engine
from src.universe.database import CompanyModel, Base as UniverseBase
from src.carveout.database import Division
from src.carveout.workflow import EUR_TO_GBP_RATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Backfill")

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Create core tables (Carveout)
        await conn.run_sync(Base.metadata.create_all)
        # Create universe tables (Companies)
        await conn.run_sync(UniverseBase.metadata.create_all)

async def backfill():
    logger.info("Starting Backfill...")
    await init_db()
    
    async with async_session_factory() as session:
        # 1. Backfill Companies
        logger.info("Backfilling Companies...")
        result = await session.execute(select(CompanyModel))
        companies = result.scalars().all()
        
        for company in companies:
            if company.market_share is None:
                company.market_share = round(random.uniform(5.0, 35.0), 2)
            if company.competitor_count is None:
                company.competitor_count = random.randint(3, 12)
            if company.market_growth_rate is None:
                company.market_growth_rate = round(random.uniform(1.0, 10.0), 2)
            
            # Ensure revenue_gbp is populated if missing
            if company.revenue_gbp is None:
                # Mock revenue between 50M and 5B GBP
                company.revenue_gbp = random.randint(50_000_000, 5_000_000_000) 
                
        logger.info(f"Updated {len(companies)} companies.")
        
        # 2. Backfill Divisions
        logger.info("Backfilling Divisions...")
        result = await session.execute(select(Division))
        divisions = result.scalars().all()
        
        for div in divisions:
            if div.revenue_eur and not div.revenue_gbp:
                div.revenue_gbp = int(div.revenue_eur * EUR_TO_GBP_RATE)
            
            if div.ebitda_eur and not div.ebitda_gbp:
                div.ebitda_gbp = int(div.ebitda_eur * EUR_TO_GBP_RATE)
                
            if not div.strategic_autonomy:
                div.strategic_autonomy = random.choice(['core', 'non_core', 'strategic_review', 'standalone'])

        logger.info(f"Updated {len(divisions)} divisions.")
        
        await session.commit()
        logger.info("Backfill Complete.")

if __name__ == "__main__":
    asyncio.run(backfill())

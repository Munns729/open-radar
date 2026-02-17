import asyncio
import logging
import sys
import os

# Ensure src is in path
sys.path.append(".")

from src.core.database import async_session_factory, Base, engine
from src.tracker.database import TrackedCompany, CompanyEvent, TrackingAlert, AlertPreference, TrackingStatus, EventSeverity
from src.alerts.alert_engine import alert_engine
from src.universe.database import CompanyModel
from sqlalchemy import select, delete

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_verification():
    logger.info("Starting Alert System Verification...")
    
    async with async_session_factory() as session:
        # 1. Cleanup previous test data
        logger.info("Cleaning up old test data...")
        await session.execute(delete(TrackingAlert))
        await session.execute(delete(CompanyEvent))
        await session.execute(delete(TrackedCompany))
        await session.execute(delete(CompanyModel).where(CompanyModel.name == "Test Company Inc."))
        await session.commit()
        
        # 2. Setup Test Data
        logger.info("Creating test company...")
        company = CompanyModel(name="Test Company Inc.", sector="Technology", hq_country="US")
        session.add(company)
        await session.commit()
        await session.refresh(company)
        
        tracked = TrackedCompany(company_id=company.id, tracking_status=TrackingStatus.ACTIVE)
        session.add(tracked)
        await session.commit()
        await session.refresh(tracked)
        
        logger.info(f"Created Tracked Company ID: {tracked.id}")
        
        # 3. Create Event
        logger.info("Creating test event...")
        event = CompanyEvent(
            tracked_company_id=tracked.id,
            event_type="funding",
            title="Tests Raised Series Z",
            description="A huge round of funding for testing purposes.",
            severity=EventSeverity.HIGH,
            source_url="http://test.com"
        )
        session.add(event)
        await session.commit()
        
        # 4. Run Alert Engine
        logger.info("Running Alert Engine...")
        await alert_engine.check_alerts()
        
        # 5. Verify Alert Created
        logger.info("Verifying alert creation...")
        stmt = select(TrackingAlert).where(TrackingAlert.tracked_company_id == tracked.id)
        result = await session.execute(stmt)
        alerts = result.scalars().all()
        
        if len(alerts) >= 1:
            logger.info(f"SUCCESS: {len(alerts)} alerts found.")
            for a in alerts:
                logger.info(f"Alert: {a.message} (Read: {a.is_read})")
        else:
            logger.error("FAILURE: No alerts found!")
            
if __name__ == "__main__":
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_verification())
    except Exception as e:
        logger.error(f"Verification Failed: {e}")

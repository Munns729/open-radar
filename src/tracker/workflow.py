"""
Workflow orchestrator for Module 3 - Target Tracker.

Updates tracked companies by detecting new events and generating alerts.
"""
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.tracker.database import (
    TrackedCompany, 
    CompanyEvent, 
    TrackingAlert,
    TrackingStatus,
    EventSeverity
)
from src.tracker.enricher import CompanyEnricher

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_tracked_companies(
    company_ids: Optional[List[int]] = None,
    force_check: bool = False
) -> dict:
    """
    Main workflow to update all tracked companies.
    
    For each active tracked company:
    1. Detect new events since last check
    2. Save events to database
    3. Create alerts for critical/high severity events
    4. Update last_checked timestamp
    
    Args:
        company_ids: Optional list of specific tracked company IDs to update.
                    If None, updates all active tracked companies.
        force_check: If True, check all companies regardless of next_check_due.
        
    Returns:
        Dict with summary statistics.
    """
    stats = {
        "companies_checked": 0,
        "events_detected": 0,
        "alerts_created": 0,
        "errors": 0,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }
    
    logger.info("Starting tracker update workflow...")
    
    enricher = CompanyEnricher()
    
    async with async_session_factory() as session:
        # Query active tracked companies
        stmt = select(TrackedCompany).where(
            TrackedCompany.tracking_status == TrackingStatus.ACTIVE.value
        )
        
        if company_ids:
            stmt = stmt.where(TrackedCompany.id.in_(company_ids))
        elif not force_check:
            # Only check companies that are due for checking
            stmt = stmt.where(
                (TrackedCompany.next_check_due == None) |
                (TrackedCompany.next_check_due <= datetime.utcnow())
            )
        
        result = await session.execute(stmt)
        tracked_companies = result.scalars().all()
        
        logger.info(f"Found {len(tracked_companies)} companies to update")
        
        for tracked in tracked_companies:
            try:
                logger.info(f"Processing tracked company ID {tracked.id} (company_id: {tracked.company_id})")
                
                # Determine the "since" date for event detection
                since = tracked.last_checked or (datetime.utcnow() - timedelta(days=30))
                
                # Detect new events
                new_events = await enricher.detect_events(tracked.company_id, since)
                
                # Save events
                for event in new_events:
                    event.tracked_company_id = tracked.id
                    session.add(event)
                    stats["events_detected"] += 1
                    
                    # Create alert for critical/high severity events
                    if event.severity in [EventSeverity.CRITICAL.value, EventSeverity.HIGH.value]:
                        alert = TrackingAlert(
                            tracked_company_id=tracked.id,
                            alert_type=event.event_type,
                            message=f"[{event.severity.upper()}] {event.title}",
                            is_read=False,
                        )
                        session.add(alert)
                        stats["alerts_created"] += 1
                        logger.info(f"Created alert for event: {event.title[:50]}...")
                
                # Update timestamps
                tracked.last_checked = datetime.utcnow()
                
                # Set next check based on priority
                if tracked.priority == "high":
                    tracked.next_check_due = datetime.utcnow() + timedelta(days=1)
                elif tracked.priority == "medium":
                    tracked.next_check_due = datetime.utcnow() + timedelta(days=3)
                else:
                    tracked.next_check_due = datetime.utcnow() + timedelta(days=7)
                
                stats["companies_checked"] += 1
                
            except Exception as e:
                logger.error(f"Error processing tracked company {tracked.id}: {e}", exc_info=True)
                stats["errors"] += 1
        
        # Commit all changes
        await session.commit()
    
    stats["completed_at"] = datetime.utcnow().isoformat()
    
    # Log summary
    logger.info("=" * 50)
    logger.info("TRACKER UPDATE COMPLETE")
    logger.info(f"  Companies checked: {stats['companies_checked']}")
    logger.info(f"  Events detected:   {stats['events_detected']}")
    logger.info(f"  Alerts created:    {stats['alerts_created']}")
    logger.info(f"  Errors:            {stats['errors']}")
    logger.info("=" * 50)
    
    return stats


async def add_company_to_tracking(
    company_id: int,
    priority: str = "medium",
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> TrackedCompany:
    """
    Add a company to tracking.
    
    Args:
        company_id: The ID of the company from the universe database.
        priority: Priority level (high/medium/low).
        tags: Optional list of tags.
        notes: Optional notes about the company.
        
    Returns:
        The created TrackedCompany record.
    """
    async with async_session_factory() as session:
        # Check if already tracked
        stmt = select(TrackedCompany).where(TrackedCompany.company_id == company_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Company {company_id} is already being tracked (ID: {existing.id})")
            # Reactivate if closed
            if existing.tracking_status == TrackingStatus.CLOSED.value:
                existing.tracking_status = TrackingStatus.ACTIVE.value
                existing.priority = priority
                await session.commit()
            return existing
        
        # Create new tracking record
        tracked = TrackedCompany(
            company_id=company_id,
            tracking_status=TrackingStatus.ACTIVE.value,
            priority=priority,
            tags=tags or [],
            notes=notes,
            added_date=datetime.utcnow(),
            next_check_due=datetime.utcnow(),  # Check immediately
        )
        session.add(tracked)
        await session.commit()
        await session.refresh(tracked)
        
        logger.info(f"Added company {company_id} to tracking with ID {tracked.id}")
        return tracked


async def remove_company_from_tracking(tracked_id: int, hard_delete: bool = False) -> bool:
    """
    Remove a company from tracking.
    
    Args:
        tracked_id: The ID of the tracked company record.
        hard_delete: If True, permanently delete. Otherwise, mark as closed.
        
    Returns:
        True if successful, False otherwise.
    """
    async with async_session_factory() as session:
        stmt = select(TrackedCompany).where(TrackedCompany.id == tracked_id)
        result = await session.execute(stmt)
        tracked = result.scalar_one_or_none()
        
        if not tracked:
            logger.warning(f"Tracked company {tracked_id} not found")
            return False
        
        if hard_delete:
            await session.delete(tracked)
            logger.info(f"Permanently deleted tracked company {tracked_id}")
        else:
            tracked.tracking_status = TrackingStatus.CLOSED.value
            logger.info(f"Closed tracking for company {tracked_id}")
        
        await session.commit()
        return True


async def get_unread_alerts(limit: int = 50) -> List[TrackingAlert]:
    """
    Get all unread tracking alerts.
    
    Args:
        limit: Maximum number of alerts to return.
        
    Returns:
        List of unread TrackingAlert records.
    """
    async with async_session_factory() as session:
        stmt = select(TrackingAlert).where(
            TrackingAlert.is_read == False
        ).order_by(
            TrackingAlert.created_at.desc()
        ).limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def mark_alert_read(alert_id: int) -> bool:
    """
    Mark an alert as read.
    
    Args:
        alert_id: The ID of the alert.
        
    Returns:
        True if successful, False otherwise.
    """
    async with async_session_factory() as session:
        stmt = select(TrackingAlert).where(TrackingAlert.id == alert_id)
        result = await session.execute(stmt)
        alert = result.scalar_one_or_none()
        
        if not alert:
            return False
        
        alert.is_read = True
        await session.commit()
        return True


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Target Tracker - Monitor investment targets"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update tracked companies")
    update_parser.add_argument(
        "--company-id", 
        type=int, 
        nargs="+",
        help="Specific tracked company IDs to update"
    )
    update_parser.add_argument(
        "--force", 
        action="store_true",
        help="Force check all companies regardless of schedule"
    )
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add company to tracking")
    add_parser.add_argument(
        "company_id", 
        type=int,
        help="Company ID from universe database"
    )
    add_parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        default="medium",
        help="Tracking priority"
    )
    add_parser.add_argument(
        "--tags",
        nargs="+",
        help="Tags for the company"
    )
    add_parser.add_argument(
        "--notes",
        type=str,
        help="Initial notes"
    )
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove company from tracking")
    remove_parser.add_argument(
        "tracked_id",
        type=int,
        help="Tracked company ID"
    )
    remove_parser.add_argument(
        "--hard-delete",
        action="store_true",
        help="Permanently delete instead of marking closed"
    )
    
    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="View unread alerts")
    alerts_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of alerts to show"
    )
    
    args = parser.parse_args()
    
    if args.command == "update":
        asyncio.run(update_tracked_companies(
            company_ids=args.company_id,
            force_check=args.force
        ))
    elif args.command == "add":
        asyncio.run(add_company_to_tracking(
            company_id=args.company_id,
            priority=args.priority,
            tags=args.tags,
            notes=args.notes
        ))
    elif args.command == "remove":
        asyncio.run(remove_company_from_tracking(
            tracked_id=args.tracked_id,
            hard_delete=args.hard_delete
        ))
    elif args.command == "alerts":
        alerts = asyncio.run(get_unread_alerts(limit=args.limit))
        if alerts:
            print(f"\n--- {len(alerts)} UNREAD ALERTS ---")
            for alert in alerts:
                print(f"[{alert.id}] {alert.alert_type}: {alert.message[:80]}...")
        else:
            print("\nNo unread alerts.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

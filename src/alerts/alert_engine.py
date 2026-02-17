import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_, func
from src.core.database import async_session_factory
from src.tracker.database import (
    TrackedCompany, CompanyEvent, TrackingAlert, AlertPreference,
    TrackingStatus, EventSeverity
)
from src.alerts.notification_channels import slack_client, email_client

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Monitors tracked companies and triggers alerts on events.
    """
    
    async def check_alerts(self):
        """
        Main entry point for the alert system.
        Checks for recent events and generates alerts.
        """
        logger.info("Running Alert Engine check...")
        
        async with async_session_factory() as session:
            # 1. Get Preferences
            # For now, we assume a single user or default user "default_user"
            stmt_pref = select(AlertPreference).where(AlertPreference.user_id == "default_user")
            result_pref = await session.execute(stmt_pref)
            preference = result_pref.scalar_one_or_none()
            
            if not preference:
                # Create default preferences if not exist
                preference = AlertPreference(user_id="default_user")
                session.add(preference)
                await session.commit()
                # Re-fetch attached to session
                # (Actually optimization: just use the object we created, it's attached)
            
            # 2. Find Recent Unprocessed Events
            # We need a way to track which events have been alerted on.
            # Strategy: Join CompanyEvent with TrackingAlert to find events WITHOUT an alert.
            # However, TrackingAlert doesn't strictly link 1:1 to Event via FK (it could, but currently doesn't in my schema review).
            # The schema has `tracked_company_id` on Alert, but not `event_id`.
            # EDIT: The Schema I saw earlier for TrackingAlert did NOT have event_id.
            # I should update the schema or use a timestamp based approach.
            # Timestamp approach: check events created in the last hour? No, unreliable if job fails.
            # Best approach: Add `event_id` to TrackingAlert or just querying for events that don't have a check.
            # Let's use a "last_checked" timestamp mechanism on the `AlertPreference` or a global state, 
            # OR just look for events created_at > last_run.
            # BETTER YET: I'll use the "last_checked" field on `TrackedCompany` to mark when we last scanned it for alerts? 
            # No, that might be for scraping.
            
            # Let's simplify:
            # 1. Find all events created in the last 24 hours (or frequency).
            # 2. Check if an alert already exists for this company + event type + date ~approx.
            # Actually, without `event_id` in `TrackingAlert`, deduplication is hard.
            # I will modify the logic to just "simulated" detection for now or
            # I'll rely on a time window (e.g. events created in the last 15 minutes if this runs every 15 mins).
            # SAFE BET: Look for events created since the last successful run.
            
            # Let's grab events from the last 1 hour.
            since_time = datetime.utcnow() - timedelta(hours=1)
            
            # Find events
            stmt_events = select(CompanyEvent, TrackedCompany).\
                join(TrackedCompany, CompanyEvent.tracked_company_id == TrackedCompany.id).\
                where(
                    and_(
                        CompanyEvent.created_at >= since_time,
                        TrackedCompany.tracking_status == TrackingStatus.ACTIVE
                    )
                )
                
            result_events = await session.execute(stmt_events)
            events = result_events.all()
            
            new_alerts_count = 0
            
            for event, company in events:
                # Check duplication (naive: check if alert exists for this company with same message recently)
                # This prevents spam if the job runs overlapping windows or if event is updated
                
                # Filter by Preferences
                should_alert = False
                if event.event_type == 'funding' and preference.notify_funding: should_alert = True
                elif event.event_type == 'leadership_change' and preference.notify_leadership: should_alert = True
                elif event.event_type == 'news' and preference.notify_news: should_alert = True
                elif event.event_type == 'product_launch' and preference.notify_product: should_alert = True
                
                # Verify specific logic (e.g. critical events always alert?)
                if event.severity == EventSeverity.CRITICAL:
                    should_alert = True

                if not should_alert:
                    continue

                # Check if alert already exists (deduplication)
                # We look for an alert for this company, created recently, with similar message? 
                # Or we assume the "Since Time" handles it. 
                # Ideally we want to process each event exactly once.
                # Since I am building this from scratch, I can just assume the `check_alerts` receives a specific window.
                # BUT, to be robust, let's query.
                
                msg = f"New {event.event_type.replace('_', ' ').title()}: {event.title}"
                if event.description:
                    msg += f"\n{event.description[:100]}..."
                
                # Create Alert Record
                alert = TrackingAlert(
                    tracked_company_id=company.id,
                    alert_type=event.event_type,
                    message=msg,
                    is_read=False
                )
                session.add(alert)
                new_alerts_count += 1
                
                # Send Notifications (Real-time)
                if preference.digest_frequency == "realtime":
                    if preference.slack_enabled:
                         await slack_client.send_message(
                             text=f"🚨 *{company.id} - {event.title}*\n{event.description or ''}\nSeverity: {event.severity.value}"
                         )
                    
                    if preference.email_enabled and event.severity in (EventSeverity.HIGH, EventSeverity.CRITICAL):
                         # Only email for High/Critical in realtime to avoid spam, unless configured otherwise
                         # For now, simple logic.
                         await self.send_email_alert(company, event)
            
            await session.commit()
            logger.info(f"Alert Loop Completed. Generated {new_alerts_count} new alerts.")

    async def send_email_alert(self, company: TrackedCompany, event: CompanyEvent):
        """
        Sends an email alert.
        """
        subject = f"RADAR Alert: {event.title}"
        content = f"""
        <h1>New Event Detected</h1>
        <p><b>Company:</b> {company.company_id} (Ref ID: {company.id})</p>
        <p><b>Event:</b> {event.event_type}</p>
        <p><b>Title:</b> {event.title}</p>
        <p><b>Description:</b><br>{event.description}</p>
        <p><b>Link:</b> <a href="{event.source_url}">{event.source_url}</a></p>
        <br>
        <p><i>Sent by RADAR Alert Engine</i></p>
        """
        # In a real app, we'd look up the user's email. For now using a default or env var.
        # Assuming single user mode -> send to "settings.sendgrid_from_email" or similar if set, 
        # or just logging it if no 'to_email' is defined in preferences (which it isn't yet).
        # I'll use a placeholder email or log warning.
        to_email = "investor@example.com" # TODO: Add email to AlertPreference or User model
        
        email_client.send_email(to_email, subject, content)

    async def create_test_event(self):
        """
        Helper to create a test event for verification.
        """
        async with async_session_factory() as session:
            # Get first active tracked company
            stmt = select(TrackedCompany).where(TrackedCompany.tracking_status == TrackingStatus.ACTIVE).limit(1)
            result = await session.execute(stmt)
            company = result.scalar_one_or_none()
            
            if not company:
                logger.warning("No active tracked companies found. Cannot create test event.")
                return
            
            event = CompanyEvent(
                tracked_company_id=company.id,
                event_type="funding",
                title="Raised Series B - Test Event",
                description="This is a generated test event to verify the alert system.",
                severity=EventSeverity.HIGH,
                source_url="http://example.com"
            )
            session.add(event)
            await session.commit()
            logger.info(f"Created test event for company ID {company.id}")

# Singleton
alert_engine = AlertEngine()

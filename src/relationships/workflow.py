"""
Workflow functions for Relationship Manager module.

Provides scheduled/triggered workflows for:
- Syncing email interactions (Gmail API stub)
- Updating relationship scores
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.relationships.database import Contact, Interaction, InteractionType, InteractionOutcome
from src.relationships.analyzer import RelationshipAnalyzer

# Try to import core database, fallback for standalone testing
try:
    from src.core.database import async_session_factory
except ImportError:
    async_session_factory = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def sync_email_interactions(
    session: Optional[AsyncSession] = None
) -> dict:
    """
    Sync email interactions from Gmail API.
    
    If Gmail API is configured:
    1. Fetch sent emails to known contacts
    2. Create Interaction records
    3. Update last_contact_date on contacts
    
    Note: This is a stub implementation. Full Gmail integration requires:
    - Gmail API credentials
    - OAuth2 authentication flow
    - google-api-python-client package
    
    Returns:
        Summary of synced interactions
    """
    should_close_session = False
    
    if session is None:
        if async_session_factory is None:
            logger.error("Database session factory not available")
            return {"status": "error", "message": "Database not configured"}
        session = async_session_factory()
        should_close_session = True
    
    try:
        logger.info("Starting email sync workflow...")
        
        # Check if Gmail API is configured
        gmail_configured = _check_gmail_config()
        
        if not gmail_configured:
            logger.info("Gmail API not configured. Skipping email sync.")
            return {
                "status": "skipped",
                "message": "Gmail API not configured. Set GMAIL_CREDENTIALS_PATH to enable.",
                "synced_count": 0
            }
        
        # Get all contacts with email addresses
        stmt = select(Contact).where(Contact.email.isnot(None))
        result = await session.execute(stmt)
        contacts = result.scalars().all()
        
        if not contacts:
            return {
                "status": "success",
                "message": "No contacts with email addresses found",
                "synced_count": 0
            }
        
        # Build email -> contact mapping
        email_to_contact = {c.email.lower(): c for c in contacts if c.email}
        
        # Fetch emails from Gmail (stub - would use Gmail API)
        emails = await _fetch_gmail_emails(list(email_to_contact.keys()))
        
        synced_count = 0
        for email_data in emails:
            contact = email_to_contact.get(email_data["to_email"].lower())
            if not contact:
                continue
            
            # Create interaction record
            interaction = Interaction(
                contact_id=contact.id,
                interaction_type=InteractionType.EMAIL.value,
                interaction_date=email_data["date"],
                subject=email_data["subject"],
                notes=f"Synced from Gmail. Message ID: {email_data['message_id']}",
                outcome=None  # User can update later
            )
            session.add(interaction)
            
            # Update last contact date
            if contact.last_contact_date is None or email_data["date"] > contact.last_contact_date:
                contact.last_contact_date = email_data["date"]
            
            synced_count += 1
        
        await session.commit()
        
        logger.info(f"Email sync complete. Synced {synced_count} interactions.")
        
        return {
            "status": "success",
            "synced_count": synced_count,
            "contacts_checked": len(contacts)
        }
        
    finally:
        if should_close_session:
            await session.close()


def _check_gmail_config() -> bool:
    """Check if Gmail API credentials are configured."""
    import os
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
    return credentials_path is not None and os.path.exists(credentials_path) if credentials_path else False


async def _fetch_gmail_emails(contact_emails: list) -> list:
    """
    Fetch sent emails to specified contacts from Gmail API.
    
    This is a stub implementation. Full implementation would:
    1. Authenticate with Gmail API using OAuth2
    2. Query sent messages to contact emails
    3. Parse message metadata
    
    Returns empty list for now.
    """
    # TODO: Implement Gmail API integration
    # Example code for reference:
    #
    # from google.oauth2.credentials import Credentials
    # from googleapiclient.discovery import build
    #
    # creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # service = build('gmail', 'v1', credentials=creds)
    #
    # for email in contact_emails:
    #     query = f'to:{email} in:sent'
    #     results = service.users().messages().list(userId='me', q=query).execute()
    #     messages = results.get('messages', [])
    #     for msg in messages:
    #         # Parse message and yield
    #         pass
    
    return []


async def update_relationship_scores(
    session: Optional[AsyncSession] = None
) -> dict:
    """
    Recalculate relationship_strength scores for all contacts.
    
    This workflow should be run periodically (e.g., daily) to:
    1. Update relationship_score based on interaction history
    2. Adjust relationship_strength category (cold/warm/hot)
    3. Identify contacts needing follow-up
    
    Returns:
        Summary of updates made
    """
    should_close_session = False
    
    if session is None:
        if async_session_factory is None:
            logger.error("Database session factory not available")
            return {"status": "error", "message": "Database not configured"}
        session = async_session_factory()
        should_close_session = True
    
    try:
        logger.info("Starting relationship score update workflow...")
        
        analyzer = RelationshipAnalyzer(session)
        
        # Update all scores
        updated_count = await analyzer.update_all_relationship_scores()
        
        # Get follow-up suggestions
        follow_ups = await analyzer.suggest_follow_ups(days_threshold=90, min_strength=50)
        
        # Get network stats
        stats = await analyzer.get_network_stats()
        
        logger.info(f"Score update complete. Updated {updated_count} contacts.")
        logger.info(f"Found {len(follow_ups)} contacts needing follow-up.")
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "follow_up_count": len(follow_ups),
            "network_stats": stats
        }
        
    finally:
        if should_close_session:
            await session.close()


async def run_daily_relationship_workflow(
    session: Optional[AsyncSession] = None
) -> dict:
    """
    Run all daily relationship management workflows.
    
    Order:
    1. Sync email interactions (if Gmail configured)
    2. Update relationship scores
    """
    logger.info("Starting daily relationship workflow...")
    
    results = {}
    
    # 1. Sync emails
    email_result = await sync_email_interactions(session)
    results["email_sync"] = email_result
    
    # 2. Update scores
    score_result = await update_relationship_scores(session)
    results["score_update"] = score_result
    
    logger.info("Daily relationship workflow complete.")
    
    return results


if __name__ == "__main__":
    # Standalone test run
    print("Running relationship workflow...")
    asyncio.run(run_daily_relationship_workflow())

"""Public service interface for the Relationships module.

Other modules should import from here, not from relationships.database directly.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.relationships.database import Contact


async def get_contacts(
    limit: int = 50, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get contacts. Returns list of dicts."""
    async with get_async_db() as session:
        stmt = select(Contact).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return [c.to_dict() for c in result.scalars().all()]


async def get_contact_by_id(contact_id: int) -> Optional[Dict[str, Any]]:
    """Get a single contact by ID. Returns dict or None."""
    async with get_async_db() as session:
        stmt = select(Contact).where(
            Contact.id == contact_id
        )
        result = await session.execute(stmt)
        contact = result.scalar_one_or_none()
        return contact.to_dict() if contact else None

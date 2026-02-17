"""Relationships router — CRM, contacts, interactions, network graph, warm intros."""

import logging
from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.schemas import StandardResponse, PaginatedResponse
from fastapi import Depends
from src.relationships.database import (
    Contact, Interaction, NetworkConnection,
    RelationshipStrength,
)
from src.relationships.analyzer import RelationshipAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/relationships",
    tags=["Relationships"]
)


# --- Schemas ---

class ContactCreate(BaseModel):
    """Schema for creating a new contact."""
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: str = "founder"
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class InteractionCreate(BaseModel):
    """Schema for logging a new interaction."""
    contact_id: int
    interaction_type: str = "email"
    interaction_date: Optional[str] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None


class ConnectionCreate(BaseModel):
    """Schema for creating a network connection."""
    contact_a_id: int
    contact_b_id: int
    connection_type: str = "colleague"
    strength: int = 50
    notes: Optional[str] = None
    discovered_via: str = "manual"


# --- Endpoints ---

@router.post("/contact", response_model=StandardResponse[dict])
async def create_contact(
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_db)
):
    """Add a new contact to the CRM."""
    if contact_data.email:
        stmt = select(Contact).where(Contact.email == contact_data.email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Contact with email {contact_data.email} already exists"
            )

    contact = Contact(
        full_name=contact_data.full_name,
        email=contact_data.email,
        phone=contact_data.phone,
        linkedin_url=contact_data.linkedin_url,
        contact_type=contact_data.contact_type,
        company_name=contact_data.company_name,
        job_title=contact_data.job_title,
        location=contact_data.location,
        notes=contact_data.notes,
        tags=contact_data.tags,
        relationship_strength=RelationshipStrength.COLD.value,
        relationship_score=0
    )

    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    return StandardResponse(data={
        "contact_id": contact.id,
        "message": f"Contact '{contact.full_name}' created successfully"
    })


@router.get("/contacts", response_model=PaginatedResponse[dict])
async def list_contacts(
    limit: int = 100,
    offset: int = 0,
    contact_type: Optional[str] = None,
    strength: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """List contacts with optional filters."""
    stmt = select(Contact).order_by(desc(Contact.relationship_score))

    if contact_type:
        stmt = stmt.where(Contact.contact_type == contact_type)
    if strength:
        stmt = stmt.where(Contact.relationship_strength == strength)
    if company:
        stmt = stmt.where(Contact.company_name.ilike(f"%{company}%"))
    if search:
        stmt = stmt.where(
            (Contact.full_name.ilike(f"%{search}%")) |
            (Contact.company_name.ilike(f"%{search}%")) |
            (Contact.email.ilike(f"%{search}%"))
        )

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    contacts = result.scalars().all()

    count_stmt = select(func.count(Contact.id))
    if contact_type:
        count_stmt = count_stmt.where(Contact.contact_type == contact_type)
    if strength:
        count_stmt = count_stmt.where(Contact.relationship_strength == strength)

    total = await session.scalar(count_stmt)

    return PaginatedResponse(
        data=[
            {
                "id": c.id,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "linkedin_url": c.linkedin_url,
                "contact_type": c.contact_type,
                "company_name": c.company_name,
                "job_title": c.job_title,
                "location": c.location,
                "relationship_strength": c.relationship_strength,
                "relationship_score": c.relationship_score,
                "tags": c.tags,
                "last_contact_date": c.last_contact_date.isoformat() if c.last_contact_date else None,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in contacts
        ],
        total=total or 0,
        limit=limit,
        offset=offset
    )


@router.get("/contact/{contact_id}", response_model=StandardResponse[dict])
async def get_contact_detail(
    contact_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get detailed contact view with interaction history."""
    contact = await session.get(Contact, contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    interactions_stmt = select(Interaction).where(
        Interaction.contact_id == contact_id
    ).order_by(desc(Interaction.interaction_date)).limit(50)

    result = await session.execute(interactions_stmt)
    interactions = result.scalars().all()

    connections_stmt = select(NetworkConnection).where(
        (NetworkConnection.contact_a_id == contact_id) |
        (NetworkConnection.contact_b_id == contact_id)
    )
    result = await session.execute(connections_stmt)
    connections = result.scalars().all()

    connected_ids = set()
    for conn in connections:
        connected_ids.add(conn.get_other_contact(contact_id))

    connected_contacts = {}
    if connected_ids:
        stmt = select(Contact).where(Contact.id.in_(connected_ids))
        result = await session.execute(stmt)
        for c in result.scalars():
            connected_contacts[c.id] = c

    return StandardResponse(data={
        "contact": {
            "id": contact.id,
            "full_name": contact.full_name,
            "email": contact.email,
            "phone": contact.phone,
            "linkedin_url": contact.linkedin_url,
            "contact_type": contact.contact_type,
            "company_name": contact.company_name,
            "job_title": contact.job_title,
            "location": contact.location,
            "notes": contact.notes,
            "relationship_strength": contact.relationship_strength,
            "relationship_score": contact.relationship_score,
            "tags": contact.tags,
            "last_contact_date": contact.last_contact_date.isoformat() if contact.last_contact_date else None,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "enrichment_data": contact.enrichment_data,
            "enriched_at": contact.enriched_at.isoformat() if contact.enriched_at else None
        },
        "interactions": [
            {
                "id": i.id,
                "interaction_type": i.interaction_type,
                "interaction_date": i.interaction_date.isoformat() if i.interaction_date else None,
                "subject": i.subject,
                "notes": i.notes,
                "outcome": i.outcome,
                "next_action": i.next_action,
                "next_action_date": i.next_action_date.isoformat() if i.next_action_date else None
            }
            for i in interactions
        ],
        "connections": [
            {
                "id": conn.id,
                "other_contact_id": conn.get_other_contact(contact_id),
                "other_contact_name": (
                    connected_contacts[conn.get_other_contact(contact_id)].full_name
                    if conn.get_other_contact(contact_id) in connected_contacts
                    else "Unknown"
                ),
                "other_contact_company": (
                    connected_contacts[conn.get_other_contact(contact_id)].company_name
                    if conn.get_other_contact(contact_id) in connected_contacts
                    else None
                ),
                "connection_type": conn.connection_type,
                "strength": conn.strength,
                "discovered_via": conn.discovered_via
            }
            for conn in connections
        ],
        "stats": {
            "total_interactions": len(interactions),
            "total_connections": len(connections)
        }
    })


@router.put("/contact/{contact_id}", response_model=StandardResponse[dict])
async def update_contact(
    contact_id: int, 
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_db)
):
    """Update an existing contact."""
    contact = await session.get(Contact, contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.full_name = contact_data.full_name
    contact.email = contact_data.email
    contact.phone = contact_data.phone
    contact.linkedin_url = contact_data.linkedin_url
    contact.contact_type = contact_data.contact_type
    contact.company_name = contact_data.company_name
    contact.job_title = contact_data.job_title
    contact.location = contact_data.location
    contact.notes = contact_data.notes
    contact.tags = contact_data.tags

    await session.commit()

    return StandardResponse(data={"message": "Contact updated"})


@router.delete("/contact/{contact_id}", response_model=StandardResponse[dict])
async def delete_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a contact and all related data."""
    contact = await session.get(Contact, contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await session.delete(contact)
    await session.commit()

    return StandardResponse(data={"message": "Contact deleted"})


@router.post("/interaction", response_model=StandardResponse[dict])
async def log_interaction(
    interaction_data: InteractionCreate,
    session: AsyncSession = Depends(get_db)
):
    """Log a new interaction with a contact."""
    contact = await session.get(Contact, interaction_data.contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    interaction_date = date_type.today()
    if interaction_data.interaction_date:
        interaction_date = date_type.fromisoformat(interaction_data.interaction_date)

    next_action_date = None
    if interaction_data.next_action_date:
        next_action_date = date_type.fromisoformat(interaction_data.next_action_date)

    interaction = Interaction(
        contact_id=interaction_data.contact_id,
        interaction_type=interaction_data.interaction_type,
        interaction_date=interaction_date,
        subject=interaction_data.subject,
        notes=interaction_data.notes,
        outcome=interaction_data.outcome,
        next_action=interaction_data.next_action,
        next_action_date=next_action_date
    )

    session.add(interaction)

    if contact.last_contact_date is None or interaction_date > contact.last_contact_date:
        contact.last_contact_date = interaction_date

    await session.commit()

    analyzer = RelationshipAnalyzer(session)
    new_score = await analyzer.calculate_relationship_strength(contact.id)
    contact.relationship_score = new_score

    if new_score >= 70:
        contact.relationship_strength = RelationshipStrength.HOT.value
    elif new_score >= 40:
        contact.relationship_strength = RelationshipStrength.WARM.value
    else:
        contact.relationship_strength = RelationshipStrength.COLD.value

    await session.commit()

    return StandardResponse(data={
        "interaction_id": interaction.id,
        "new_relationship_score": new_score
    })


@router.post("/connection", response_model=StandardResponse[dict])
async def create_connection(
    connection_data: ConnectionCreate,
    session: AsyncSession = Depends(get_db)
):
    """Create a network connection between two contacts."""
    contact_a = await session.get(Contact, connection_data.contact_a_id)
    contact_b = await session.get(Contact, connection_data.contact_b_id)

    if not contact_a or not contact_b:
        raise HTTPException(status_code=404, detail="One or both contacts not found")

    if connection_data.contact_a_id == connection_data.contact_b_id:
        raise HTTPException(status_code=400, detail="Cannot connect a contact to themselves")

    stmt = select(NetworkConnection).where(
        ((NetworkConnection.contact_a_id == connection_data.contact_a_id) &
            (NetworkConnection.contact_b_id == connection_data.contact_b_id)) |
        ((NetworkConnection.contact_a_id == connection_data.contact_b_id) &
            (NetworkConnection.contact_b_id == connection_data.contact_a_id))
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Connection already exists")

    connection = NetworkConnection(
        contact_a_id=connection_data.contact_a_id,
        contact_b_id=connection_data.contact_b_id,
        connection_type=connection_data.connection_type,
        strength=connection_data.strength,
        notes=connection_data.notes,
        discovered_via=connection_data.discovered_via
    )

    session.add(connection)
    await session.commit()

    return StandardResponse(data={
        "connection_id": connection.id,
        "message": f"Connected {contact_a.full_name} with {contact_b.full_name}"
    })


@router.get("/warm-intro/{target_id}", response_model=StandardResponse[dict])
async def find_warm_intro(
    target_id: int, 
    min_strength: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """Find warm introduction path to a target contact."""
    target = await session.get(Contact, target_id)

    if not target:
        raise HTTPException(status_code=404, detail="Target contact not found")

    analyzer = RelationshipAnalyzer(session)
    path_result = await analyzer.find_warm_intro_path(target_id, min_strength)

    return StandardResponse(data={
        "target": {
            "id": target.id,
            "full_name": target.full_name,
            "company": target.company_name,
            "job_title": target.job_title
        },
        **path_result
    })


@router.get("/follow-ups", response_model=StandardResponse[dict])
async def get_follow_ups(
    days_threshold: int = 90,
    min_strength: int = 50,
    limit: int = 20,
    session: AsyncSession = Depends(get_db)
):
    """Get contacts that need follow-up."""
    analyzer = RelationshipAnalyzer(session)
    follow_ups = await analyzer.suggest_follow_ups(
        days_threshold=days_threshold,
        min_strength=min_strength,
        limit=limit
    )

    return StandardResponse(data={
        "follow_ups": follow_ups,
        "count": len(follow_ups),
        "threshold_days": days_threshold
    })


@router.get("/network-map", response_model=StandardResponse[dict])
async def get_network_map(session: AsyncSession = Depends(get_db)):
    """Get all contacts and connections for network visualization."""
    contacts_stmt = select(Contact)
    result = await session.execute(contacts_stmt)
    contacts = result.scalars().all()

    connections_stmt = select(NetworkConnection)
    result = await session.execute(connections_stmt)
    connections = result.scalars().all()

    nodes = [
        {
            "id": c.id,
            "name": c.full_name,
            "company": c.company_name,
            "type": c.contact_type,
            "strength": c.relationship_strength,
            "score": c.relationship_score,
            "size": max(5, c.relationship_score / 5)
        }
        for c in contacts
    ]

    edges = [
        {
            "id": conn.id,
            "source": conn.contact_a_id,
            "target": conn.contact_b_id,
            "type": conn.connection_type,
            "strength": conn.strength,
            "width": max(1, conn.strength / 20)
        }
        for conn in connections
    ]

    analyzer = RelationshipAnalyzer(session)
    stats = await analyzer.get_network_stats()

    return StandardResponse(data={
        "nodes": nodes,
        "edges": edges,
        "stats": stats
    })


@router.get("/stats", response_model=StandardResponse[dict])
async def get_relationship_stats(session: AsyncSession = Depends(get_db)):
    """Get relationship network statistics."""
    analyzer = RelationshipAnalyzer(session)
    stats = await analyzer.get_network_stats()

    type_stmt = select(
        Contact.contact_type,
        func.count(Contact.id)
    ).group_by(Contact.contact_type)
    result = await session.execute(type_stmt)
    type_breakdown = {row[0]: row[1] for row in result.all()}

    strength_stmt = select(
        Contact.relationship_strength,
        func.count(Contact.id)
    ).group_by(Contact.relationship_strength)
    result = await session.execute(strength_stmt)
    strength_breakdown = {row[0]: row[1] for row in result.all()}

    return StandardResponse(data={
        **stats,
        "by_type": type_breakdown,
        "by_strength": strength_breakdown
    })

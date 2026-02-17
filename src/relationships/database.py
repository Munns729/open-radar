"""
Database models for Module 5 - Relationship Manager (CRM).
"""
from datetime import datetime, date
from typing import List, Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, 
    ForeignKey, Text, JSON, Float, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from src.core.database import Base


class ContactType(str, PyEnum):
    """Type of contact in the CRM."""
    FOUNDER = "founder"
    CEO = "ceo"
    CFO = "cfo"
    ADVISOR = "advisor"
    BANKER = "banker"
    LAWYER = "lawyer"
    INVESTOR = "investor"


class RelationshipStrength(str, PyEnum):
    """Qualitative relationship strength."""
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class InteractionType(str, PyEnum):
    """Type of interaction with a contact."""
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    LINKEDIN_MESSAGE = "linkedin_message"


class InteractionOutcome(str, PyEnum):
    """Outcome of an interaction."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    NO_RESPONSE = "no_response"


class ConnectionType(str, PyEnum):
    """Type of connection between two contacts."""
    COLLEAGUE = "colleague"
    FOUNDER_INVESTOR = "founder_investor"
    ADVISOR = "advisor"
    INTRODUCER = "introducer"


class DiscoveredVia(str, PyEnum):
    """How the connection was discovered."""
    LINKEDIN = "linkedin"
    MANUAL = "manual"
    EMAIL = "email"


class Contact(Base):
    """
    CRM Contact - Founder, investor, advisor, or other professional.
    """
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Professional info
    contact_type: Mapped[str] = mapped_column(String(50), default=ContactType.FOUNDER.value)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationship tracking
    relationship_strength: Mapped[str] = mapped_column(String(20), default=RelationshipStrength.COLD.value)
    relationship_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 calculated score
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_contact_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Enrichment data from LinkedIn
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    interactions: Mapped[List["Interaction"]] = relationship(
        "Interaction", 
        back_populates="contact",
        cascade="all, delete-orphan"
    )
    
    # Network connections (as either party)
    connections_as_a: Mapped[List["NetworkConnection"]] = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.contact_a_id",
        back_populates="contact_a",
        cascade="all, delete-orphan"
    )
    connections_as_b: Mapped[List["NetworkConnection"]] = relationship(
        "NetworkConnection",
        foreign_keys="NetworkConnection.contact_b_id",
        back_populates="contact_b",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_contact_type', 'contact_type'),
        Index('idx_contact_strength', 'relationship_strength'),
        Index('idx_contact_company', 'company_name'),
    )

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.full_name}', company='{self.company_name}')>"
    
    @property
    def all_connections(self) -> List["NetworkConnection"]:
        """Get all network connections for this contact."""
        return self.connections_as_a + self.connections_as_b


class Interaction(Base):
    """
    Record of an interaction with a contact.
    """
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    
    interaction_type: Mapped[str] = mapped_column(String(50), default=InteractionType.EMAIL.value)
    interaction_date: Mapped[date] = mapped_column(Date, default=date.today)
    
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    outcome: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Follow-up tracking
    next_action: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    next_action_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="interactions")

    __table_args__ = (
        Index('idx_interaction_date', 'interaction_date'),
        Index('idx_interaction_type', 'interaction_type'),
    )

    def __repr__(self):
        return f"<Interaction(id={self.id}, contact_id={self.contact_id}, type='{self.interaction_type}')>"


class NetworkConnection(Base):
    """
    Connection between two contacts in the network graph.
    Represents a professional relationship that can be used for warm intros.
    """
    __tablename__ = "network_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # The two contacts (order doesn't matter semantically, but stored consistently)
    contact_a_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    contact_b_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    
    connection_type: Mapped[str] = mapped_column(String(50), default=ConnectionType.COLLEAGUE.value)
    strength: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discovered_via: Mapped[str] = mapped_column(String(20), default=DiscoveredVia.MANUAL.value)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    contact_a: Mapped["Contact"] = relationship(
        "Contact", 
        foreign_keys=[contact_a_id],
        back_populates="connections_as_a"
    )
    contact_b: Mapped["Contact"] = relationship(
        "Contact", 
        foreign_keys=[contact_b_id],
        back_populates="connections_as_b"
    )

    __table_args__ = (
        Index('idx_network_contacts', 'contact_a_id', 'contact_b_id'),
        CheckConstraint('contact_a_id != contact_b_id', name='no_self_connection'),
        CheckConstraint('strength >= 0 AND strength <= 100', name='strength_range'),
    )

    def __repr__(self):
        return f"<NetworkConnection(id={self.id}, a={self.contact_a_id}, b={self.contact_b_id}, strength={self.strength})>"
    
    def get_other_contact(self, contact_id: int) -> int:
        """Given one contact ID, return the other contact in the connection."""
        if self.contact_a_id == contact_id:
            return self.contact_b_id
        return self.contact_a_id

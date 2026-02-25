"""
Database models for Module 3 - Target Tracker.

Tracks companies of interest for investment monitoring, including
events, notes, and alerts.
"""
from datetime import datetime, date
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, 
    ForeignKey, Text, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


# Enums for tracking status and priority
class TrackingStatus(str, PyEnum):
    """Status of company tracking"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class TrackingPriority(str, PyEnum):
    """Priority level for tracked company"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventType(str, PyEnum):
    """Types of company events"""
    FUNDING = "funding"
    LEADERSHIP_CHANGE = "leadership_change"
    PRODUCT_LAUNCH = "product_launch"
    NEWS = "news"
    FINANCIAL_UPDATE = "financial_update"


class EventSeverity(str, PyEnum):
    """Severity level of events"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NoteType(str, PyEnum):
    """Types of notes"""
    CALL = "call"
    MEETING = "meeting"
    RESEARCH = "research"
    OUTREACH = "outreach"


class TrackedCompany(Base):
    """
    Main tracking record for companies of interest.
    Links to the main CompanyModel in the universe module.
    """
    __tablename__ = "tracked_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # FK to companies table
    
    tracking_status: Mapped[str] = mapped_column(
        String(20), 
        default=TrackingStatus.ACTIVE.value,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(10), 
        default=TrackingPriority.MEDIUM.value,
        index=True
    )
    
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    added_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_check_due: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    events: Mapped[List["CompanyEvent"]] = relationship(
        "CompanyEvent", 
        back_populates="tracked_company",
        cascade="all, delete-orphan"
    )
    company_notes: Mapped[List["CompanyNote"]] = relationship(
        "CompanyNote", 
        back_populates="tracked_company",
        cascade="all, delete-orphan"
    )
    alerts: Mapped[List["TrackingAlert"]] = relationship(
        "TrackingAlert", 
        back_populates="tracked_company",
        cascade="all, delete-orphan"
    )
    documents: Mapped[List["CompanyDocument"]] = relationship(
        "CompanyDocument",
        back_populates="tracked_company",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_tracked_status_priority', 'tracking_status', 'priority'),
    )

    def __repr__(self):
        return f"<TrackedCompany(id={self.id}, company_id={self.company_id}, status='{self.tracking_status}')>"


class CompanyEvent(Base):
    """
    Timeline of significant events for a tracked company.
    Captures funding rounds, leadership changes, product launches, etc.
    """
    __tablename__ = "company_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_company_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_companies.id"), 
        nullable=False,
        index=True
    )
    
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    severity: Mapped[str] = mapped_column(
        String(20), 
        default=EventSeverity.MEDIUM.value,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    tracked_company: Mapped["TrackedCompany"] = relationship(
        "TrackedCompany", 
        back_populates="events"
    )

    __table_args__ = (
        Index('idx_event_date_severity', 'event_date', 'severity'),
    )

    def __repr__(self):
        return f"<CompanyEvent(id={self.id}, type='{self.event_type}', title='{self.title[:30]}...')>"


class CompanyNote(Base):
    """
    User notes on tracked companies.
    Captures calls, meetings, research notes, outreach records.
    """
    __tablename__ = "company_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_company_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_companies.id"), 
        nullable=False,
        index=True
    )
    
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note_type: Mapped[str] = mapped_column(
        String(20), 
        default=NoteType.RESEARCH.value,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Relationships
    tracked_company: Mapped["TrackedCompany"] = relationship(
        "TrackedCompany", 
        back_populates="company_notes"
    )

    def __repr__(self):
        return f"<CompanyNote(id={self.id}, type='{self.note_type}')>"


class TrackingAlert(Base):
    """
    Alerts generated for tracked companies.
    Created when significant events are detected.
    """
    __tablename__ = "tracking_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_company_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_companies.id"), 
        nullable=False,
        index=True
    )
    
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    risk_level: Mapped[str] = mapped_column(String(20), default="low", index=True)  # low | elevated | high
    context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Relationships
    tracked_company: Mapped["TrackedCompany"] = relationship(
        "TrackedCompany", 
        back_populates="alerts"
    )

    __table_args__ = (
        Index('idx_alert_unread', 'is_read', 'created_at'),
    )

    def __repr__(self):
        return f"<TrackingAlert(id={self.id}, type='{self.alert_type}', read={self.is_read})>"


class CompanyDocument(Base):
    """
    Documents uploaded for a tracked company.
    Used for RAG (Retrieval Augmented Generation) by the Agent.
    """
    __tablename__ = "company_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_company_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_companies.id"), 
        nullable=False,
        index=True
    )
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, txt, etc
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Content for RAG
    
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    tracked_company: Mapped["TrackedCompany"] = relationship(
        "TrackedCompany", 
        back_populates="documents"
    )

    def __repr__(self):
        return f"<CompanyDocument(id={self.id}, filename='{self.filename}')>"


class AlertPreference(Base):
    """
    User preferences for alerts.
    """
    __tablename__ = "alert_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), default="default_user", index=True) # Supporting multi-user later
    
    # Enable/Disable channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Event Types to monitor
    notify_funding: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_leadership: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_news: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_product: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Frequency
    digest_frequency: Mapped[str] = mapped_column(String(20), default="realtime") # realtime, daily, weekly
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AlertPreference(user='{self.user_id}', email={self.email_enabled}, slack={self.slack_enabled})>"

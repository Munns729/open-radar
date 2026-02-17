"""Database models and operations for Competitive Radar"""
import logging
from datetime import datetime
from typing import List, Optional, Type
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.core.config import settings

logger = logging.getLogger(__name__)

from src.core.database import Base

class VCFirmModel(Base):
    """VC Firm database model"""
    __tablename__ = 'vc_firms'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    linkedin_company_id = Column(String(100))
    website = Column(String(500))
    tier = Column(String(10), index=True)  # 'A', 'B', 'C'
    focus_sectors = Column(Text)  # Store as comma-separated string for SQLite compatibility, or use JSON/ARRAY for PG
    typical_check_size_gbp = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    announcements = relationship("VCAnnouncementModel", back_populates="vc_firm")

class VCAnnouncementModel(Base):
    """VC Announcement database model"""
    __tablename__ = 'vc_announcements'

    id = Column(Integer, primary_key=True)
    vc_firm_id = Column(Integer, ForeignKey('vc_firms.id'))
    company_name = Column(String(255), nullable=False)
    round_type = Column(String(50))  # 'Seed', 'Series A', etc.
    amount_gbp = Column(Integer)
    announced_date = Column(Date, index=True)
    description = Column(Text)
    source_url = Column(String(500))
    linkedin_post_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    vc_firm = relationship("VCFirmModel", back_populates="announcements")
    threat_score = relationship("ThreatScoreModel", back_populates="announcement", uselist=False)

class ThreatScoreModel(Base):
    """Threat Score database model"""
    __tablename__ = 'threat_scores'

    id = Column(Integer, primary_key=True)
    announcement_id = Column(Integer, ForeignKey('vc_announcements.id'))
    category = Column(String(100))  # 'aerospace', 'healthcare', 'fintech'
    threat_score = Column(Integer)  # 0-100
    threat_level = Column(String(20), index=True)  # 'critical', 'high', 'medium', 'low'
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    announcement = relationship("VCAnnouncementModel", back_populates="threat_score")

class MonitoringTargetModel(Base):
    """Target URL for monitoring (Concept: Web Monitor)"""
    __tablename__ = 'monitoring_targets'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    target_type = Column(String(50)) # 'homepage', 'team', 'pricing', 'news'
    last_checked = Column(DateTime)
    last_content_hash = Column(String(64)) # SHA256 of content to detect changes
    selector = Column(String(255)) # Optional CSS selector to focus on
    is_active = Column(Integer, default=1)
    
    changes = relationship("DetectedChangeModel", back_populates="target")
    price_points = relationship("PricePointModel", back_populates="target")

class DetectedChangeModel(Base):
    """Record of a detected change on a monitored target"""
    __tablename__ = 'detected_changes'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('monitoring_targets.id'))
    detected_at = Column(DateTime, default=datetime.utcnow)
    change_type = Column(String(50)) # 'content_diff', 'visual_diff', 'api_diff'
    description = Column(Text) # Summary of what changed
    diff_content = Column(Text) # The actual diff or JSON change
    screenshot_path = Column(String(500))
    severity = Column(String(20), default="medium")
    
    target = relationship("MonitoringTargetModel", back_populates="changes")

class PricePointModel(Base):
    """Structured pricing data point"""
    __tablename__ = 'price_points'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('monitoring_targets.id'))
    recorded_at = Column(DateTime, default=datetime.utcnow)
    plan_name = Column(String(100))
    price_amount = Column(Integer) # Normalized
    currency = Column(String(10), default='GBP')
    billing_period = Column(String(20)) # 'monthly', 'annual'
    
    target = relationship("MonitoringTargetModel", back_populates="price_points")


# Helper functions using core database utilities
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def init_db():
    """Initialize database tables"""
    from src.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Competitive database tables initialized")

async def create_vc_firm(session: AsyncSession, firm_data: dict) -> VCFirmModel:
    """Create a new VC firm"""
    # Handle list to string conversion for SQLite compatibility if needed
    if isinstance(firm_data.get('focus_sectors'), list):
        firm_data['focus_sectors'] = ",".join(firm_data['focus_sectors'])
        
    firm = VCFirmModel(**firm_data)
    session.add(firm)
    await session.flush()
    await session.refresh(firm)
    return firm

async def get_vc_firm(session: AsyncSession, name: str) -> Optional[VCFirmModel]:
    """Get VC firm by name"""
    result = await session.execute(select(VCFirmModel).where(VCFirmModel.name == name))
    return result.scalars().first()

async def create_announcement(session: AsyncSession, announcement_data: dict, threat_data: Optional[dict] = None) -> VCAnnouncementModel:
    """Create announcement and optional threat score"""
    announcement = VCAnnouncementModel(**announcement_data)
    session.add(announcement)
    await session.flush()  # Get ID

    if threat_data:
        threat_data['announcement_id'] = announcement.id
        threat = ThreatScoreModel(**threat_data)
        session.add(threat)

    await session.flush()
    await session.refresh(announcement)
    return announcement

async def get_threats_by_level(session: AsyncSession, levels: List[str]) -> List[ThreatScoreModel]:
    """Get threats by level (e.g. ['critical', 'high'])"""
    result = await session.execute(
        select(ThreatScoreModel)
        .filter(ThreatScoreModel.threat_level.in_(levels))
        .order_by(ThreatScoreModel.threat_score.desc())
    )
    return result.scalars().all()

"""Alerts router — consolidated notification system for RADAR."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, case

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.schemas import StandardResponse
from src.tracker.database import TrackingAlert, AlertPreference, TrackedCompany

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/alerts",
    tags=["Alerts"]
)


# --- Schemas ---

class AlertRead(BaseModel):
    id: int
    tracked_company_id: int
    company_id: Optional[int] = None  # The universe company ID (via TrackedCompany)
    alert_type: str
    message: str
    is_read: bool
    risk_level: str
    context_summary: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class AlertUpdate(BaseModel):
    is_read: bool


class PreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    notify_funding: Optional[bool] = None
    notify_leadership: Optional[bool] = None
    notify_news: Optional[bool] = None
    notify_product: Optional[bool] = None
    digest_frequency: Optional[str] = None


# --- Endpoints ---

@router.get("/", response_model=StandardResponse[List[dict]], summary="Get Alerts")
async def get_alerts(
    unread_only: bool = False,
    risk_level: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """
    Get list of alerts. Joins with TrackedCompany to include company_id.
    Serves both Dashboard.jsx and AlertsFeed.jsx.
    """
    stmt = (
        select(TrackingAlert, TrackedCompany.company_id)
        .outerjoin(TrackedCompany, TrackingAlert.tracked_company_id == TrackedCompany.id)
    )

    if unread_only:
        stmt = stmt.where(TrackingAlert.is_read == False)
    if risk_level is not None:
        stmt = stmt.where(TrackingAlert.risk_level == risk_level)

    risk_order = case(
        (TrackingAlert.risk_level == "high", 1),
        (TrackingAlert.risk_level == "elevated", 2),
        else_=3
    )
    stmt = stmt.order_by(risk_order, TrackingAlert.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    data = [
        {
            "id": alert.id,
            "tracked_company_id": alert.tracked_company_id,
            "company_id": company_id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "is_read": alert.is_read,
            "risk_level": getattr(alert, "risk_level", "low"),
            "context_summary": getattr(alert, "context_summary", None),
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }
        for alert, company_id in rows
    ]
    return StandardResponse(data=data)


@router.get("/unread-count", response_model=StandardResponse[dict], summary="Unread Alert Count")
async def get_unread_count(session: AsyncSession = Depends(get_db)):
    """Get the count of unread alerts for badge."""
    stmt = select(func.count(TrackingAlert.id)).where(TrackingAlert.is_read == False)
    result = await session.execute(stmt)
    count = result.scalar() or 0
    return StandardResponse(data={"count": count})


@router.patch("/{alert_id}", response_model=StandardResponse[dict], summary="Update Alert")
async def update_alert(
    alert_id: int, 
    update: AlertUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Mark alert as read/unread (with request body)."""
    stmt = select(TrackingAlert).where(TrackingAlert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = update.is_read
    await session.commit()
    await session.refresh(alert)

    return StandardResponse(data={
        "id": alert.id,
        "tracked_company_id": alert.tracked_company_id,
        "alert_type": alert.alert_type,
        "message": alert.message,
        "is_read": alert.is_read,
        "risk_level": getattr(alert, "risk_level", "low"),
        "context_summary": getattr(alert, "context_summary", None),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    })


@router.patch("/{alert_id}/read", response_model=StandardResponse[dict], summary="Mark Alert Read")
async def mark_alert_read(
    alert_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Convenience endpoint: mark a single alert as read (no request body needed).
    Used by AlertsFeed.jsx.
    """
    stmt = select(TrackingAlert).where(TrackingAlert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    await session.commit()

    return StandardResponse(data={"status": "success", "alert_id": alert_id})


@router.get("/preferences", response_model=StandardResponse[dict], summary="Get Preferences")
async def get_preferences(session: AsyncSession = Depends(get_db)):
    """Get user alert preferences."""
    stmt = select(AlertPreference).where(AlertPreference.user_id == "default_user")
    result = await session.execute(stmt)
    pref = result.scalar_one_or_none()

    if not pref:
        pref = AlertPreference(user_id="default_user")
        session.add(pref)
        await session.commit()

    return StandardResponse(data=pref.to_dict())


@router.post("/preferences", response_model=StandardResponse[dict], summary="Update Preferences")
async def update_preferences(
    settings: PreferenceUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update alert preferences."""
    stmt = select(AlertPreference).where(AlertPreference.user_id == "default_user")
    result = await session.execute(stmt)
    pref = result.scalar_one_or_none()

    if not pref:
        pref = AlertPreference(user_id="default_user")
        session.add(pref)

    if settings.email_enabled is not None:
        pref.email_enabled = settings.email_enabled
    if settings.slack_enabled is not None:
        pref.slack_enabled = settings.slack_enabled
    if settings.notify_funding is not None:
        pref.notify_funding = settings.notify_funding
    if settings.notify_leadership is not None:
        pref.notify_leadership = settings.notify_leadership
    if settings.notify_news is not None:
        pref.notify_news = settings.notify_news
    if settings.notify_product is not None:
        pref.notify_product = settings.notify_product
    if settings.digest_frequency is not None:
        pref.digest_frequency = settings.digest_frequency

    await session.commit()
    await session.refresh(pref)
    return StandardResponse(data=pref.to_dict())


@router.post("/test-trigger", summary="Trigger Test Alert")
async def trigger_test_alert():
    """Manually trigger the alert engine for testing."""
    from src.alerts.alert_engine import alert_engine

    try:
        await alert_engine.create_test_event()
        await alert_engine.check_alerts()
        return {"status": "triggered"}
    except Exception as e:
        logger.exception("Test alert trigger failed")
        raise HTTPException(status_code=500, detail=str(e))

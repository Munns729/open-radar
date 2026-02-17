"""Tracker router — target watchlist management, notes, events, documents, AI agent."""

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, desc

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.schemas import StandardResponse, PaginatedResponse
from fastapi import Depends
from src.tracker.database import (
    TrackedCompany, CompanyEvent, CompanyNote, CompanyDocument,
    TrackingStatus,
)
from src.tracker.enricher import CompanyEnricher

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tracker",
    tags=["Target Tracker"]
)


# --- Schemas ---

class AddCompanyRequest(BaseModel):
    company_id: int
    priority: str = "medium"
    tags: list = []
    notes: str = None


class AddNoteRequest(BaseModel):
    note_text: str
    created_by: str = None
    note_type: str = "research"


class BatchAddRequest(BaseModel):
    company_ids: List[int]
    priority: str = "medium"
    tags: List[str] = []


class QueryRequest(BaseModel):
    question: str


# --- Endpoints ---

@router.post("/add")
async def add_company_to_tracker(request: AddCompanyRequest):
    """Add a company to tracking."""
    from src.tracker.workflow import add_company_to_tracking

    try:
        tracked = await add_company_to_tracking(
            company_id=request.company_id,
            priority=request.priority,
            tags=request.tags,
            notes=request.notes
        )
        return {
            "status": "success",
            "message": "Company added to tracking",
            "tracked_id": tracked.id,
            "company_id": tracked.company_id
        }
    except Exception as e:
        logger.exception("Failed to add company to tracker")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-add", response_model=StandardResponse[dict], summary="Batch Add Targets")
async def batch_add_to_tracker(
    request: BatchAddRequest,
    session: AsyncSession = Depends(get_db)
):
    """Add multiple companies to tracking in one operation."""
    added_count = 0
    for company_id in request.company_ids:
        exists = await session.execute(
            select(TrackedCompany).where(TrackedCompany.company_id == company_id)
        )
        if exists.scalar_one_or_none():
            continue

        tracker = TrackedCompany(
            company_id=company_id,
            priority=request.priority,
            tags=request.tags,
            tracking_status=TrackingStatus.PROSPECTING,
            added_date=date.today()
        )
        session.add(tracker)
        added_count += 1

    await session.commit()
    return StandardResponse(data={"added_count": added_count})


@router.get("/companies", response_model=StandardResponse[list])
async def get_tracked_companies(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_db)
):
    """List all tracked companies with optional filters."""
    stmt = select(TrackedCompany).limit(limit)

    if status:
        stmt = stmt.where(TrackedCompany.tracking_status == status)
    if priority:
        stmt = stmt.where(TrackedCompany.priority == priority)

    stmt = stmt.order_by(TrackedCompany.added_date.desc())

    result = await session.execute(stmt)
    tracked_companies = result.scalars().all()

    data = [
        {
            "id": tc.id,
            "company_id": tc.company_id,
            "tracking_status": tc.tracking_status,
            "priority": tc.priority,
            "tags": tc.tags,
            "notes": tc.notes,
            "added_date": tc.added_date.isoformat() if tc.added_date else None,
            "last_checked": tc.last_checked.isoformat() if tc.last_checked else None,
            "next_check_due": tc.next_check_due.isoformat() if tc.next_check_due else None,
        }
        for tc in tracked_companies
    ]
    return StandardResponse(data=data)


@router.get("/company/{tracked_id}", response_model=StandardResponse[dict])
async def get_tracked_company_detail(
    tracked_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get detailed profile for a tracked company."""
    stmt = select(TrackedCompany).where(TrackedCompany.id == tracked_id)
    result = await session.execute(stmt)
    tracked = result.scalar_one_or_none()

    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked company not found")

    enricher = CompanyEnricher()
    profile = await enricher.enrich_tracked_company(tracked.company_id)

    events_stmt = select(CompanyEvent).where(
        CompanyEvent.tracked_company_id == tracked_id
    ).order_by(CompanyEvent.event_date.desc()).limit(20)
    events_result = await session.execute(events_stmt)
    events = events_result.scalars().all()

    notes_stmt = select(CompanyNote).where(
        CompanyNote.tracked_company_id == tracked_id
    ).order_by(CompanyNote.created_at.desc()).limit(20)
    notes_result = await session.execute(notes_stmt)
    notes = notes_result.scalars().all()

    return StandardResponse(data={
        "tracking": {
            "id": tracked.id,
            "company_id": tracked.company_id,
            "tracking_status": tracked.tracking_status,
            "priority": tracked.priority,
            "tags": tracked.tags,
            "notes": tracked.notes,
            "added_date": tracked.added_date.isoformat() if tracked.added_date else None,
            "last_checked": tracked.last_checked.isoformat() if tracked.last_checked else None,
        },
        "profile": profile,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "title": e.title,
                "description": e.description,
                "severity": e.severity,
                "source_url": e.source_url,
            }
            for e in events
        ],
        "notes": [
            {
                "id": n.id,
                "note_text": n.note_text,
                "created_by": n.created_by,
                "note_type": n.note_type,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
    })


@router.post("/company/{tracked_id}/note", response_model=StandardResponse[dict])
async def add_note_to_tracked_company(
    tracked_id: int, 
    request: AddNoteRequest,
    session: AsyncSession = Depends(get_db)
):
    """Add a note to a tracked company."""
    stmt = select(TrackedCompany).where(TrackedCompany.id == tracked_id)
    result = await session.execute(stmt)
    tracked = result.scalar_one_or_none()

    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked company not found")

    note = CompanyNote(
        tracked_company_id=tracked_id,
        note_text=request.note_text,
        created_by=request.created_by,
        note_type=request.note_type,
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return StandardResponse(data={
        "note_id": note.id,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    })


@router.get("/company/{tracked_id}/events", response_model=StandardResponse[list])
async def get_tracked_company_events(
    tracked_id: int,
    severity: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """Get event timeline for a tracked company."""
    stmt = select(CompanyEvent).where(
        CompanyEvent.tracked_company_id == tracked_id
    )

    if severity:
        stmt = stmt.where(CompanyEvent.severity == severity)

    stmt = stmt.order_by(CompanyEvent.event_date.desc()).limit(limit)

    result = await session.execute(stmt)
    events = result.scalars().all()

    data = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "title": e.title,
            "description": e.description,
            "severity": e.severity,
            "source_url": e.source_url,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
    return StandardResponse(data=data)


@router.post("/company/{tracked_id}/documents", response_model=StandardResponse[dict], summary="Upload Document")
async def upload_company_document(
    tracked_id: int, 
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    """Upload a document for the AI agent to analyze."""
    from src.tracker.files import FileManager

    stmt = select(TrackedCompany).where(TrackedCompany.id == tracked_id)
    result = await session.execute(stmt)
    tracked = result.scalar_one_or_none()

    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked company not found")

    storage_path, filename = await FileManager.save_file(tracked.company_id, file)

    file_type = filename.split('.')[-1]
    text = FileManager.extract_text(storage_path, file_type)

    doc = CompanyDocument(
        tracked_company_id=tracked_id,
        filename=filename,
        file_type=file_type,
        storage_path=storage_path,
        extracted_text=text
    )
    session.add(doc)
    await session.commit()

    return StandardResponse(data={"message": "File uploaded and processed"})


@router.get("/company/{tracked_id}/documents", response_model=StandardResponse[list], summary="List Documents")
async def list_company_documents(
    tracked_id: int,
    session: AsyncSession = Depends(get_db)
):
    """List documents available for a company."""
    stmt = select(CompanyDocument).where(
        CompanyDocument.tracked_company_id == tracked_id
    ).order_by(CompanyDocument.uploaded_at.desc())

    docs = (await session.execute(stmt)).scalars().all()

    data = [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "uploaded_at": d.uploaded_at.isoformat()
        }
        for d in docs
    ]
    return StandardResponse(data=data)


@router.post("/company/{tracked_id}/query", summary="AI Agent Query")
async def query_tracker_agent(tracked_id: int, request: QueryRequest):
    """Ask the AI agent a question about the company using unified context."""
    from src.tracker.agent import TrackerAgent

    agent = TrackerAgent()
    response = await agent.query(tracked_id, request.question)

    return response


@router.delete("/company/{tracked_id}")
async def remove_company_from_tracker(tracked_id: int, hard_delete: bool = False):
    """Remove a company from tracking."""
    from src.tracker.workflow import remove_company_from_tracking

    success = await remove_company_from_tracking(tracked_id, hard_delete=hard_delete)

    if not success:
        raise HTTPException(status_code=404, detail="Tracked company not found")

    return {
        "status": "success",
        "message": "Company removed from tracking" if hard_delete else "Company tracking closed"
    }

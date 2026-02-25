"""Document Intelligence router — upload, extract, reconcile to Canon."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks
from sqlalchemy import select, func, desc

from src.core.database import get_async_db
from src.core.schemas import StandardResponse
from src.universe.database import CompanyModel
from src.documents.database import DocumentIngestion, DocumentExtract
from src.documents.service import ingest_document, process_document

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/documents",
    tags=["Document Intelligence"],
)


async def _company_exists(company_id: int) -> bool:
    async with get_async_db() as session:
        result = await session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        return result.scalar_one_or_none() is not None


@router.post("/{company_id}/upload", response_model=StandardResponse[dict], summary="Upload document")
async def upload_document(
    company_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form(...),
):
    """Upload a document; enqueue processing. Returns document_id and status=processing."""
    if not await _company_exists(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    content = await file.read()
    doc, created = await ingest_document(
        company_id=company_id,
        document_type=document_type.strip() or "other",
        filename=file.filename or "file",
        file_content=content,
    )
    if created:
        background_tasks.add_task(process_document, doc.id)
    return StandardResponse(
        data={"document_id": doc.id, "status": "processing" if created else doc.processing_status}
    )


@router.get("/{company_id}", response_model=StandardResponse[list], summary="List documents")
async def list_documents(company_id: int):
    """List DocumentIngestion rows for company, ordered by uploaded_at desc."""
    if not await _company_exists(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentIngestion)
            .where(DocumentIngestion.company_id == company_id)
            .order_by(desc(DocumentIngestion.uploaded_at))
        )
        rows = result.scalars().all()
    data = [
        {
            "id": r.id,
            "company_id": r.company_id,
            "document_type": r.document_type,
            "filename": r.filename,
            "processing_status": r.processing_status,
            "page_count": r.page_count,
            "error_message": r.error_message,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
    return StandardResponse(data=data)


@router.get("/{company_id}/summary", response_model=StandardResponse[dict], summary="Document intelligence summary")
async def document_summary(company_id: int):
    """Aggregate across DocumentExtract: red flags, open questions, moat directions, tier signals, proposal count."""
    if not await _company_exists(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentExtract).where(DocumentExtract.company_id == company_id)
        )
        extracts = result.scalars().all()
    red_flags: list[str] = []
    open_questions: list[str] = []
    moat_by_pillar: dict[str, list[str]] = {}
    tier_signals: list[dict[str, Any]] = []
    proposal_count = 0
    doc_count_by_type: dict[str, int] = {}
    async with get_async_db() as session:
        ing_result = await session.execute(
            select(DocumentIngestion.document_type, func.count(DocumentIngestion.id))
            .where(DocumentIngestion.company_id == company_id)
            .group_by(DocumentIngestion.document_type)
        )
        for row in ing_result.all():
            doc_count_by_type[row[0] or "other"] = row[1]
    for ex in extracts:
        if ex.red_flags:
            red_flags.extend(ex.red_flags)
        if ex.open_questions_raised:
            open_questions.extend(ex.open_questions_raised)
        if ex.moat_evidence:
            for pillar, ev in ex.moat_evidence.items():
                if isinstance(ev, dict) and ev.get("direction"):
                    if pillar not in moat_by_pillar:
                        moat_by_pillar[pillar] = []
                    moat_by_pillar[pillar].append(ev.get("direction", ""))
        if ex.tier_signal and isinstance(ex.tier_signal, dict):
            tier_signals.append(ex.tier_signal)
        proposal_count += ex.proposals_generated or 0
    return StandardResponse(
        data={
            "doc_count_by_type": doc_count_by_type,
            "red_flags": red_flags,
            "open_questions": open_questions,
            "moat_evidence_by_pillar": moat_by_pillar,
            "tier_signals": tier_signals,
            "proposal_count": proposal_count,
        }
    )


@router.get("/item/{document_id}", response_model=StandardResponse[dict], summary="Get single document and extract")
async def get_document_item(document_id: int):
    """Single DocumentIngestion with its DocumentExtract if present."""
    async with get_async_db() as session:
        ing_result = await session.execute(
            select(DocumentIngestion).where(DocumentIngestion.id == document_id)
        )
        ingestion = ing_result.scalar_one_or_none()
        if not ingestion:
            raise HTTPException(status_code=404, detail="Document not found")
        ex_result = await session.execute(
            select(DocumentExtract).where(DocumentExtract.document_id == document_id)
        )
        extract = ex_result.scalar_one_or_none()
    data = {
        "id": ingestion.id,
        "company_id": ingestion.company_id,
        "document_type": ingestion.document_type,
        "filename": ingestion.filename,
        "processing_status": ingestion.processing_status,
        "page_count": ingestion.page_count,
        "error_message": ingestion.error_message,
        "uploaded_at": ingestion.uploaded_at.isoformat() if ingestion.uploaded_at else None,
        "processed_at": ingestion.processed_at.isoformat() if ingestion.processed_at else None,
    }
    if extract:
        data["extract"] = {
            "id": extract.id,
            "moat_evidence": extract.moat_evidence,
            "resilience_evidence": extract.resilience_evidence,
            "thesis_elements": extract.thesis_elements,
            "tier_signal": extract.tier_signal,
            "scarcity_signals": extract.scarcity_signals,
            "open_questions_raised": extract.open_questions_raised,
            "red_flags": extract.red_flags,
            "proposals_generated": extract.proposals_generated,
            "llm_prompt_version": extract.llm_prompt_version,
            "extracted_at": extract.extracted_at.isoformat() if extract.extracted_at else None,
        }
    else:
        data["extract"] = None
    return StandardResponse(data=data)


@router.post("/item/{document_id}/reprocess", response_model=StandardResponse[dict], summary="Reprocess document")
async def reprocess_document(document_id: int, background_tasks: BackgroundTasks):
    """Set status=pending and enqueue process_document."""
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentIngestion).where(DocumentIngestion.id == document_id)
        )
        ingestion = result.scalar_one_or_none()
        if not ingestion:
            raise HTTPException(status_code=404, detail="Document not found")
        ingestion.processing_status = "pending"
        ingestion.error_message = None
    background_tasks.add_task(process_document, document_id)
    return StandardResponse(data={"document_id": document_id, "status": "processing"})

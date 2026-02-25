"""
Document ingestion: upload, extract text, LLM extraction, reconcile to Canon.
"""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update

from src.core.database import get_async_db
from src.documents.database import DocumentIngestion, DocumentExtract
from src.documents.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
    EXTRACT_PROMPT_VERSION,
)
from src.canon.service import get_canon, get_current_moat_scores, update_canon, create_proposal
from src.universe.database import CompanyModel
from src.core.ai_client import ai_client
from src.core.config import settings

logger = logging.getLogger(__name__)

DOCUMENT_UPLOAD_DIR = settings.data_dir / "document_ingestions"


def extract_text_from_file(file_path: str) -> tuple[str, int]:
    """
    Extract text from file. PDF: pdfplumber; DOCX: python-docx; else plain text.
    Returns (text, page_count). Raises ValueError if extraction fails completely.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            import pdfplumber
            text_parts = []
            page_count = 0
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            text = "\n".join(text_parts) if text_parts else ""
            if not text and page_count > 0:
                raise ValueError("PDF produced no extractable text")
            return text, page_count
        if suffix in (".docx", ".doc"):
            from docx import Document
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text, 0
        # .txt, .md, etc.
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text, 0
    except Exception as e:
        logger.exception("extract_text_from_file failed for %s: %s", file_path, e)
        raise ValueError(f"Text extraction failed: {e}") from e


async def ingest_document(
    company_id: int,
    document_type: str,
    filename: str,
    file_content: bytes,
) -> tuple[DocumentIngestion, bool]:
    """
    Dedupe by (company_id, file_hash). Save file to disk, extract text, create DocumentIngestion with status=pending.
    Returns (document_ingestion, created: True if new row, False if existing).
    """
    file_hash = hashlib.sha256(file_content).hexdigest()
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentIngestion).where(
                DocumentIngestion.company_id == company_id,
                DocumentIngestion.file_hash == file_hash,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

    # Save file to disk (same pattern as tracker: company dir under upload root)
    DOCUMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    company_dir = DOCUMENT_UPLOAD_DIR / str(company_id)
    company_dir.mkdir(exist_ok=True)
    safe_name = Path(filename).name
    storage_path = company_dir / safe_name
    storage_path.write_bytes(file_content)
    storage_path_str = str(storage_path)

    raw_text = None
    page_count = None
    try:
        raw_text, page_count = extract_text_from_file(storage_path_str)
    except ValueError as e:
        logger.warning("Text extraction failed for %s: %s", filename, e)
        # Still create ingestion; processing will fail with a clear error

    async with get_async_db() as session:
        row = DocumentIngestion(
            company_id=company_id,
            document_type=document_type,
            filename=filename,
            file_hash=file_hash,
            raw_text=raw_text,
            page_count=page_count,
            processing_status="pending",
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return row, True


async def process_document(document_id: int) -> DocumentExtract | None:
    """
    Load ingestion, set processing, run LLM extraction, create DocumentExtract, reconcile to Canon, set complete.
    """
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentIngestion).where(DocumentIngestion.id == document_id)
        )
        ingestion = result.scalar_one_or_none()
        if not ingestion:
            logger.warning("DocumentIngestion id=%s not found", document_id)
            return None
        ingestion.processing_status = "processing"
        await session.flush()
        await session.commit()

    company_id = ingestion.company_id
    company_name = "Unknown"
    async with get_async_db() as session:
        company_result = await session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        if company:
            company_name = company.name or "Unknown"

    if not (ingestion.raw_text and ingestion.raw_text.strip()):
        async with get_async_db() as session:
            result = await session.execute(
                select(DocumentIngestion).where(DocumentIngestion.id == document_id)
            )
            ing = result.scalar_one()
            ing.processing_status = "failed"
            ing.error_message = "No extractable text (image-only or empty document)"
            await session.commit()
        return None

    canon = await get_canon(company_id)
    current_moat_scores = await get_current_moat_scores(company_id)
    current_thesis = canon.thesis_summary if canon else None
    open_questions = canon.open_questions if canon else None

    user_prompt = build_extraction_prompt(
        company_name=company_name,
        document_type=ingestion.document_type,
        raw_text=ingestion.raw_text,
        current_thesis=current_thesis,
        current_moat_scores=current_moat_scores,
        open_questions=open_questions,
    )
    try:
        raw_response = await ai_client.generate(
            user_prompt, EXTRACTION_SYSTEM_PROMPT, temperature=0.1
        )
    except Exception as e:
        logger.exception("LLM generate failed for document_id=%s: %s", document_id, e)
        async with get_async_db() as session:
            result = await session.execute(
                select(DocumentIngestion).where(DocumentIngestion.id == document_id)
            )
            ing = result.scalar_one()
            ing.processing_status = "failed"
            ing.error_message = str(e)
            await session.commit()
        return None

    # Strip markdown fences and parse JSON
    text = raw_response.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("LLM response not valid JSON for document_id=%s: %s", document_id, e)
        async with get_async_db() as session:
            result = await session.execute(
                select(DocumentIngestion).where(DocumentIngestion.id == document_id)
            )
            ing = result.scalar_one()
            ing.processing_status = "failed"
            ing.error_message = f"Invalid JSON: {e}"
            await session.commit()
        return None

    # Build or update extract row (one per document_id)
    extract_data = {
        "moat_evidence": parsed.get("moat_evidence"),
        "resilience_evidence": parsed.get("resilience_evidence"),
        "thesis_elements": parsed.get("thesis_elements"),
        "tier_signal": parsed.get("tier_signal"),
        "scarcity_signals": parsed.get("scarcity_signals"),
        "open_questions_raised": parsed.get("open_questions_raised"),
        "red_flags": parsed.get("red_flags"),
        "llm_prompt_version": EXTRACT_PROMPT_VERSION,
    }
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentExtract).where(DocumentExtract.document_id == document_id)
        )
        existing_extract = result.scalar_one_or_none()
        if existing_extract:
            for key, value in extract_data.items():
                setattr(existing_extract, key, value)
            extract = existing_extract
            await session.flush()
            await session.refresh(extract)
        else:
            extract = DocumentExtract(
                document_id=document_id,
                company_id=company_id,
                **extract_data,
            )
            session.add(extract)
            await session.flush()
            await session.refresh(extract)
        await session.commit()

    proposals_count = await _reconcile_extract(extract, company_id, document_id)

    async with get_async_db() as session:
        await session.execute(
            update(DocumentExtract).where(DocumentExtract.id == extract.id).values(
                proposals_generated=proposals_count
            )
        )
        await session.execute(
            update(DocumentIngestion).where(DocumentIngestion.id == document_id).values(
                processing_status="complete",
                processed_at=datetime.utcnow(),
            )
        )
        await session.commit()

    # Reload extract to return with proposals_generated set
    async with get_async_db() as session:
        result = await session.execute(
            select(DocumentExtract).where(DocumentExtract.document_id == document_id)
        )
        return result.scalar_one_or_none()


async def _reconcile_extract(
    extract: DocumentExtract, company_id: int, document_id: int
) -> int:
    """
    Apply extract to Canon: open questions, red flags, moat proposals, tier proposal.
    Each block is try/except so one failure does not block others. Returns proposals_count.
    """
    proposals_count = 0

    # Open questions — append
    if extract.open_questions_raised:
        try:
            canon = await get_canon(company_id)
            existing = (canon.open_questions or []) if canon else []
            new_q = [q for q in extract.open_questions_raised if q not in existing]
            if new_q:
                await update_canon(
                    company_id,
                    {"open_questions": existing + new_q},
                    source_module="document_ingestion",
                    triggered_by=f"doc_{document_id}",
                )
        except Exception as e:
            logger.warning("Reconcile open_questions failed: %s", e)

    # Red flags — prepend and append to open_questions
    if extract.red_flags:
        try:
            flagged = [f"⚠️ RED FLAG: {f}" for f in extract.red_flags]
            canon = await get_canon(company_id)
            existing = (canon.open_questions or []) if canon else []
            await update_canon(
                company_id,
                {"open_questions": flagged + existing},
                source_module="document_ingestion",
                triggered_by=f"doc_{document_id}",
            )
        except Exception as e:
            logger.warning("Reconcile red_flags failed: %s", e)

    # Moat evidence → proposal if confidence >= 0.65
    if extract.moat_evidence:
        try:
            current_scores = await get_current_moat_scores(company_id)
            for pillar, ev in extract.moat_evidence.items():
                if not isinstance(ev, dict):
                    continue
                if ev.get("confidence", 0) < 0.65:
                    continue
                current = current_scores.get(pillar, 50)
                direction = ev.get("direction")
                if direction == "weakens" and current > 50:
                    await create_proposal(
                        company_id=company_id,
                        proposed_field=f"moat_{pillar}",
                        proposed_value=str(max(0, current - 15)),
                        current_value=str(current),
                        rationale=ev.get("evidence"),
                        signals=[ev.get("key_quote", "")],
                        source_module="document_ingestion",
                        triggered_by=f"doc_{document_id}",
                    )
                    proposals_count += 1
                elif direction == "strengthens" and current < 50:
                    await create_proposal(
                        company_id=company_id,
                        proposed_field=f"moat_{pillar}",
                        proposed_value=str(min(100, current + 15)),
                        current_value=str(current),
                        rationale=ev.get("evidence"),
                        signals=[ev.get("key_quote", "")],
                        source_module="document_ingestion",
                        triggered_by=f"doc_{document_id}",
                    )
                    proposals_count += 1
        except Exception as e:
            logger.warning("Reconcile moat_evidence failed: %s", e)

    # Tier signal → proposal if confidence >= 0.70 and direction != maintain
    if (
        extract.tier_signal
        and isinstance(extract.tier_signal, dict)
        and extract.tier_signal.get("confidence", 0) >= 0.70
        and extract.tier_signal.get("direction") != "maintain"
    ):
        try:
            canon = await get_canon(company_id)
            current_tier = canon.current_tier if canon else None
            await create_proposal(
                company_id=company_id,
                proposed_field="current_tier",
                proposed_value=extract.tier_signal.get("direction", ""),
                current_value=str(current_tier) if current_tier is not None else None,
                rationale=extract.tier_signal.get("rationale"),
                source_module="document_ingestion",
                triggered_by=f"doc_{document_id}",
            )
            proposals_count += 1
        except Exception as e:
            logger.warning("Reconcile tier_signal failed: %s", e)

    return proposals_count

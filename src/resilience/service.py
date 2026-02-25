"""
AI Resilience service: record assessments, run automated scoring, flags, portfolio matrix.
"""
import json
import logging
from typing import Any

from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.core.ai_client import ai_client
from src.canon.service import get_canon, update_canon
from src.canon.database import CompanyCanon
from src.capability.service import get_all_levels
from src.universe.database import CompanyModel
from src.resilience.database import AIResilienceAssessment, AIResilienceFlag
from src.resilience.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)

logger = logging.getLogger(__name__)

VALID_VERDICTS = ("resilient", "watch", "exposed")
VALID_SCARCITY = (
    "regulatory_permission",
    "physical_chokepoint",
    "proprietary_data",
    "network_lock_in",
    "trust_and_liability",
    "none",
)


def _compute_composite(
    substitution_score: int,
    disintermediation_score: int,
    amplification_score: int,
    cost_disruption_score: int,
) -> float:
    """((6-sub) + (6-disint) + amp + (6-cost)) / 16 * 100"""
    return ((6 - substitution_score) + (6 - disintermediation_score) + amplification_score + (6 - cost_disruption_score)) / 16.0 * 100.0


def _compute_verdict(composite_score: float) -> str:
    if composite_score >= 70:
        return "resilient"
    if composite_score >= 45:
        return "watch"
    return "exposed"


async def record_assessment(
    company_id: int,
    capability_level: int,
    scores: dict,
    assessed_by: str = "manual",
    llm_prompt_version: str | None = None,
    raw_llm_response: str | None = None,
) -> AIResilienceAssessment:
    """
    Compute composite and verdict, optionally create flag, optionally update canon open_questions.
    Insert new assessment row and return it.
    """
    sub = scores.get("substitution_score")
    disint = scores.get("disintermediation_score")
    amp = scores.get("amplification_score")
    cost = scores.get("cost_disruption_score")
    if None in (sub, disint, amp, cost):
        raise ValueError("Missing one or more dimension scores (substitution, disintermediation, amplification, cost_disruption)")
    composite_score = _compute_composite(sub, disint, amp, cost)
    overall_verdict = _compute_verdict(composite_score)

    scarcity = scores.get("scarcity_classification")
    if scarcity and scarcity not in VALID_SCARCITY:
        scarcity = "none"
    scarcity_rationale = scores.get("scarcity_rationale")
    assessment_notes = scores.get("assessment_notes")

    async with get_async_db() as session:
        prev = await _get_previous_assessment(session, company_id, capability_level)
        composite_delta = None
        if prev and prev.composite_score is not None:
            composite_delta = composite_score - prev.composite_score
        verdict_changed = (prev is None) or (prev.overall_verdict != overall_verdict)
        delta_above = composite_delta is not None and abs(composite_delta) >= 10
        if prev and (delta_above or verdict_changed):
            flag = AIResilienceFlag(
                company_id=company_id,
                capability_level=capability_level,
                previous_verdict=prev.overall_verdict,
                new_verdict=overall_verdict,
                composite_delta=composite_delta,
                flag_reason=None,
            )
            session.add(flag)
            await session.flush()

        row = AIResilienceAssessment(
            company_id=company_id,
            capability_level=capability_level,
            substitution_score=sub,
            disintermediation_score=disint,
            amplification_score=amp,
            cost_disruption_score=cost,
            composite_score=composite_score,
            overall_verdict=overall_verdict,
            scarcity_classification=scarcity,
            scarcity_rationale=scarcity_rationale,
            assessed_by=assessed_by,
            llm_prompt_version=llm_prompt_version,
            raw_llm_response=raw_llm_response,
            assessment_notes=assessment_notes,
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)

    if overall_verdict == "exposed" and (prev is None or prev.overall_verdict != "exposed"):
        canon = await get_canon(company_id)
        open_questions = list(canon.open_questions or []) if canon else []
        open_questions.append(f"⚠️ AI Resilience: L{capability_level} assessment = EXPOSED")
        await update_canon(
            company_id,
            {"open_questions": open_questions},
            source_module="resilience",
        )

    return row


async def _get_previous_assessment(
    session: AsyncSession,
    company_id: int,
    capability_level: int,
) -> AIResilienceAssessment | None:
    result = await session.execute(
        select(AIResilienceAssessment)
        .where(
            and_(
                AIResilienceAssessment.company_id == company_id,
                AIResilienceAssessment.capability_level == capability_level,
            )
        )
        .order_by(desc(AIResilienceAssessment.assessed_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_assessment(
    company_id: int,
    capability_level: int,
) -> AIResilienceAssessment | None:
    """Most recent row for (company_id, capability_level)."""
    async with get_async_db() as session:
        return await _get_previous_assessment(session, company_id, capability_level)


async def get_resilience_trajectory(company_id: int) -> dict:
    """{level: [{composite_score, overall_verdict, assessed_at}]} for levels 1–4, chronological."""
    async with get_async_db() as session:
        result = await session.execute(
            select(AIResilienceAssessment)
            .where(AIResilienceAssessment.company_id == company_id)
            .order_by(AIResilienceAssessment.capability_level, AIResilienceAssessment.assessed_at.asc())
        )
        rows = result.scalars().all()
    by_level: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    for r in rows:
        if r.capability_level not in by_level:
            continue
        by_level[r.capability_level].append({
            "composite_score": r.composite_score,
            "overall_verdict": r.overall_verdict,
            "assessed_at": r.assessed_at.isoformat() if r.assessed_at else None,
        })
    return by_level


async def run_automated_assessment(
    company_id: int,
    capability_level: int,
) -> AIResilienceAssessment:
    """Load canon, company, moat scores, level description; call LLM; parse JSON; record_assessment."""
    async with get_async_db() as session:
        company_result = await session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")
    canon = await get_canon(company_id)
    moat_scores = await _get_current_moat_scores(company_id)
    levels = await get_all_levels()
    level_row = next((l for l in levels if l.level == capability_level), None)
    if not level_row:
        raise ValueError(f"Capability level {capability_level} not found")
    level_label = level_row.label or f"L{capability_level}"
    level_description = level_row.description or ""
    thesis_summary = canon.thesis_summary if canon else None
    open_questions = canon.open_questions if canon else []
    if isinstance(open_questions, list):
        open_questions = ", ".join(str(x) for x in open_questions) if open_questions else "None"
    else:
        open_questions = str(open_questions or "None")
    description = (company.description or "")[:2000]
    user_prompt = build_user_prompt(
        company_name=company.name or "Unknown",
        description=description,
        thesis_summary=thesis_summary,
        moat_scores=moat_scores,
        open_questions=open_questions,
        capability_level=capability_level,
        level_label=level_label,
        level_description=level_description,
    )
    raw = await ai_client.generate(user_prompt, SYSTEM_PROMPT, temperature=0.2)
    try:
        parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
    except json.JSONDecodeError as e:
        logger.error("Resilience LLM response not valid JSON: %s", raw[:500])
        raise ValueError(f"LLM response was not valid JSON: {e}. Raw (truncated): {raw[:300]}") from e
    scores = {
        "substitution_score": _int_score(parsed, "substitution_score"),
        "disintermediation_score": _int_score(parsed, "disintermediation_score"),
        "amplification_score": _int_score(parsed, "amplification_score"),
        "cost_disruption_score": _int_score(parsed, "cost_disruption_score"),
        "scarcity_classification": (parsed.get("scarcity_classification") or "none").strip(),
        "scarcity_rationale": (parsed.get("scarcity_rationale") or "").strip() or None,
        "assessment_notes": (parsed.get("assessment_notes") or "").strip() or None,
    }
    return await record_assessment(
        company_id=company_id,
        capability_level=capability_level,
        scores=scores,
        assessed_by="automated",
        llm_prompt_version=PROMPT_VERSION,
        raw_llm_response=raw,
    )


def _int_score(data: dict, key: str) -> int:
    v = data.get(key)
    if v is None:
        raise ValueError(f"Missing {key} in LLM response")
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {key}: expected int 1-5, got {v!r}")
    if not (1 <= n <= 5):
        raise ValueError(f"{key} must be 1-5, got {n}")
    return n


async def _get_current_moat_scores(company_id: int) -> dict:
    from src.canon.service import get_current_moat_scores as get_moat
    return await get_moat(company_id)


async def run_full_portfolio_assessment(company_ids: list[int]) -> dict:
    """For each company_id, for each level 1–4 call run_automated_assessment. Skip on error, log. Return {company_id: {level: verdict}}."""
    results: dict[int, dict[int, str]] = {}
    for cid in company_ids:
        results[cid] = {}
        for level in (1, 2, 3, 4):
            try:
                assessment = await run_automated_assessment(cid, level)
                results[cid][level] = assessment.overall_verdict or "unknown"
            except Exception as e:
                logger.warning("Resilience assessment failed company_id=%s level=%s: %s", cid, level, e)
    return results


async def get_portfolio_resilience_matrix() -> list[dict]:
    """Companies with any assessment: name, moat_score, l1–l4 verdicts, l2_composite; sorted by l2_composite desc."""
    from sqlalchemy import func as fn
    async with get_async_db() as session:
        subq = (
            select(
                AIResilienceAssessment.company_id,
                AIResilienceAssessment.capability_level,
                AIResilienceAssessment.composite_score,
                AIResilienceAssessment.overall_verdict,
                fn.row_number()
                .over(
                    partition_by=(
                        AIResilienceAssessment.company_id,
                        AIResilienceAssessment.capability_level,
                    ),
                    order_by=desc(AIResilienceAssessment.assessed_at),
                )
                .label("rn"),
            )
            .select_from(AIResilienceAssessment)
        ).subquery()
        latest = select(subq).where(subq.c.rn == 1)
        result = await session.execute(latest)
        rows = result.all()
    company_ids = list({r.company_id for r in rows})
    if not company_ids:
        return []
    async with get_async_db() as session:
        companies_result = await session.execute(
            select(CompanyModel).where(CompanyModel.id.in_(company_ids))
        )
        companies = {c.id: c for c in companies_result.scalars().all()}
    by_company: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r.company_id not in by_company:
            c = companies.get(r.company_id)
            by_company[r.company_id] = {
                "company_id": r.company_id,
                "company_name": c.name if c else str(r.company_id),
                "moat_score": c.moat_score if c else None,
                "l1_verdict": None,
                "l2_verdict": None,
                "l3_verdict": None,
                "l4_verdict": None,
                "l2_composite": None,
            }
        d = by_company[r.company_id]
        if r.capability_level == 1:
            d["l1_verdict"] = r.overall_verdict
        elif r.capability_level == 2:
            d["l2_verdict"] = r.overall_verdict
            d["l2_composite"] = r.composite_score
        elif r.capability_level == 3:
            d["l3_verdict"] = r.overall_verdict
        elif r.capability_level == 4:
            d["l4_verdict"] = r.overall_verdict
    out = list(by_company.values())
    out.sort(key=lambda x: (x["l2_composite"] is None, -(x["l2_composite"] or 0)))
    return out


async def get_resilience_flags(
    reviewed: bool = False,
    limit: int = 50,
) -> list[AIResilienceFlag]:
    async with get_async_db() as session:
        result = await session.execute(
            select(AIResilienceFlag)
            .where(AIResilienceFlag.reviewed == reviewed)
            .order_by(desc(AIResilienceFlag.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


async def mark_flag_reviewed(flag_id: int) -> AIResilienceFlag | None:
    """Set flag.reviewed = True. Return the flag or None if not found."""
    async with get_async_db() as session:
        result = await session.execute(
            select(AIResilienceFlag).where(AIResilienceFlag.id == flag_id)
        )
        flag = result.scalar_one_or_none()
        if not flag:
            return None
        flag.reviewed = True
        await session.flush()
        await session.refresh(flag)
        return flag

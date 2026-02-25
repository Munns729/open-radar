"""
Canon service: get/create/update company canons, audit log, and moat score history.
All functions are async and use get_async_db().
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, desc, and_, update, func

from src.core.database import get_async_db
from src.canon.database import CompanyCanon, CanonEntry, MoatScoreHistory, CanonProposal
from src.universe.database import CompanyModel

logger = logging.getLogger(__name__)

# Fields that require human approval: changes create a CanonProposal instead of direct write.
PROPOSAL_REQUIRED_FIELDS = {"current_tier"}


def _value_to_text(value: Any) -> str | None:
    """Normalize value for comparison and storage in CanonEntry (Text)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


async def get_or_create_canon(company_id: int) -> CompanyCanon:
    """Select by company_id. If not found: create with defaults, add, commit, return. If found: return."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CompanyCanon).where(CompanyCanon.company_id == company_id)
        )
        canon = result.scalar_one_or_none()
        if canon is not None:
            return canon
        canon = CompanyCanon(company_id=company_id)
        session.add(canon)
        await session.flush()
        await session.refresh(canon)
        return canon


async def get_canon(company_id: int) -> CompanyCanon | None:
    """Simple select by company_id, return canon or None."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CompanyCanon).where(CompanyCanon.company_id == company_id)
        )
        return result.scalar_one_or_none()


async def update_canon(
    company_id: int,
    updates: dict,
    source_module: str | None = None,
    triggered_by: str | None = None,
) -> CompanyCanon:
    """
    Get or create canon. For each key/value in updates: if value differs from current,
    insert a CanonEntry. Apply all updates to the Canon row. Commit and return.
    """
    try:
        async with get_async_db() as session:
            result = await session.execute(
                select(CompanyCanon).where(CompanyCanon.company_id == company_id)
            )
            canon = result.scalar_one_or_none()
            if canon is None:
                canon = CompanyCanon(company_id=company_id)
                session.add(canon)
                await session.flush()

            for key, new_val in updates.items():
                if not hasattr(CompanyCanon, key):
                    continue
                # Proposal gate: tier (and other PROPOSAL_REQUIRED_FIELDS) go through queue unless this is an approval.
                if key in PROPOSAL_REQUIRED_FIELDS and source_module != "proposal_approved":
                    current_value = getattr(canon, key, None)
                    if str(_value_to_text(new_val) or "") != str(_value_to_text(current_value) or ""):
                        await create_proposal(
                            company_id=company_id,
                            proposed_field=key,
                            proposed_value=str(_value_to_text(new_val) or ""),
                            current_value=str(current_value) if current_value is not None else None,
                            rationale=f"Proposed by {source_module or 'unknown'}",
                            source_module=source_module,
                            triggered_by=triggered_by,
                        )
                    continue
                current_val = getattr(canon, key, None)
                new_text = _value_to_text(new_val)
                current_text = _value_to_text(current_val)
                if current_text != new_text:
                    entry = CanonEntry(
                        company_id=company_id,
                        field_changed=key,
                        previous_value=current_text,
                        new_value=new_text or "",
                        source_module=source_module,
                        triggered_by=triggered_by,
                    )
                    session.add(entry)
                setattr(canon, key, new_val)

            await session.flush()
            await session.refresh(canon)
            return canon
    except Exception as e:
        logger.error("update_canon failed for company_id=%s: %s", company_id, e)
        raise


async def get_canon_history(company_id: int, limit: int = 50) -> list[CanonEntry]:
    """CanonEntry rows for company_id, ordered by created_at desc, limit."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CanonEntry)
            .where(CanonEntry.company_id == company_id)
            .order_by(desc(CanonEntry.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_recent_changes(limit: int = 20) -> list[CanonEntry]:
    """Across all companies, ordered by created_at desc, limit."""
    async with get_async_db() as session:
        result = await session.execute(
            select(CanonEntry).order_by(desc(CanonEntry.created_at)).limit(limit)
        )
        return list(result.scalars().all())


async def record_moat_score(
    company_id: int,
    pillar: str,
    score: int,
    rationale: str | None = None,
    source: str | None = None,
    triggered_by: str | None = None,
) -> MoatScoreHistory:
    """Insert new MoatScoreHistory row. Never update. Return it."""
    async with get_async_db() as session:
        row = MoatScoreHistory(
            company_id=company_id,
            pillar=pillar,
            score=score,
            rationale=rationale,
            source=source,
            triggered_by=triggered_by,
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return row


async def get_current_moat_scores(company_id: int) -> dict[str, int]:
    """For each distinct pillar, the row with max created_at. Return {pillar: score}."""
    async with get_async_db() as session:
        # Subquery: (company_id, pillar, max(created_at))
        from sqlalchemy import func as fn

        subq = (
            select(
                MoatScoreHistory.company_id,
                MoatScoreHistory.pillar,
                fn.max(MoatScoreHistory.created_at).label("max_created"),
            )
            .where(MoatScoreHistory.company_id == company_id)
            .group_by(MoatScoreHistory.company_id, MoatScoreHistory.pillar)
        ).subquery()

        result = await session.execute(
            select(MoatScoreHistory.pillar, MoatScoreHistory.score).join(
                subq,
                and_(
                    MoatScoreHistory.company_id == subq.c.company_id,
                    MoatScoreHistory.pillar == subq.c.pillar,
                    MoatScoreHistory.created_at == subq.c.max_created,
                ),
            )
        )
        return {row.pillar: row.score for row in result.all()}


async def get_moat_score_history(
    company_id: int,
    pillar: str | None = None,
    limit: int = 50,
) -> list[MoatScoreHistory]:
    """Optional pillar filter. Order by created_at desc."""
    async with get_async_db() as session:
        q = select(MoatScoreHistory).where(MoatScoreHistory.company_id == company_id)
        if pillar is not None:
            q = q.where(MoatScoreHistory.pillar == pillar)
        q = q.order_by(desc(MoatScoreHistory.created_at)).limit(limit)
        result = await session.execute(q)
        return list(result.scalars().all())


async def get_moat_trends(company_id: int) -> dict[str, list]:
    """Return {pillar: [{score, created_at, source}]} ordered oldest-first for sparklines."""
    async with get_async_db() as session:
        result = await session.execute(
            select(MoatScoreHistory)
            .where(MoatScoreHistory.company_id == company_id)
            .order_by(MoatScoreHistory.pillar, MoatScoreHistory.created_at)
        )
        rows = result.scalars().all()
    out: dict[str, list] = {}
    for r in rows:
        if r.pillar not in out:
            out[r.pillar] = []
        out[r.pillar].append({
            "score": r.score,
            "created_at": r.created_at,
            "source": r.source,
        })
    return out


async def mark_stale_canons(stale_days: int = 90) -> int:
    """
    Find all CompanyCanon where last_refreshed_at < now() - timedelta(days=stale_days)
    and coverage_status != "archived". Set coverage_status = "stale". Return count updated.
    """
    cutoff = datetime.utcnow() - timedelta(days=stale_days)
    async with get_async_db() as session:
        stmt = (
            update(CompanyCanon)
            .where(
                and_(
                    CompanyCanon.last_refreshed_at < cutoff,
                    CompanyCanon.coverage_status != "archived",
                )
            )
            .values(coverage_status="stale")
        )
        result = await session.execute(stmt)
        return result.rowcount or 0


async def create_proposal(
    company_id: int,
    proposed_field: str,
    proposed_value: str,
    current_value: str | None = None,
    rationale: str | None = None,
    signals: list | None = None,
    source_module: str | None = None,
    triggered_by: str | None = None,
) -> CanonProposal:
    """
    Create or update a pending proposal for a canon field change.
    If a pending proposal already exists for (company_id, proposed_field), update it; else create new.
    New proposals get expires_at = now() + 14 days.
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(days=14)
    async with get_async_db() as session:
        result = await session.execute(
            select(CanonProposal).where(
                and_(
                    CanonProposal.company_id == company_id,
                    CanonProposal.proposed_field == proposed_field,
                    CanonProposal.status == "pending",
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.proposed_value = proposed_value
            existing.rationale = rationale or existing.rationale
            existing.expires_at = expires_at
            await session.flush()
            await session.refresh(existing)
            return existing
        proposal = CanonProposal(
            company_id=company_id,
            proposed_field=proposed_field,
            current_value=current_value,
            proposed_value=proposed_value,
            rationale=rationale,
            signals=signals,
            source_module=source_module,
            triggered_by=triggered_by,
            status="pending",
            expires_at=expires_at,
        )
        session.add(proposal)
        await session.flush()
        await session.refresh(proposal)
        return proposal


async def approve_proposal(proposal_id: int, reviewer_note: str | None = None) -> CanonProposal:
    """Apply the proposed change via update_canon, then mark proposal approved."""
    async with get_async_db() as session:
        result = await session.execute(select(CanonProposal).where(CanonProposal.id == proposal_id))
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ValueError("Proposal not found")
        if proposal.status != "pending":
            raise ValueError(f"Proposal is not pending (status={proposal.status})")
    # Apply change (own session inside update_canon; source_module=proposal_approved bypasses gate)
    await update_canon(
        proposal.company_id,
        {proposal.proposed_field: proposal.proposed_value},
        source_module="proposal_approved",
        triggered_by=f"proposal_{proposal_id}",
    )
    now = datetime.utcnow()
    async with get_async_db() as session:
        result = await session.execute(select(CanonProposal).where(CanonProposal.id == proposal_id))
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ValueError("Proposal not found")
        proposal.status = "approved"
        proposal.reviewed_at = now
        proposal.reviewer_note = reviewer_note
        await session.flush()
        await session.refresh(proposal)
        return proposal


async def reject_proposal(proposal_id: int, reviewer_note: str | None = None) -> CanonProposal:
    """Mark proposal rejected."""
    async with get_async_db() as session:
        result = await session.execute(select(CanonProposal).where(CanonProposal.id == proposal_id))
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ValueError("Proposal not found")
        proposal.status = "rejected"
        proposal.reviewed_at = datetime.utcnow()
        proposal.reviewer_note = reviewer_note
        await session.flush()
        await session.refresh(proposal)
        return proposal


async def get_pending_proposals(company_id: int | None = None) -> list[CanonProposal]:
    """Return pending, non-expired proposals, optionally filtered by company_id. Order by created_at asc."""
    now = datetime.utcnow()
    async with get_async_db() as session:
        q = select(CanonProposal).where(
            CanonProposal.status == "pending",
            CanonProposal.expires_at > now,
        )
        if company_id is not None:
            q = q.where(CanonProposal.company_id == company_id)
        q = q.order_by(CanonProposal.created_at)
        result = await session.execute(q)
        return list(result.scalars().all())


async def expire_stale_proposals() -> int:
    """Set status = 'auto-expired' for all pending proposals with expires_at < now(). Return count."""
    now = datetime.utcnow()
    async with get_async_db() as session:
        stmt = (
            update(CanonProposal)
            .where(
                and_(
                    CanonProposal.status == "pending",
                    CanonProposal.expires_at < now,
                )
            )
            .values(status="auto-expired")
        )
        result = await session.execute(stmt)
        return result.rowcount or 0


async def get_coverage_manifest() -> list[dict]:
    """
    Join CompanyCanon with CompanyModel on company_id. Group by sector.
    Return list of dicts per sector with company_count, active_count, stale_count,
    tier_breakdown, last_activity, recent_signal_count. Sorted by stale_count desc.
    """
    async with get_async_db() as session:
        # Load all canons with company sector and tier
        q = (
            select(
                CompanyCanon.company_id,
                CompanyCanon.coverage_status,
                CompanyCanon.last_refreshed_at,
                CompanyModel.sector,
                CompanyModel.tier,
            )
            .join(CompanyModel, CompanyCanon.company_id == CompanyModel.id)
        )
        result = await session.execute(q)
        rows = result.all()

        # Build sector -> list of (coverage_status, last_refreshed_at, tier)
        sector_data: dict[str, list[tuple[str, datetime | None, Any]]] = {}
        for r in rows:
            sector = r.sector if r.sector else "Unknown"
            if sector not in sector_data:
                sector_data[sector] = []
            tier_val = r.tier.value if hasattr(r.tier, "value") else str(r.tier) if r.tier else None
            sector_data[sector].append((r.coverage_status, r.last_refreshed_at, tier_val))

        # Recent signal count: CanonEntry in last 30 days per company_id, then map to sector
        signal_cutoff = datetime.utcnow() - timedelta(days=30)
        entry_q = (
            select(CanonEntry.company_id, func.count(CanonEntry.id).label("cnt"))
            .where(CanonEntry.created_at >= signal_cutoff)
            .group_by(CanonEntry.company_id)
        )
        entry_result = await session.execute(entry_q)
        company_signal_counts = {row.company_id: row.cnt for row in entry_result.all()}

        # Company ID -> sector (from same join we already have)
        company_sector: dict[int, str] = {}
        for r in rows:
            sector = r.sector if r.sector else "Unknown"
            company_sector[r.company_id] = sector

        sector_signals: dict[str, int] = {}
        for cid, cnt in company_signal_counts.items():
            sec = company_sector.get(cid, "Unknown")
            sector_signals[sec] = sector_signals.get(sec, 0) + cnt

        # Build manifest per sector
        manifest: list[dict] = []
        tier_keys = ("1A", "1B", "2", "waitlist")
        for sector, items in sector_data.items():
            company_count = len(items)
            active_count = sum(1 for s, _, _ in items if s == "active")
            stale_count = sum(1 for s, _, _ in items if s == "stale")
            tier_breakdown = {k: 0 for k in tier_keys}
            for _, _, t in items:
                if t and t in tier_breakdown:
                    tier_breakdown[t] += 1
            last_dates = [d for _, d, _ in items if d]
            last_activity = max(last_dates).isoformat() if last_dates else ""
            recent_signal_count = sector_signals.get(sector, 0)
            manifest.append({
                "sector": sector,
                "company_count": company_count,
                "active_count": active_count,
                "stale_count": stale_count,
                "tier_breakdown": tier_breakdown,
                "last_activity": last_activity,
                "recent_signal_count": recent_signal_count,
            })
        manifest.sort(key=lambda x: x["stale_count"], reverse=True)
        return manifest

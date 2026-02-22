"""
Scoring program: Graph-free moat scoring, tier assignment, audit trail.
Zone 3b: Moat scoring and tier assignment.
"""
import logging
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from src.core.thesis import thesis
from src.universe.database import CertificationModel, CompanyModel, ScoringEvent
from src.universe.moat_scorer import MoatScorer
from src.universe.ops.filters import PreEnrichmentFilter
from src.universe.pipeline_context import set_analysis_model
from src.universe.status import reporter
from src.universe.tier_monitor import detect_tier_change, TierChangeReport, _parse_tier

logger = logging.getLogger(__name__)


async def run_scoring(
    session,
    min_revenue: Optional[int] = None,
    countries: Optional[List[str]] = None,
    analysis_model: str = "auto",
    limit: Optional[int] = None,
) -> TierChangeReport:
    """
    Moat scoring and tier assignment. No graph analysis or relationship enrichment.
    Returns a TierChangeReport with any tier transitions detected.
    """
    override = analysis_model if analysis_model != "auto" else None
    set_analysis_model(override)

    logger.info("Running Scoring Pipeline...")
    tier_report = TierChangeReport()

    logger.info("=" * 50)
    logger.info("Zone 3b: Scoring & Tier Assignment")
    logger.info("=" * 50)
    reporter.set_zone(3, "Scoring & Tier Assignment")

    from sqlalchemy import nulls_last

    stmt = select(CompanyModel).where(CompanyModel.extraction_complete_at != None).options(
        selectinload(CompanyModel.certifications),
        selectinload(CompanyModel.relationships_as_a),
        selectinload(CompanyModel.relationships_as_b),
    )
    if min_revenue:
        stmt = stmt.where(CompanyModel.revenue_gbp >= min_revenue)
    if countries:
        stmt = stmt.where(CompanyModel.hq_country.in_(countries))
    if limit:
        stmt = stmt.order_by(nulls_last(desc(CompanyModel.last_updated))).limit(limit)
        logger.info(f"Zone 3 limited to {limit} most recently updated companies (testing mode)")

    result = await session.execute(stmt)
    companies = result.scalars().all()

    scoreable = []
    insufficient = []
    for c in companies:
        ok, reason = PreEnrichmentFilter.should_score(c)
        if ok:
            scoreable.append(c)
        else:
            insufficient.append((c, reason))

    # Mark insufficient-data companies explicitly so they don't look like scored-zero.
    # Set moat_score to NULL so the UI/API can distinguish "not scored" from "scored 0".
    for company, reason in insufficient:
        changed = False
        if not isinstance(company.moat_analysis, dict) or company.moat_analysis.get("scoring_status") != "insufficient_data":
            company.moat_analysis = {"scoring_status": "insufficient_data", "reason": reason}
            changed = True
        if company.moat_score is not None and company.moat_score == 0:
            company.moat_score = None
            changed = True
        if changed:
            await session.commit()

    if insufficient:
        logger.info(
            f"Skipping moat scoring for {len(insufficient)} companies "
            "(insufficient data — website text or real description required). "
            "Marked as scoring_status=insufficient_data."
        )

    to_score = scoreable
    logger.info(f"Scoring {len(to_score)} companies...")

    for idx, company in enumerate(to_score):
        result = await session.execute(select(CertificationModel).where(CertificationModel.company_id == company.id))
        certs = result.scalars().all()

        company._previous_tier = company.tier.value if company.tier else None

        raw_website_text = company.raw_website_text or ""
        await MoatScorer.score_with_llm(company, certs, graph_signals=None, raw_website_text=raw_website_text)

        previous_score = getattr(company, '_previous_moat_score', None)
        previous_attrs = getattr(company, '_previous_moat_attributes', None)
        previous_tier_str = getattr(company, '_previous_tier', None)
        old_tier = _parse_tier(previous_tier_str) if previous_tier_str else None

        tier_change = detect_tier_change(
            company_id=company.id,
            company_name=company.name,
            old_tier=old_tier,
            new_tier=company.tier,
            old_score=previous_score,
            new_score=company.moat_score,
            moat_attributes=company.moat_attributes,
        )
        if tier_change:
            tier_report.changes.append(tier_change)

        if (idx + 1) % 25 == 0 or idx == 0:
            logger.info(f"Scored {idx + 1}/{len(to_score)}: {company.name} -> {company.moat_score} ({company.tier.value if company.tier else 'waitlist'})")

        changes = {}
        for pillar in thesis.pillar_names:
            old_s = (previous_attrs or {}).get(pillar, {}).get("score", 0) if isinstance(previous_attrs, dict) else 0
            new_s = (company.moat_attributes or {}).get(pillar, {}).get("score", 0) if isinstance(company.moat_attributes, dict) else 0
            if old_s != new_s:
                changes[pillar] = {
                    "old": old_s,
                    "new": new_s,
                    "delta": new_s - old_s,
                    "old_justification": (previous_attrs or {}).get(pillar, {}).get("justification", "") if isinstance(previous_attrs, dict) else "",
                    "new_justification": (company.moat_attributes or {}).get(pillar, {}).get("justification", "") if isinstance(company.moat_attributes, dict) else "",
                }

        trigger = "initial" if previous_score is None or previous_score == 0 else "rescan"

        event = ScoringEvent(
            company_id=company.id,
            moat_score=company.moat_score,
            tier=company.tier.value if company.tier else "waitlist",
            moat_attributes=company.moat_attributes,
            weights_used=dict(thesis.moat_weights),
            previous_score=previous_score if previous_score else None,
            score_delta=(company.moat_score - previous_score) if previous_score else None,
            changes=changes if changes else None,
            trigger=trigger,
        )
        session.add(event)

        await session.commit()

    tier_report.companies_scored = len(to_score)

    if tier_report.has_changes:
        logger.info(f"Tier changes detected: {len(tier_report.promotions)} promotions, {len(tier_report.demotions)} demotions, {len(tier_report.new_entries)} new entries")

    set_analysis_model(None)
    logger.info("Scoring Complete.")
    return tier_report

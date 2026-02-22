"""
Enrichment program: Batch LLM pillar scoring (semantic enrichment).
Zone 3a: Semantic enrichment.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from src.universe.database import CompanyModel
from src.universe.ops.semantic_enrichment import enrich_companies_batched
from src.universe.ops.filters import PreEnrichmentFilter
from src.universe.programs._shared import build_llm_clients
from src.universe.status import reporter

logger = logging.getLogger(__name__)


async def run_enrichment(
    session,
    min_revenue: Optional[int] = None,
    countries: Optional[List[str]] = None,
    analysis_model: str = "auto",
    limit: Optional[int] = None,
) -> None:
    """
    Semantic enrichment: Batch LLM pillar scoring for companies with raw_website_text
    that have not yet been semantically enriched.
    """
    logger.info("=" * 50)
    logger.info("Zone 3a: Semantic Enrichment")
    logger.info("=" * 50)
    reporter.set_zone(3, "Semantic Enrichment")

    anthropic_client, openai_client, openai_model_override = build_llm_clients(analysis_model)

    stmt = select(CompanyModel).where(CompanyModel.extraction_complete_at != None).options(
        selectinload(CompanyModel.certifications),
    )
    if min_revenue:
        stmt = stmt.where(CompanyModel.revenue_gbp >= min_revenue)
    if countries:
        stmt = stmt.where(CompanyModel.hq_country.in_(countries))
    if limit:
        from sqlalchemy import nulls_last
        stmt = stmt.order_by(nulls_last(desc(CompanyModel.last_updated))).limit(limit)
        logger.info(f"Semantic enrichment limited to {limit} most recently updated companies")

    result = await session.execute(stmt)
    companies = result.scalars().all()

    candidates = [c for c in companies if c.raw_website_text and not c.semantic_enriched_at]
    to_semantic_enrich = [c for c in candidates if PreEnrichmentFilter.should_semantic_enrich(c)[0]]
    skipped_semantic = len(candidates) - len(to_semantic_enrich)
    if skipped_semantic:
        logger.info(
            f"Skipping semantic enrichment for {skipped_semantic} companies "
            "(Zone 2 threshold: min text length, not excluded)"
        )

    if not to_semantic_enrich:
        logger.info("No companies to semantically enrich.")
        return

    logger.info(f"Batch Semantically Enriching {len(to_semantic_enrich)} companies...")
    batch_input = [
        {
            "id": c.id,
            "name": c.name,
            "country": c.hq_country,
            "website_text": c.raw_website_text,
            "description": c.description,
            "certifications": [cert.certification_type for cert in (c.certifications or [])]
        }
        for c in to_semantic_enrich
    ]

    results = await enrich_companies_batched(
        batch_input,
        anthropic_client=anthropic_client,
        openai_client=openai_client,
        openai_model=openai_model_override,
    )

    result_map = {r.company_id: r for r in results}
    for c in to_semantic_enrich:
        res = result_map.get(c.id)
        if res and res.enrichment_successful:
            if not c.moat_analysis or not isinstance(c.moat_analysis, dict):
                c.moat_analysis = {}
            c.moat_analysis["semantic"] = res.to_dict()
            c.semantic_enriched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            logger.info(f"Semantically enriched {c.name}")

    await session.commit()
    logger.info("Semantic enrichment complete.")

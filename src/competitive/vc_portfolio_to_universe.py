"""
Run extraction + moat scoring for companies that appear in VC portfolio holdings.

All VC-sourced companies are now in the universe (companies table) with holdings
in company_vc_holdings. This module runs the universe extraction and moat scoring
pipeline on those companies.

  - run_moat_pipeline_for_vc_portfolio: run extraction + scoring for all companies in holdings.
  - run_enrich_existing_vc_linked: same (alias for "enrich existing" — companies in holdings).
"""
import asyncio
import logging
from typing import Optional

from sqlalchemy import select

from src.competitive.vc_portfolio_models import CompanyVCHoldingModel
from src.universe.database import CompanyModel

logger = logging.getLogger(__name__)


async def _company_ids_from_holdings(limit: Optional[int] = None) -> tuple[list[int], list[int]]:
    """
    Get distinct company_id from company_vc_holdings; split into need-extraction vs already-extracted.
    Returns (ids_for_extraction, ids_for_scoring).
    """
    from src.core.database import get_async_db

    async with get_async_db() as session:
        stmt = select(CompanyVCHoldingModel.company_id).distinct()
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        company_ids = [row[0] for row in result.all()]

        if not company_ids:
            return [], []

        check = await session.execute(
            select(CompanyModel.id, CompanyModel.extraction_complete_at).where(
                CompanyModel.id.in_(company_ids)
            )
        )
        ids_for_extraction = []
        ids_for_scoring = []
        for row in check.all():
            cid, ext_at = row[0], row[1]
            if ext_at is not None:
                ids_for_scoring.append(cid)
            else:
                ids_for_extraction.append(cid)

    return ids_for_extraction, ids_for_scoring


async def run_moat_pipeline_for_vc_portfolio(limit: Optional[int] = None) -> dict:
    """
    Run extraction and moat scoring on all companies that appear in VC portfolio holdings.
    No sync step — companies are created by the scraper. Returns summary dict.
    """
    from src.core.database import get_async_db
    from src.universe.programs.extraction import run_extraction
    from src.universe.programs.scoring import run_scoring

    summary = {"extracted_count": 0, "scored_count": 0}

    ids_for_extraction, ids_for_scoring = await _company_ids_from_holdings(limit=limit)

    async with get_async_db() as session:
        if ids_for_extraction:
            await run_extraction(
                session,
                target_ids=ids_for_extraction,
                limit=len(ids_for_extraction),
                force=True,
            )
            summary["extracted_count"] = len(ids_for_extraction)

        ids_to_score = list(ids_for_scoring) + list(ids_for_extraction)
        if ids_to_score:
            tier_report = await run_scoring(session, company_ids=ids_to_score)
            summary["scored_count"] = tier_report.companies_scored if tier_report else len(ids_to_score)

    return summary


async def run_enrich_existing_vc_linked(limit: Optional[int] = None) -> dict:
    """
    Same as run_moat_pipeline_for_vc_portfolio: run extraction + moat scoring
    on companies that appear in company_vc_holdings. Kept for API/UI compatibility.
    """
    return await run_moat_pipeline_for_vc_portfolio(limit=limit)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run extraction + moat scoring for VC portfolio companies")
    parser.add_argument("--limit", type=int, default=None, help="Max companies to process")
    parser.add_argument("--enrich-existing", action="store_true", help="Same as default (no-op, kept for compatibility)")
    args = parser.parse_args()
    summary = asyncio.run(run_moat_pipeline_for_vc_portfolio(limit=args.limit))
    print("VC moat pipeline complete:", summary)

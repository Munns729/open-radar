"""
Orchestrator for RADAR Universe Pipeline.
Dispatches to independent programs: discovery → extraction → enrichment → scoring.
"""
import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from src.core.database import get_async_db, sync_session_factory
from src.core.models import CompanyTier
from src.universe.database import CompanyModel
from src.universe.ops.cost_tracker import cost_tracker
from src.universe.programs import run_discovery, run_extraction, run_enrichment, run_scoring
from src.universe.programs._shared import init_db, save_companies
from src.universe.status import reporter

# Backward compatibility
SessionLocal = sync_session_factory
enrich_companies = run_extraction
run_scoring_pipeline = run_scoring

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ALL_SOURCES = [
    "AS9100", "ISO9001", "Wikipedia", "Clutch", "GoodFirms", "Crunchbase",
    "CompaniesHouse", "ContractsFinder", "GCloud",
    "SIRENE", "UGAP", "TED", "BOAMP", "ANSSI", "BSI",
    "Deloitte", "FT1000", "Verticals",
]


async def build_universe(
    mode: str = "full",
    sources: list = None,
    min_revenue: int = None,
    countries: list = None,
    force: bool = False,
    limit: int = 15,
    analysis_model: str = "auto",
):
    """
    Modes: discovery | extraction | enrichment | scoring | full
    """
    sources = sources or ALL_SOURCES
    stages = _resolve_stages(mode)

    logger.info(f"RADAR Pipeline — Mode: {mode} | Stages: {stages}")
    reporter.set_active()
    await init_db()

    async with get_async_db() as session:
        try:
            if "discovery" in stages:
                await run_discovery(session, sources, countries=countries, limit=limit)

            if "extraction" in stages:
                print("\n" + "=" * 50)
                print("[PROGRAM] Extraction & Enrichment — Website + data for scoring")
                print("=" * 50 + "\n")
                await run_extraction(
                    session,
                    min_revenue=min_revenue,
                    countries=countries,
                    force=force,
                    limit=limit,
                )

            if "enrichment" in stages:
                await run_enrichment(
                    session,
                    min_revenue=min_revenue,
                    countries=countries,
                    analysis_model=analysis_model,
                    limit=limit,
                )

            tier_report = None
            if "scoring" in stages:
                tier_report = await run_scoring(
                    session,
                    min_revenue=min_revenue,
                    countries=countries,
                    analysis_model=analysis_model,
                    limit=limit,
                )

            await _print_summary(session, tier_report)

        except Exception as e:
            import traceback
            logger.error(f"Workflow failed: {e}\n{traceback.format_exc()}")
            reporter.state["status"] = "error"
            raise


def _resolve_stages(mode: str) -> list[str]:
    if mode == "full":
        return ["discovery", "extraction", "enrichment", "scoring"]
    elif mode in ("discovery", "extraction", "enrichment", "scoring"):
        return [mode]
    else:
        raise ValueError(f"Unknown mode: {mode}")


async def _print_summary(session, tier_report):
    """Print tier counts, cost reporting, and tier changes."""
    result = await session.execute(select(func.count(CompanyModel.id)))
    total = result.scalar() or 0

    result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_1A))
    tier1a = result.scalar() or 0

    result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_1B))
    tier1b = result.scalar() or 0

    result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_2))
    tier2 = result.scalar() or 0

    print("\n--- RADAR UNIVERSE STATUS ---")
    print(f"Total Companies: {total}")
    print(f"Tier 1A (Permanent Moats): {tier1a}")
    print(f"Tier 1B (Strong Defensibility): {tier1b}")
    print(f"Tier 2 (Opportunistic): {tier2}")
    print(f"Total Session Cost: ${cost_tracker.get_total_cost():.4f}")

    if tier_report and tier_report.has_changes:
        print("\n--- TIER CHANGES ---")
        for change in tier_report.changes:
            print(f"  {change.summary()}")

        tier_md = tier_report.render_markdown()
        tier_path = Path("outputs") / f"tier_changes_{datetime.now():%Y%m%d_%H%M%S}.md"
        tier_path.parent.mkdir(exist_ok=True)
        tier_path.write_text(tier_md)
        print(f"\nTier change report saved to {tier_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Universe pipeline: discovery | extraction | enrichment | scoring | full"
    )
    parser.add_argument(
        "--mode",
        default="full",
        choices=["discovery", "extraction", "enrichment", "scoring", "full"],
        help="discovery=scrapers only; extraction=website+enrichment; enrichment=semantic; scoring=moat+tier; full=all four",
    )
    parser.add_argument("--min-revenue", type=int, default=None, help="Minimum revenue in GBP")
    parser.add_argument("--countries", nargs="+", help="List of country codes to process (e.g. FR DE)")
    parser.add_argument("--sources", nargs="+", help="Discovery sources (AS9100, ISO9001, Wikipedia, etc.)")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if recently updated")
    parser.add_argument("--limit", type=int, default=15, help="Number of companies per source/region (discovery) or to process (extraction/enrichment/scoring)")
    parser.add_argument("--analysis-model", choices=["auto", "ollama", "moonshot"], default="auto", help="LLM for semantic enrichment + moat scoring")
    args = parser.parse_args()

    asyncio.run(
        build_universe(
            args.mode,
            args.sources,
            args.min_revenue,
            args.countries,
            args.force,
            args.limit,
            args.analysis_model,
        )
    )

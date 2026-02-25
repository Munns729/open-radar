"""
RADAR Pipeline — unified discovery, enrichment, scoring, and briefing.

Single entry point for the full investment intelligence cycle:

  Daily mode (default):
    1. Discovery (optional --full)
    2. Enrich  — fill in missing data for companies in the universe
    3. Score   — (re)score all companies against the active thesis
    4. Detect  — identify tier changes (promotions, demotions, new entries)
    5. Brief   — generate a markdown intelligence briefing

  Overnight mode (--duration N):
    Phase 0: Discovery + enrichment in alternating rounds for N hours (Qwen3 8B)
    Phase 1–4: Enrich (top-up) → Score → Tier → Brief

Usage:
  python scripts/canonical/run_daily_pipeline.py
  python scripts/canonical/run_daily_pipeline.py --skip-enrich
  python scripts/canonical/run_daily_pipeline.py --full  # include discovery
  python scripts/canonical/run_daily_pipeline.py --duration 5  # overnight mode
  python scripts/canonical/run_daily_pipeline.py --duration 5 --analysis-model ollama  # 100% local (cost)

Models: Browsing (discovery/enrichment) uses BROWSING_MODEL + OPENAI_API_BASE (Ollama).
Analysis (semantic enrichment + moat scoring) uses --analysis-model: auto (Moonshot if key set), ollama, or moonshot.
The pipeline is idempotent — safe to run multiple times per day.
Companies enriched within the last 7 days are skipped unless --force.
"""
import sys
import os
sys.path.append(os.getcwd())

import asyncio
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/daily_pipeline.log", mode="a"),
    ],
)
logger = logging.getLogger("radar.daily_pipeline")

# Overnight mode constants
DISCOVERY_BATCH = 6
ENRICHMENT_BATCH = 18
CHECK_INTERVAL_MIN = 15
STATIC_SOURCES = {"AS9100", "ISO9001", "Wikipedia", "Clutch", "GoodFirms", "Crunchbase", "Deloitte", "FT1000", "Verticals"}


def _get_all_sources():
    return [
        "AS9100", "ISO9001", "Wikipedia", "Clutch", "GoodFirms", "Crunchbase",
        "CompaniesHouse", "ContractsFinder", "GCloud",
        "SIRENE", "UGAP", "TED", "BOAMP", "ANSSI", "BSI",
        "Deloitte", "FT1000", "Verticals",
    ]


async def _run_discovery_round(session, sources_batch, limit, countries, round_num, sources_run_once):
    """Run discovery for a batch of sources (overnight mode)."""
    from src.universe.programs._shared import save_companies
    from src.universe.scrapers import (
        AS9100Scraper, ISORegistryScraper, WikipediaDiscoveryScraper,
        ClutchDiscoveryScraper, CrunchbaseDiscoveryScraper,
        CompaniesHouseDiscoveryScraper, ContractsFinderScraper, SIRENEScraper,
    )
    from src.universe.scrapers.goodfirms_discovery import GoodFirmsDiscoveryScraper
    from src.universe.scrapers.g_cloud_scraper import GCloudScraper
    from src.universe.scrapers.ugap_scraper import UGAPScraper
    from src.universe.scrapers.ted_scraper import TEDScraper
    from src.universe.scrapers.boamp_scraper import BOAMPScraper
    from src.universe.scrapers.anssi_scraper import ANSSIScraper
    from src.universe.scrapers.bsi_scraper import BSIScraper
    from src.universe.scrapers.growth_scrapers import DeloitteFast50Scraper, FT1000Scraper
    from src.universe.scrapers.vertical_associations_scraper import VerticalAssociationsScraper

    target_countries = countries or ["FR", "DE", "NL", "BE", "GB"]
    total_saved = 0
    ch_offset = (round_num - 1) * 50
    sirene_page = 1 + (round_num - 1) * 2
    boamp_offset = (round_num - 1) * 30
    ted_page = 1 + (round_num - 1)

    for source in sources_batch:
        if source in STATIC_SOURCES and source in sources_run_once:
            logger.info(f"Skipping {source} (static source, already run this session)")
            continue
        try:
            if source == "AS9100":
                sources_run_once.add(source)
                async with AS9100Scraper() as scraper:
                    data = await scraper.scrape_by_country("United Kingdom")
                    n = await save_companies(session, data.data[:limit], "AS9100")
                    total_saved += n
            elif source == "ISO9001":
                sources_run_once.add(source)
                async with ISORegistryScraper() as scraper:
                    data = await scraper.scrape_iso9001()
                    n = await save_companies(session, data.data[:limit], "ISO9001")
                    total_saved += n
            elif source == "Wikipedia":
                sources_run_once.add(source)
                async with WikipediaDiscoveryScraper() as scraper:
                    for code in target_countries[:2]:
                        if code in ["FR", "DE", "NL", "BE"]:
                            data = await scraper.discover_region(code, limit=limit)
                            n = await save_companies(session, data.data, f"Wiki-Discovery-{code}")
                            total_saved += n
            elif source == "Clutch":
                sources_run_once.add(source)
                async with ClutchDiscoveryScraper() as scraper:
                    for code in target_countries[:2]:
                        if code in ["FR", "DE", "UK", "NL", "PL"]:
                            data = await scraper.discover_tech_services(code, limit=limit)
                            n = await save_companies(session, data.data, f"Clutch-Discovery-{code}")
                            total_saved += n
            elif source == "GoodFirms":
                sources_run_once.add(source)
                async with GoodFirmsDiscoveryScraper(headless=True) as scraper:
                    for term in ["Cybersecurity", "Artificial Intelligence"]:
                        data = await scraper.discover(term=term, country="France", limit=limit)
                        n = await save_companies(session, data.data, f"GoodFirms-FR-{term}")
                        total_saved += n
            elif source == "Crunchbase":
                sources_run_once.add(source)
                async with CrunchbaseDiscoveryScraper() as scraper:
                    data = await scraper.discover_companies("UK", limit=limit)
                    n = await save_companies(session, data.data, f"Crunchbase-UK")
                    total_saved += n
            elif source == "CompaniesHouse":
                async with CompaniesHouseDiscoveryScraper() as scraper:
                    data = await scraper.scrape(limit=max(limit, 30), start_index=ch_offset)
                    n = await save_companies(session, data.data, "CompaniesHouse-UK")
                    total_saved += n
            elif source == "ContractsFinder":
                async with ContractsFinderScraper() as scraper:
                    data = await scraper.scrape(limit=max(limit, 20))
                    n = await save_companies(session, data.data, "ContractsFinder-UK")
                    total_saved += n
            elif source == "SIRENE":
                async with SIRENEScraper() as scraper:
                    data = await scraper.scrape(limit=max(limit, 30), page_start=sirene_page)
                    n = await save_companies(session, data.data, "SIRENE-FR")
                    total_saved += n
            elif source == "GCloud":
                async with GCloudScraper() as scraper:
                    data = await scraper.scrape(target_lots=["cloud-support"], limit_per_lot=limit)
                    n = await save_companies(session, data.data, "G-Cloud-UK")
                    total_saved += n
            elif source == "UGAP":
                async with UGAPScraper() as scraper:
                    data = await scraper.scrape(limit=limit)
                    n = await save_companies(session, data.data, "UGAP-FR")
                    total_saved += n
            elif source == "TED":
                async with TEDScraper() as scraper:
                    data = await scraper.scrape(countries=target_countries[:3], limit_per_country=limit, page_start=ted_page)
                    n = await save_companies(session, data.data, "TED-EU")
                    total_saved += n
            elif source == "BOAMP":
                async with BOAMPScraper() as scraper:
                    data = await scraper.scrape(limit=max(limit, 15), offset=boamp_offset)
                    n = await save_companies(session, data.data, "BOAMP-FR")
                    total_saved += n
            elif source == "ANSSI":
                async with ANSSIScraper(headless=True) as scraper:
                    data = await scraper.scrape(limit=max(limit, 20))
                    n = await save_companies(session, data.data, "ANSSI-FR")
                    total_saved += n
            elif source == "BSI":
                async with BSIScraper() as scraper:
                    data = await scraper.scrape(limit=max(limit, 30))
                    n = await save_companies(session, data.data, "BSI-DE")
                    total_saved += n
            elif source == "Deloitte":
                sources_run_once.add(source)
                async with DeloitteFast50Scraper() as scraper:
                    data = await scraper.scrape(region="UK")
                    data_list = data if isinstance(data, list) else getattr(data, "data", [])
                    n = await save_companies(session, data_list[:limit], "DeloitteFast50-UK")
                    total_saved += n
            elif source == "FT1000":
                sources_run_once.add(source)
                async with FT1000Scraper() as scraper:
                    data = await scraper.scrape()
                    data_list = data if isinstance(data, list) else getattr(data, "data", [])
                    n = await save_companies(session, data_list[:limit], "FT1000-Europe")
                    total_saved += n
            elif source == "Verticals":
                sources_run_once.add(source)
                async with VerticalAssociationsScraper() as scraper:
                    data = await scraper.scrape()
                    data_list = data if isinstance(data, list) else getattr(data, "data", [])
                    n = await save_companies(session, data_list[:limit], "VerticalAssocs")
                    total_saved += n
        except Exception as e:
            logger.warning(f"Discovery source {source} failed: {e}", exc_info=True)
        await session.commit()
    return total_saved


async def _run_overnight_loop(session, duration_hours, discovery_batch, enrichment_batch, check_interval_min, countries):
    """Discovery + enrichment in alternating rounds until time limit."""
    from src.universe.programs.extraction import run_extraction

    end_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
    last_checkin = datetime.now(timezone.utc)
    round_num = 0
    total_discovered = 0
    total_enriched = 0
    all_sources = _get_all_sources()
    sources_run_once = set()

    logger.info("=" * 60)
    logger.info(f"Phase 0: Overnight Discovery + Enrichment — {duration_hours}h | Batches: D={discovery_batch} E={enrichment_batch}")
    logger.info(f"End time: {end_time:%Y-%m-%d %H:%M} UTC")
    logger.info("=" * 60)

    while datetime.now(timezone.utc) < end_time:
        round_num += 1
        round_start = datetime.now(timezone.utc)
        offset = (round_num - 1) * 4 % len(all_sources)
        batch_sources = [all_sources[(offset + i) % len(all_sources)] for i in range(4)]

        logger.info(f"[Round {round_num}] Discovery: {batch_sources}")
        discovered = await _run_discovery_round(
            session, batch_sources, limit=discovery_batch, countries=countries,
            round_num=round_num, sources_run_once=sources_run_once,
        )
        total_discovered += discovered

        logger.info(f"[Round {round_num}] Enrichment batch ({enrichment_batch} companies)")
        await run_extraction(
            session, min_revenue=None, countries=countries, force=False, limit=enrichment_batch,
        )
        total_enriched += enrichment_batch

        now = datetime.now(timezone.utc)
        if (now - last_checkin).total_seconds() >= check_interval_min * 60:
            elapsed = (now - round_start).total_seconds()
            remaining = (end_time - now).total_seconds() / 3600
            logger.info(
                f"[CHECK-IN] Round {round_num} | Discovered: {total_discovered} | "
                f"Enriched: ~{total_enriched} | Round took {elapsed:.0f}s | ~{remaining:.1f}h remaining"
            )
            last_checkin = now

        await asyncio.sleep(5)

    logger.info("=" * 60)
    logger.info("Phase 0 complete (time limit reached)")
    logger.info(f"Rounds: {round_num} | Discovered: {total_discovered} | Enriched: ~{total_enriched}")
    logger.info("=" * 60)


async def run_pipeline(
    skip_enrich: bool = False,
    skip_scoring: bool = False,
    skip_briefing: bool = False,
    include_discovery: bool = False,
    duration_hours: float = 0,
    countries: list = None,
    min_revenue: int = None,
    force: bool = False,
    limit: int = 15,
    sources: list = None,
    discovery_batch: int = DISCOVERY_BATCH,
    enrichment_batch: int = ENRICHMENT_BATCH,
    check_interval_min: int = CHECK_INTERVAL_MIN,
    analysis_model: str = "auto",
):
    """
    Main pipeline entrypoint.
    """
    from src.core.database import get_async_db
    from src.universe.programs._shared import init_db
    from src.universe.programs.extraction import run_extraction
    from src.universe.programs.enrichment import run_enrichment
    from src.universe.programs.scoring import run_scoring
    from src.universe.tier_monitor import TierChangeReport
    from src.universe.ops.cost_tracker import cost_tracker

    start = datetime.now()
    overnight_mode = duration_hours > 0
    logger.info("=" * 60)
    logger.info(f"RADAR Pipeline — {start:%Y-%m-%d %H:%M}" + (f" (overnight {duration_hours}h)" if overnight_mode else ""))
    logger.info("=" * 60)

    # Log model selection
    from src.core.config import settings
    browsing = f"{settings.browsing_model} (Ollama)" if "11434" in (settings.openai_api_base or "") else settings.browsing_model
    if analysis_model != "auto":
        analysis = analysis_model
    else:
        analysis = "Moonshot" if settings.moonshot_api_key else ("Anthropic" if settings.anthropic_api_key else "Ollama")
    logger.info(f"Models: Browsing={browsing} | Analysis={analysis}")

    Path("logs").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)

    await init_db()

    tier_report = TierChangeReport()

    async with get_async_db() as session:
        # ── Phase 0: Overnight discovery + enrichment (optional) ──
        if overnight_mode:
            await _run_overnight_loop(
                session,
                duration_hours=duration_hours,
                discovery_batch=discovery_batch,
                enrichment_batch=enrichment_batch,
                check_interval_min=check_interval_min,
                countries=countries,
            )

        # ── Phase 1: Discovery (optional, daily mode only) ─────────
        if overnight_mode:
            logger.info("Phase 1: Discovery -- skipped (overnight mode)")
        elif include_discovery:
            logger.info("Phase 1: Discovery")
            from src.universe.programs.discovery import run_discovery
            disc_sources = sources or _get_all_sources()
            await run_discovery(session, disc_sources, countries=countries, limit=limit)
        else:
            logger.info("Phase 1: Discovery -- skipped (use --full to include)")

        # ── Phase 2: Extraction (top-up batch) ─────────────────────
        if not skip_enrich:
            logger.info("Phase 2: Extraction")
            await run_extraction(
                session,
                min_revenue=min_revenue,
                countries=countries,
                force=force,
                limit=200,
            )
        else:
            logger.info("Phase 2: Extraction -- skipped")

        # ── Phase 3: Enrichment + Scoring ──────────────────────────
        if not skip_scoring:
            logger.info("Phase 3: Semantic Enrichment")
            await run_enrichment(
                session,
                min_revenue=min_revenue,
                countries=countries,
                analysis_model=analysis_model,
            )
            logger.info("Phase 3: Scoring")
            tier_report = await run_scoring(
                session,
                min_revenue=min_revenue,
                countries=countries,
                analysis_model=analysis_model,
            )
        else:
            logger.info("Phase 3: Enrichment + Scoring -- skipped")

    # ── Phase 4: Tier Change Report ───────────────────────────
    logger.info("Phase 4: Tier Changes")
    if tier_report.has_changes:
        tier_md = tier_report.render_markdown()
        tier_path = Path("outputs") / f"tier_changes_{start:%Y%m%d}.md"
        tier_path.write_text(tier_md)

        logger.info("=" * 50)
        logger.info("TIER CHANGES DETECTED")
        logger.info("=" * 50)
        for change in tier_report.changes:
            logger.info(f"  {change.summary()}")
        logger.info(f"Full report: {tier_path}")

        if tier_report.notable_changes:
            logger.info(f"** {len(tier_report.notable_changes)} NOTABLE (Tier 1A/1B entries):")
            for nc in tier_report.notable_changes:
                logger.info(f"  * {nc.company_name} -> Tier {nc.new_tier} (score {nc.new_score})")
    else:
        logger.info("No tier changes detected.")

    # ── Phase 5: Briefing ─────────────────────────────────────
    if not skip_briefing:
        logger.info("Phase 5: Market Briefing")
        try:
            briefing = await _run_briefing(tier_report)
            if briefing:
                logger.info(f"Briefing saved to outputs/briefing_{briefing.week_starting}.md")
                logger.info(f"Also available at: outputs/latest_briefing.md")
        except Exception as e:
            logger.warning(f"Briefing generation failed (non-fatal): {e}")
    else:
        logger.info("Phase 5: Briefing -- skipped")

    # ── Summary ───────────────────────────────────────────────
    elapsed = datetime.now() - start
    logger.info("=" * 50)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Duration:     {elapsed.total_seconds():.0f}s")
    logger.info(f"Scored:       {tier_report.companies_scored} companies")
    logger.info(f"Tier changes: {len(tier_report.changes)}")
    logger.info(f"Promotions:   {len(tier_report.promotions)}")
    logger.info(f"LLM cost:     ${cost_tracker.get_total_cost():.4f}")
    logger.info("=" * 50)

    return tier_report


async def _run_briefing(tier_report):
    """Generate the market briefing with tier change context injected."""
    from src.market_intelligence.workflow import generate_market_briefing

    briefing = await generate_market_briefing()
    
    # Append tier changes to outputs/latest_briefing.md if there were changes
    latest_briefing = Path("outputs") / "latest_briefing.md"
    if tier_report.has_changes and latest_briefing.exists():
        existing = latest_briefing.read_text()
        tier_section = "\n\n---\n\n" + tier_report.render_markdown()
        latest_briefing.write_text(existing + tier_section)

    return briefing


def main():
    parser = argparse.ArgumentParser(
        description="RADAR Pipeline — unified discovery, enrichment, scoring, briefing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Include discovery phase (new company sourcing)",
    )
    parser.add_argument(
        "--skip-enrich", action="store_true",
        help="Skip enrichment, go straight to scoring",
    )
    parser.add_argument(
        "--skip-scoring", action="store_true",
        help="Skip scoring (useful if you only want enrichment)",
    )
    parser.add_argument(
        "--skip-briefing", action="store_true",
        help="Skip briefing generation",
    )
    parser.add_argument(
        "--countries", nargs="+", default=None,
        help="Country codes to process (e.g. GB FR DE)",
    )
    parser.add_argument(
        "--min-revenue", type=int, default=None,
        help="Minimum revenue filter (GBP)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-enrichment even for recently updated companies",
    )
    parser.add_argument(
        "--limit", type=int, default=15,
        help="Companies per discovery source (default 15)",
    )
    parser.add_argument(
        "--sources", nargs="+", default=None,
        help="Discovery sources (Wikipedia, Clutch, etc.)",
    )
    parser.add_argument(
        "--duration", type=float, default=0,
        help="Overnight mode: run discovery + enrichment for N hours, then score + tier + brief",
    )
    parser.add_argument(
        "--discovery-batch", type=int, default=DISCOVERY_BATCH,
        help="Companies per discovery source in overnight mode",
    )
    parser.add_argument(
        "--enrichment-batch", type=int, default=ENRICHMENT_BATCH,
        help="Enrichment batch size in overnight mode",
    )
    parser.add_argument(
        "--check-interval", type=int, default=CHECK_INTERVAL_MIN,
        help="Check-in log interval (minutes) in overnight mode",
    )
    parser.add_argument(
        "--analysis-model", choices=["auto", "ollama", "moonshot"], default="auto",
        help="LLM for semantic enrichment + moat scoring: auto (Moonshot if key set), ollama (cost), moonshot (quality)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_pipeline(
            skip_enrich=args.skip_enrich,
            skip_scoring=args.skip_scoring,
            skip_briefing=args.skip_briefing,
            include_discovery=args.full,
            duration_hours=args.duration,
            countries=args.countries,
            min_revenue=args.min_revenue,
            force=args.force,
            limit=args.limit,
            sources=args.sources,
            discovery_batch=args.discovery_batch,
            enrichment_batch=args.enrichment_batch,
            check_interval_min=args.check_interval,
            analysis_model=args.analysis_model,
        )
    )


if __name__ == "__main__":
    main()

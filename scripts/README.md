# RADAR Scripts Reference

## Canonical Scripts (Use These)

All standard operations live here. These are the scripts you run day-to-day.

| Task | Script | Example |
|------|--------|---------|
| Discover new companies | `canonical/comprehensive_discovery.py` | `python scripts/canonical/comprehensive_discovery.py` |
| Bootstrap universe from scratch | `canonical/bootstrap_universe.py` | `python scripts/canonical/bootstrap_universe.py` |
| Enrich existing companies | `canonical/enrich_companies.py` | `python scripts/canonical/enrich_companies.py` |
| General enrichment | `canonical/enrich_general.py` | `python scripts/canonical/enrich_general.py` |
| Re-score all moats | `canonical/force_rescore.py` | `python scripts/canonical/force_rescore.py` |
| Backfill scoring data | `canonical/backfill_scoring_data.py` | `python scripts/canonical/backfill_scoring_data.py` |
| Run daily pipeline | `canonical/run_daily_pipeline.py` | `python scripts/canonical/run_daily_pipeline.py` |
| Run market intel scan | `canonical/run_intel_scan.py` | `python scripts/canonical/run_intel_scan.py` |
| Run investigation | `canonical/run_investigation.py` | `python scripts/canonical/run_investigation.py` |
| Run trend detection | `canonical/run_trend_detection.py` | `python scripts/canonical/run_trend_detection.py` |
| Generate weekly briefing | `canonical/generate_weekly_briefing.py` | `python scripts/canonical/generate_weekly_briefing.py` |
| Generate report | `canonical/generate_report_only.py` | `python scripts/canonical/generate_report_only.py` |
| Health check | `canonical/health_check.py` | `python scripts/canonical/health_check.py` |
| Set up LinkedIn auth | `canonical/setup_linkedin_auth.py` | `python scripts/canonical/setup_linkedin_auth.py` |
| Run public server | `canonical/run_public.py` | `python scripts/canonical/run_public.py` |
| Run agent scraper | `canonical/run_agent_scraper.py` | `python scripts/canonical/run_agent_scraper.py` |
| **Unified pipeline** | `canonical/run_daily_pipeline.py` | `python scripts/canonical/run_daily_pipeline.py` |

## Pipeline / Scheduled Execution

```bash
# Daily: enrich + score + tier + brief
python scripts/canonical/run_daily_pipeline.py

# Overnight: discovery + enrichment for 5h, then score + tier + brief
python scripts/canonical/run_daily_pipeline.py --duration 5

# Skip enrichment (e.g. after overnight run)
python scripts/canonical/run_daily_pipeline.py --skip-enrich
```

For cron/Task Scheduler: see **[setup_overnight_cron.md](setup_overnight_cron.md)**.

Logs: `logs/daily_pipeline.log`

## Other Directories (Private / gitignored)

- **one_off/** — Ad-hoc scripts for specific firms, batches, or data fixes. May have hardcoded names or batch sizes.
- **debug/** — Read-only inspection scripts for checking data, scrapers, and DB state. Should never modify data.
- **migrations/** — Database schema changes and data restructuring (use Alembic for new migrations).
- **seeding/** — Scripts to populate the database with initial or test data.
- **validation/** — Verification scripts to test data quality and system integrity.

## Database

All scripts use PostgreSQL (no SQLite). Ensure `docker-compose up -d` is running before executing any script.

- Module code uses **async** sessions via `async_session_factory` / `get_db` / `get_async_db`
- Scripts use **sync** sessions via `sync_session_factory` / `get_sync_db`

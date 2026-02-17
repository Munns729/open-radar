# RADAR Scripts Reference

## Canonical Scripts (Use These)

| Task | Script | Example |
|------|--------|---------|
| Discover new companies | `canonical/comprehensive_discovery.py` | `python scripts/canonical/comprehensive_discovery.py` |
| Bootstrap universe from scratch | `canonical/bootstrap_universe.py` | `python scripts/canonical/bootstrap_universe.py` |
| Enrich existing companies | `canonical/enrich_companies.py` | `python scripts/canonical/enrich_companies.py` |
| General enrichment | `canonical/enrich_general.py` | `python scripts/canonical/enrich_general.py` |
| Re-score all moats | `canonical/force_rescore.py` | `python scripts/canonical/force_rescore.py` |
| Backfill scoring data | `canonical/backfill_scoring_data.py` | `python scripts/canonical/backfill_scoring_data.py` |
| Run market intel scan | `canonical/run_intel_scan.py` | `python scripts/canonical/run_intel_scan.py` |
| Run investigation | `canonical/run_investigation.py` | `python scripts/canonical/run_investigation.py` |
| Run trend detection | `canonical/run_trend_detection.py` | `python scripts/canonical/run_trend_detection.py` |
| Generate report | `canonical/generate_report_only.py` | `python scripts/canonical/generate_report_only.py` |
| Health check | `canonical/health_check.py` | `python scripts/canonical/health_check.py` |
| Set up LinkedIn auth | `canonical/setup_linkedin_auth.py` | `python scripts/canonical/setup_linkedin_auth.py` |
| Run public server | `canonical/run_public.py` | `python scripts/canonical/run_public.py` |
| Run agent scraper | `canonical/run_agent_scraper.py` | `python scripts/canonical/run_agent_scraper.py` |

## Other Directories (Private)

These directories are gitignored in the open-source release. Create them locally
for your own deal-specific scripts:

- **one_off/**: Ad-hoc scripts for specific firms, batches, or data fixes.
- **debug/**: Inspection scripts for checking data, scrapers, and DB state.
- **migrations/**: Database schema changes and data restructuring.
- **seeding/**: Scripts to populate the database with initial or test data.
- **validation/**: Verification scripts to test data quality and system integrity.

## Important Notes

- Always use canonical/ scripts for standard operations
- one_off/ scripts may have hardcoded firm names or batch sizes — review before reuse
- debug/ scripts are read-only inspection tools — they should never modify data

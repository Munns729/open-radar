# RADAR Agent Interface Guide

This document is designed to help AI agents (like yourself) navigate, understand, and control the RADAR (Real-time Automated Discovery & Analysis for Relevance) system.

## 1. System Overview
RADAR is an investment intelligence platform that automates the "top of the funnel" for Private Equity. It discovers companies, analyzes their defensibility (Moats), tracks competitive activity, and identifies divestiture (Carveout) opportunities.

## 2. Capability Manifest

| Capability | Module | Description | Entry Point |
| :--- | :--- | :--- | :--- |
| **Discovery** | `universe` | Find new companies via scrapers (no website discovery) | `python -m src.universe.workflow --mode discovery` |
| **Moat Scoring** | `universe` | Analyze company defensibility (configurable pillars) | `src.universe.moat_scorer.MoatScorer` |
| **VC Tracking** | `competitive` | Monitor VC LinkedIn/Websites for threats | `python -m src.competitive.workflow` |
| **Carveout Analysis**| `carveout` | Detect corporate spin-off signals | `python -m src.carveout.workflow` |
| **PE Tracking** | `capital` | Map PE firm portfolios and dry powder | `python -m src.capital.workflow` |
| **Deal Intelligence** | `deal_intelligence`| Valuation comparables and probability scoring | `python -m src.deal_intelligence.workflow` |
| **Market Intelligence** | `market_intelligence` | Trend detection, news aggregation, weekly briefings | `python -m src.market_intelligence.workflow` |
| **CRM** | `relationships`| Manage contacts and network strength | `src.relationships.database.Contact` |
| **Target Tracker** | `tracker` | Monitor specific companies for events and alerts | `src.tracker.workflow` (if exists) or `src.tracker` API |
| **Reporting** | `reporting` | HTML/Excel report generation | `python -m src.reporting` |
| **Alerts** | `alerts` | Alert engine + notification channels | `src.alerts.alert_engine.AlertEngine` |
| **Thesis Validator** | `web` + `capital` | Company fit analysis + market hypothesis validation | `GET /api/thesis/*` (UI: `/thesis`) |

## 3. Thesis Configuration

All investment thesis parameters (moat dimensions, weights, tier thresholds, certification scores,
LLM prompts, business filters) are loaded from `config/thesis.yaml`. The config is read once at
startup by `src/core/thesis.py` and exposed as the `thesis_config` singleton.

- **Config file**: `config/thesis.yaml` (gitignored — proprietary)
- **Example**: `config/thesis.example.yaml` (committed — generic starting point)
- **Loader**: `src/core/thesis.py` → `thesis_config` singleton
- **Env var**: `THESIS_CONFIG_PATH` overrides the default path
- **API**: `GET /api/config/thesis` returns the active thesis summary

To change scoring behavior, edit the YAML — no code changes needed.

## 4. Database Skill Map (SQL Reference)
The database runs on PostgreSQL (`docker-compose up -d`).

### Universe (Core Funnel)
- `companies`: The main table for all discovered entities. Key fields: `moat_score` (nullable; NULL when insufficient data — see `moat_analysis.scoring_status`), `tier`, `revenue_gbp`.
- `certifications`: Quality signals (AS9100, etc.) linked to companies.
- `company_relationships`: Graph edges between companies (Customer, Supplier, Competitor).

### Deal Intelligence (Analytics)
- `deal_records`: Historical PE transactions with valuation multiples.
- `deal_comparables`: Links between deals showing similarity scores.
- `market_metrics`: Sector-level aggregates (median multiples, deal volume).
- `deal_probabilities`: Probability of a company transacting in next 6-12 months.

### Market Intelligence (Trends)
- `intelligence_items`: News articles, RSS feed items, and regulatory updates.
- `market_trends`: Identified macro trends (e.g., "AI Regulation").
- `weekly_briefings`: Generated executive summaries of market activity.
- `news_sources`: Configured RSS feeds and scrapers.

### Capital (The Money)
- `pe_firms`: Private Equity firms and their strategies.
- `pe_investments`: Portfolio companies held by PE firms.

### Carveout (Divestitures)
- `corporate_parents`: Large corporations (e.g., Unilever).
- `divisions`: Business units that could be carved out.
- `carveout_signals`: Intelligence hits (e.g., "Strategic Review").

### Competitive (The Bench)
- `vc_announcements`: Recent funding rounds tracked from VCs.
- `threat_scores`: Analysis of how VC rounds impact our thesis or targets.

### Tracker (Monitoring)
- `tracked_companies`: Companies specifically watchlisted for updates.
- `company_events`: Detected events (Funding, Leadership Change, etc.).
- `tracking_alerts`: Generated alerts for user review.
- `company_notes`: User-created research notes.

### Relationships (CRM)
- `contacts`: People database (Founders, Investors, Advisors).
- `interactions`: Log of emails, calls, and meetings.
- `network_connections`: Graph of who knows whom.

## 4. Entry Point Cheat Sheet

### Build/Update Universe
Four programs (run independently or in sequence). Orchestrator: `src/universe/workflow.py`; implementations: `src/universe/programs/`.
```bash
# Discovery: Scrapers only — descriptions, revenue, sector (no website discovery)
python -m src.universe.workflow --mode discovery

# Extraction: Website + CH/OC + LLM enrichment — runs on companies not yet extraction-complete
python -m src.universe.workflow --mode extraction

# Enrichment: Batch semantic (LLM pillar) enrichment — runs on extraction-complete companies with raw_website_text
python -m src.universe.workflow --mode enrichment

# Scoring: Moat scoring + tier assignment (no graph) — runs on extraction-complete companies
python -m src.universe.workflow --mode scoring

# Full pipeline: discovery -> extraction -> enrichment -> scoring
python -m src.universe.workflow --mode full
```

### Run Intelligence Analytics
```bash
# Run full deal intelligence (enrichment + metrics + scoring)
python -m src.deal_intelligence.workflow

# Run daily market intelligence scan
python -m src.market_intelligence.workflow
```

### Generate Reports
```bash
# Generate HTML report for Tier 1A companies
python -m src.reporting --format html --tier 1A
```

## 5. Global API Reference
The API serves as the control plane. All endpoints are prefixed with `/api`.
- **Docs**: `http://127.0.0.1:8000/docs`

### Primary Routers
- **Universe** (`/api/universe`): Main company funnel and stats.
- **Deal Intelligence** (`/api/intelligence`): Valuation and comparables.
    - `GET /valuation`: Real-time valuation estimates.
    - `GET /deal-probability/{id}`: Score a company.
- **Market Intel** (`/api/intel`): Market trends and briefings.
    - `GET /briefing/latest`: Weekly briefing.
    - `GET /trends`: Top market trends.
- **Capital** (`/api/capital`): PE firm and investment data.
    - `POST /scan`: Trigger capital flows scan.
    - `GET /investments`: Recent PE investments.
- **Competitive** (`/api/competitive`): VC activity and threat scores.
    - `GET /feed`: Latest VC announcements.
    - `GET /threats`: High-threat competitors.
- **Carveout** (`/api/carveout`): Divestiture signals and parent cos.
    - `POST /scan`: Identify potential carveouts.
    - `GET /candidates`: List separation candidates.
- **Deals** (`/api/deals`): Workflow triggers for enrichment/scoring.
- **Search** (`/api/search`): Global search across all entities.
- **Dashboard** (`/api/dashboard`): Aggregated stats for UI home.
- **Thesis Validator** (`/api/thesis`): Company fit analysis.
    - `GET /config`: Full thesis config (pillars, thresholds).
    - `GET /validate/{company_id}`: Company pillar breakdown, deal screening, scoring history.
    - `GET /leaderboard`: Top companies by moat score.
    - `GET /distribution`: Pillar score distribution across universe.

### Specialized Routers
- **Tracker** (`/api/tracker`): Watchlists and event monitoring.
- **Relationships** (`/api/relationships`): CRM contacts and graph.
- **Reports** (`/api/reports`): Report generation triggers.
- **Alerts** (`/api/alerts`): User alert feed.
- **Config** (`/api/config`): System settings.

## 6. Module Boundaries & Ownership

Each module under src/ follows this pattern:
- `database.py`: SQLAlchemy models (the module's tables)
- `workflow.py`: Main orchestrator (CLI entry point). Universe splits logic into `programs/` (discovery, extraction, enrichment, scoring).
- `service.py`: Public API logic (clean separation)
- `__init__.py`: Public exports

### Cross-Module Dependencies
- `deal_intelligence` reads from `capital` (PEFirmModel, PEInvestmentModel) and `universe` (CompanyModel)
- `tracker` reads from `universe` (CompanyModel) for company metadata
- `reporting` reads from all modules to generate cross-cutting reports
- `web/routers/*` read from all modules to serve API endpoints

### Critical Files (Coordinate Before Changing)
- `core/database.py`: Shared DB engines and session factories. Changes affect ALL modules.
- `core/thesis.py`: Investment thesis config loader. All scoring reads from this.
- `config/thesis.yaml`: Proprietary thesis config (gitignored). Edit this to change scoring behavior.
- `universe/database.py`: CompanyModel is the central entity. Schema changes require Alembic migration.
- `core/config.py`: Settings singleton. Adding a new env var requires updating .env.example.
- `web/routers/__init__.py`: Router registration. New routers must be added here.
- **Scraper bases**: All scraper bases live in `universe/scrapers/base.py` (`BaseScraper` for Playwright, `ApiScraper` for aiohttp). Universe and other modules (e.g. carveout) import from `src.universe.scrapers.base`. There is no scraper base in core. See `universe/scrapers/README.md`.

## 7. Logic Flow (The "Agent Loop")
1.  **Discover**: Run Universe Scrapers to find "Raw" targets.
2.  **Enrich**: Fetch financials (Companies House) and Web data.
3.  **Score**: Run `MoatScorer` (Universe) and `DealProbabilityScorer` (Intel).
4.  **Monitor**: Competitive Radar (VC) and Capital Flows (PE) provide context-driven alerts.

## 8. Common Pitfalls

1. **Async/Sync Mismatch**: `universe/programs/*` and the universe workflow use **async** sessions (`get_async_db()`). `capital/workflow.py` uses SYNC sessions. Do NOT mix async session calls into capital workflow without a full refactor. `tracker/` and `deal_intelligence/` are properly async.

2. **Core Models Separation**: `src/core/models.py` contains ONLY Enums (MoatType, CompanyTier, ThreatLevel). It does NOT contain database models or dataclasses.
   - **Enums**: `src/core/models.py`
   - **Dataclasses (DTOs)**: `src/core/data_types.py`
   - **ORM Models**: `src/<module>/database.py`

3. **Name Matching**: Always use `normalize_name()` from `core/utils.py` when comparing company names. Direct string comparison will miss "Dassault Systèmes" vs "Dassault Systemes".

4. **Database Location**: All modules share a single PostgreSQL database (run `docker-compose up -d`). 
   Use `get_db()` / `get_sync_db()` for all database access. SQLite is not supported.

5. **Router Pattern**: All new API endpoints go in a dedicated router file under `src/web/routers/`, then register it in `__init__.py`. Never add endpoints directly to `app.py`.

6. **Scripts Directory**: Canonical scripts are in `scripts/canonical/`. Other subdirectories contain historical, debug, or migration scripts. See `scripts/README.md`.

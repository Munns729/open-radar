# Module 1: Universe Scanner Specification

## Overview
The Universe Scanner is the foundational module of the RADAR system. It discovers, enriches, and scores investable B2B tech companies.
Target Universe Size: **150,000+ companies**
Primary Focus: UK (initial), expanding to EU/US.

## Data Sources
| Source | URL | specific Data |
|--------|-----|---------------|
| **IAQG OASIS** | https://www.oasis-open.org | AS9100 Certified Companies (Aerospace) |
| **Companies House** | https://api.company-information.service.gov.uk | Financials, Officers, SIC Codes, Status |
| **ISO Registries** | Various (BSI, TUV, etc.) | ISO 9001, 27001, 13485 Certifications |

## Architecture
The module is composed of:
1.  **Scrapers**: Async implementations for each data source.
    - `src/universe/scrapers/` — shared bases in `base.py` (`BaseScraper`, `ApiScraper`); API scrapers in `api/`, Playwright scrapers in `browser/`. See `src/universe/scrapers/README.md`.
2.  **Database**: SQLAlchemy models stored in PostgreSQL (or SQLite for dev).
    - `src/universe/database.py`
3.  **Analysis Logic**:
    - **Moat Scorer**: Assigns 0-100 score based on regulatory/structural advantages.
    - **Graph Analyzer**: Detects relationships (subsidiaries, supply chains).
4.  **Workflow**: Orchestrator for full/incremental builds.
    - `src/universe/workflow.py`

## Moat Scoring Methodology (0-100)
Companies are scored to identify high-quality targets (Tier 1A/1B). Companies without sufficient content (e.g. no website text, SIC-only description) are not scored: `moat_score` remains NULL and `moat_analysis.scoring_status` is set to `"insufficient_data"` so they are distinct from companies scored 0.

### 1. Regulatory Certifications (Max 40)
- **AS9100**: 20 pts (High barrrier to entry)
- **ISO 27001/13485**: 15 pts
- **FCA/MHRA**: 15-20 pts
- **ISO 9001**: 10 pts

### 2. Business Scale (Max 20)
- Revenue > £50M: 10 pts
- EBITDA Margin > 20%: 5 pts
- Employees > 100: 3-5 pts

### 3. Geographic/Strategic (Max 20)
- UK Sovereign capability (AS9100 + GB HQ): +5 pts
- Manufacturing/Physical integration: +5 pts

### Tier Classification
- **Tier 1A**: Score 70-100 (Prime Targets)
- **Tier 1B**: Score 50-69 (Secondary Targets)
- **Tier 2**: Score < 50 (Watchlist)

## Usage

### Run Full Build
Scrapes all sources and rebuilds the universe.
```bash
python -m src.universe.workflow --mode full
```

### Run Incremental Update
Updates existing companies and scrapes new pages only.
```bash
python -m src.universe.workflow --mode incremental
```

### Run Tests
```bash
pytest tests/unit/test_universe.py -v
```

## Graph Analysis
The system automatically detects relationships:
- **Shared Address**: Likely Group/Subsidiary.
- **Shared Directors**: (Future) Network identification.
- **Certifications**: Competitor clusters (same narrow scope).

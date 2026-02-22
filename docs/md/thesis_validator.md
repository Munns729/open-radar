# Thesis Validator

The **Thesis Validator** is an interactive tool for validating how individual companies fit your investment thesis.

## Overview

The Thesis Validator appears in the web UI at `/thesis` and exposes two tabs:

| Tab | Purpose |
|-----|---------|
| **Validate** | Drill into a single company: pillar scores, evidence, deal screening, scoring history |
| **Leaderboard** | Top companies by thesis score, with pillar highlights and universe distribution |

## 1. Company Validation (Validate Tab)

Answers: *"How does company X fit our investment thesis?"*

### Flow
1. Search for a scored company by name.
2. Select a company to see the full breakdown.
3. View:
   - **Score gauge** — Moat score (0–100) with tier thresholds (2, 1B, 1A); shows N/A when `scoring_status` is `insufficient_data`
   - **Pillar breakdown** — Raw score, evidence threshold, justification, weighted contribution per pillar (regulatory, network, geographic, liability, physical)
   - **Radar chart** — Visual comparison across pillars
   - **Deal screening** — Financial fit and competitive position (informational)
   - **Certifications** — With thesis-assigned scores
   - **Risk penalty** — If applicable
   - **Scoring history** — Last 5 scoring events with deltas

### Data Sources
- `companies` (moat_score, moat_attributes, moat_analysis, including `moat_analysis.scoring_status` for "insufficient_data" when not scored)
- `certifications`
- `scoring_events`
- `config/thesis.yaml` (pillar weights, thresholds)

## 2. Leaderboard (Leaderboard Tab)

Answers: *"Who are our best-fit companies?"*

### Flow
1. Lists top companies by moat score (default limit: 15).
2. Filter by tier or sector (optional).
3. Click a company to jump to Validate view.
4. **Universe Distribution** chart — Average pillar score and % of companies with evidence per pillar.

### Data Sources
- `companies` (moat_score > 0; companies with NULL score or `scoring_status: "insufficient_data"` are excluded)
- `config/thesis.yaml` (pillar names for strongest-pillar logic)

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/thesis/config` | Full thesis config (pillars, thresholds, business filters) |
| `GET /api/thesis/validate/{company_id}` | Company validation breakdown |
| `GET /api/thesis/leaderboard` | Top companies by score (optional: tier, sector) |
| `GET /api/thesis/distribution` | Pillar score distribution across universe |

## Module Dependencies

- **Universe** — Company model, certifications, scoring events
- **Core** — Thesis config, database session

## Related

- **Thesis config**: `config/thesis.yaml`, `src/core/thesis.py`
- **Moat scoring**: `src/universe/moat_scorer.py`

# RADAR: Real-time Automated Discovery & Analysis for Returns

![Status](https://img.shields.io/badge/status-active_development-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![React](https://img.shields.io/badge/frontend-React-61DAFB)
![License](https://img.shields.io/badge/license-Apache%202.0-orange)

**AI-powered investment intelligence platform for private equity deal sourcing.**

RADAR automates the top of the PE funnel: it discovers companies, scores their structural defensibility, tracks competitive threats, identifies carveout opportunities, and maps global capital flows — surfacing high-conviction investment targets before they come to market.

## What RADAR Does

- **Universe Scanner** — Continuously discovers European B2B tech companies (configurable by revenue, geography, sector) from Companies House, accreditation registries, industry directories, and web scraping.
- **Moat Scoring** — Scores every company (0–100) on structural defensibility using a configurable 5-Pillar analysis with both quantitative rules and LLM-powered semantic enrichment.
- **Capital Flows** — Tracks 6,000+ PE firms globally, mapping portfolios, dry powder, and recent transactions.
- **Carveout Scanner** — Identifies corporate divisions ripe for divestiture by monitoring earnings calls, activist activity, and segment reporting.
- **Competitive Radar** — Monitors VC funding rounds and competitive dynamics as threat signals.
- **Deal Intelligence** — Valuation comparables, deal probability scoring, and market trend detection.
- **Relationship Manager** — CRM for tracking intermediary and founder relationships.
- **Reporting** — Automated HTML and Excel report generation with configurable filters.

## 5-Pillar Moat Analysis

RADAR's default scoring framework evaluates companies on five structural moat pillars:

1. **Regulatory & Compliance** — Barriers from licenses, mandates, or certifications (e.g. ITAR, AS9100, FDA)
2. **Network Effects** — Value increases with user adoption (marketplaces, data contribution networks)
3. **Intellectual Property** — Patents, trade secrets, and defensible technical moats
4. **Brand & Reputation** — Customer loyalty, trusted vendor status, and switching costs
5. **Cost Advantage** — Economies of scale, unique resource access, or process efficiencies

The scoring framework is fully configurable — see `docs/design/custom_investment_thesis.md` for the custom thesis architecture that lets you define your own scoring rules.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy, Alembic |
| Frontend | React, Vite, Tailwind CSS |
| Database | PostgreSQL (recommended) / SQLite (dev) |
| AI | OpenAI-compatible LLMs (configurable) |
| Scraping | Playwright (browser automation) |

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/radar.git
cd radar

# Environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Playwright browsers (for scraping)
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your API keys

# Database (PostgreSQL via Docker)
docker-compose up -d

# Run backend
uvicorn src.web.app:app --reload --port 8000

# Run frontend (separate terminal)
cd src/web/ui
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) for the dashboard, or [http://localhost:8000/docs](http://localhost:8000/docs) for the API.

## Project Structure

```
src/
├── core/                # Config, models, database, shared utilities
├── web/                 # FastAPI backend + React frontend
│   ├── app.py           # FastAPI application
│   ├── routers/         # API endpoint routers
│   └── ui/              # React/Vite frontend
├── universe/            # Company discovery & moat scoring
├── competitive/         # VC threat monitoring
├── tracker/             # Target company watchlists & events
├── deal_intelligence/   # Valuations, comparables, deal probability
├── market_intelligence/ # Trend detection, news, weekly briefings
├── relationships/       # CRM & network mapping
├── capital/             # PE firm tracking & capital flows
├── carveout/            # Corporate divestiture signals
├── reporting/           # HTML/Excel report generation
├── alerts/              # Alert engine & notifications
└── search/              # Global search across all entities
```

See `AGENTS.md` for a comprehensive guide to the codebase, database schema, API reference, and module boundaries.

## Documentation

| Document | Description |
|----------|------------|
| `AGENTS.md` | Full codebase guide for AI agents and developers |
| `DEVELOPMENT.md` | Development workflow and conventions |
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/GETTING_STARTED.md` | Detailed setup guide |
| `docs/design/custom_investment_thesis.md` | Custom thesis scoring architecture |
| `docs/md/` | Per-module documentation |
| `docs/specs/` | Module specifications |

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.

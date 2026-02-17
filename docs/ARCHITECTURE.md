# RADAR System Architecture

## High-Level Overview

```text
+-------------+      +-------------+      +------------------+
|   Sources   |  ->  |  Ingestion  |  ->  |   Intelligence   |
| (Web/APIs)  |      |  (Scrapers) |      | (AI/Agents)      |
+-------------+      +-------------+      +------------------+
                                                 |
                                                 v
                                          +------------------+
                                          |     Database     |
                                          | (Postgres/SQLAlchemy)|
                                          +------------------+
                                                 |
                                                 v
                                          +------------------+
                                          |   Action/UI      |
                                          | (Reports/Notion) |
                                          +------------------+
```

## Modules

### Core
- **Config**: Centralized configuration management.
- **Models**: Shared Pydantic/Dataclass data structures.

### Functional Modules
1. **Universe**: Scans Companies House, LinkedIn, etc. for raw targets.
2. **Competitive**: Monitors VC portfolios and funding news.
3. **Tracker**: Periodic updates on specific watchlist companies.
4. **Intelligence**: Synthesizes data to form investment opinions.
5. **Relationships**: Tracks interactions with founders/intermediaries.
6. **Market Intel**: Aggregates macro trends and sector news.
7. **Market Intel**: Aggregates macro trends and sector news.
8. **Capital**: Tracks LP capital flows.
9. **Carveout**: Special module for corporate divestiture detection.

## Data Flow
1. **Scrapers** (Playwright) fetch raw HTML/JSON.
2. **Parsers** (BeautifulSoup) extract structured data.
3. **Agents** (Kimi/Antigravity) enrich and classify data (e.g., Moat detection).
4. **Database** (PostgreSQL) stores structured records.
5. **Alembic** manages schema migrations.

## Tech Choices
- **Python 3.11**: Modern async support and type hinting.
- **Playwright**: Robust browser automation for dynamic sites.
- **SQLAlchemy 2.0**: Modern ORM with async support.
- **Pydantic**: Data validation and serialization.
- **Multi-Agent**: Decoupled agents for scalability and specialization.

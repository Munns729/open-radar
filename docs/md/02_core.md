# Core Module Documentation

The `src.core` module provides the foundational infrastructure for the RADAR platform, including configuration management, database connections, and shared data models.

## 1. Configuration (`src.core.config`)

RADAR uses `pydantic-settings` to manage configuration. This ensures type safety and allows settings to be loaded from environment variables (`.env` file) or defaults.

### Key Settings
The `Settings` class defines all available configuration options:

-   **Environment**: `ENVIRONMENT` (development/production), `LOG_LEVEL`.
-   **API Keys**: 
    -   `MOONSHOT_API_KEY` (Kimi AI)
    -   `OPENAI_API_KEY` (Fallback/Alternative)
    -   `COMPANIES_HOUSE_API_KEY` (Financial data)
    -   `SENDGRID_API_KEY`, `SLACK_WEBHOOK_URL` (Notifications)
-   **Database**: 
    -   `DATABASE_URL`: Connection string for the main application database (default: `sqlite:///data/radar.db`).
    -   `UNIVERSE_DB_URL`: Connection string for the discovery database (can be separated for scale).

### Usage
```python
from src.core.config import settings

print(settings.database_url)
if settings.environment == "production":
    # Do production things
    pass
```

## 2. Database (`src.core.database`)

The system uses **SQLAlchemy (AsyncIO)** for database interactions.

-   **Engine**: An asynchronous engine (`create_async_engine`) is initialized using the `DATABASE_URL`.
-   **Sessions**: `get_db()` is an async generator dependency used in FastAPI endpoints to provide a database session.
-   **Base**: `Base` is the declarative base for all ORM models.

### Multi-Database Support
The configuration supports splitting the "Universe" (raw discovery data) from the "Intelligence" (processed insights) data via `UNIVERSE_DB_URL`, though they currently point to the same SQLite file by default.

## 3. Shared Models (`src.core.models`)

`src.core.models` contains **dataclasses** (not ORM models) that are used across different modules to ensure consistent data structures. These, or similar Pydantic models, are often used for internal data passing before being mapped to SQLAlchemy ORM models.

### Key Dataclasses
-   **`Company`**: Standard representation of a target company.
    -   Fields: `revenue_gbp`, `ebitda_margin`, `moat_score`, `tier`.
-   **`CompanyTier` (Enum)**:
    -   `1A`: High priority (>£15M Rev, Strong Moat).
    -   `1B`: Medium priority (>£15M Rev, Moderate Moat).
    -   `2`: Watchlist.
-   **`MoatType` (Enum)**: The 5-Pillar classification (Network Effects, Regulatory, etc.).
-   **`ScraperOutput`**: Standardized container for raw data extracted from web scrapers.
-   **`AIAnalysisOutput`**: Standardized result format for LLM operations.

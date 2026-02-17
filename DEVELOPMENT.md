# RADAR Development Guide

This guide is for developers contributing to the RADAR (Real-time Automated Discovery & Analysis for Returns) system.

## Environment Setup

### Prerequisites
- **Python 3.11+**: Ensure you have a compatible version.
- **Node.js 18+**: For the React frontend.
- **Git**: Version control.
- **VS Code**: Recommended IDE.

### Initial Setup
1.  **Clone the Repository**
    ```bash
    git clone <repo-url>
    cd radar
    ```

2.  **Frontend Setup**
    ```bash
    cd src/web/ui
    npm install
    # Test the build
    npm run build
    ```

3.  **Backend Setup**
    Return to the root directory:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    
    pip install .
    ```

4.  **Configuration**
    Copy `.env.example` to `.env` and fill in:
    - `MOONSHOT_API_KEY`: Kimi AI key (Required for analysis).
    - `COMPANIES_HOUSE_API_KEY`: (Optional) for live UK company API access.
    - `DATABASE_URL`: `sqlite+aiosqlite:///./data/radar.db` (Default).

## Project Structure

RADAR is built as a modular monolith. Each module in `src/` should be self-contained where possible, exposing a `workflow.py` or public interface.

```
src/
├── core/           # Shared models (config.py, models.py)
├── database/       # Shared database connection logic
├── web/            # FastAPI App & React UI
├── universe/       # Module 1: Universe Scanner
├── competitive/    # Module 2: Competitive Radar
├── tracker/        # Module 3: Target Tracker
├── intelligence/   # Module 4: Deal Intelligence
├── relationships/  # Module 5: Relationship Manager
├── capital/        # Module 10: Capital Flows
└── carveout/       # Module 11: Carveout Scanner
```

## Common Workflows

### 1. Running the Scrapers (Manual)
Most modules have a `workflow.py`. You can trigger them directly:

**Universe Scanner:**
```bash
python -m src.universe.workflow
```

**Capital Flows (PE Firm Discovery):**
```bash
python -m src.capital.workflow
```

### 2. Running the API Server
The FastAPI backend serves both the API and the React frontend (in production mode).
```bash
uvicorn src.web.app:app --reload
```
Swagger Docs: http://127.0.0.1:8000/docs

### 3. Database Management
We use SQLAlchemy and Alembic (coming soon) for migrations. Currently, `src/core/database.py` handles schema creation on startup if tables are missing.

To reset the database:
1. Delete `data/radar.db`
2. Restart the app

## Testing
Run unit tests with pytest:
```bash
pytest
```
Run specific module tests:
```bash
pytest tests/unit/test_universe_scanner.py
```

## Coding Standards
- **Type Hints**: Use Python type hints everywhere.
- **Async/Await**: The system is built on `asyncio`. Use `async def` for I/O bound operations.
- **Docstrings**: Document all public classes and functions.
- **Logging**: Use `logging.getLogger(__name__)` instead of `print`.

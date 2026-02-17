# Getting Started with RADAR

## Prerequisites
- Python 3.11+
- Git
- PostgreSQL (optional for local dev, SQLite default)
- Moonshot (Kimi) API Key
- Companies House API Key

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd radar
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   - `MOONSHOT_API_KEY`: Required for AI analysis
   - `COMPANIES_HOUSE_API_KEY`: Required for universe scanning
   - `DATABASE_URL`: Defaults to local SQLite

## Running the System

### 1. Run Tests
Verify everything is set up correctly:
```bash
pytest
```

### 2. Run Universe Scanner (Example)
```bash
python -m src.universe.scanner
```

## Next Steps
- Review `ARCHITECTURE.md` for system design.
- Explore `src/core/models.py` to understand data structures.

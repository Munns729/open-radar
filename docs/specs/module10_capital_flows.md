# Module 10: Capital Flows Scanner

## 1. Overview
The Capital Flows Scanner tracks global capital allocators to answer "Who buys companies like ours?" and "What multiples do they pay?". It monitors:
- **6,000 PE Firms**: Tracking funds, strategy, and portfolio companies.
- **500 Consolidators**: Serial acquirers and platform companies.
- **400 Strategic Acquirers**: Corporate buyers in relevant sectors.

## 2. Architecture
The system uses an **LLM-Agent based scraping architecture** to bypass anti-bot measures and handle unstructured data.

### Components
1.  **Database Layer (`src/capital/database.py`)**: SQLAlchemy models storing firms, investments, and acquisitions.
2.  **Scraping Agents (`src/capital/scrapers/`)**:
    -   `BaseBrowsingAgent`: Wraps Playwright + LLM (Open Source/Cheap) for robust navigation.
    -   `SECEdgarAgent`: Finds US PE firms via SEC Form ADV.
    -   `PEWebsiteAgent`: Extracts portfolio data from firm websites.
    -   `NewsMonitoringAgent`: Tracks M&A news.
    -   `PublicMarketAgent`: Parses 8-Ks for deal terms.
3.  **Analysis Engines (`src/capital/analyzers/`)**:
    -   `ExitMatcher`: Matches portfolio companies to buyers.
4.  **Workflow (`src/capital/workflow.py`)**: Orchestrates the weekly scan.

## 3. Data Models

### PE Firm
- `id`, `name`, `aum_usd`, `strategy` (Buyout, Growth), `hq_country`
- `portfolio_companies`: Relationship to Investments

### PE Investment
- `pe_firm_id`, `company_name`, `entry_date`, `exit_date`
- `moat_type`, `entry_multiple`, `exit_multiple`, `moic`

### Consolidator
- `name`, `type` (Platform, Serial), `sponsor_id` (if PE backed)
- `acquisition_criteria` (Size, Sector)

### Strategic Acquirer
- `name`, `sector`, `market_cap`, `cash_balance`
- `acquisitions_last_24m`

## 4. Agentic Scraping Strategy
To minimize costs and avoid blocking:
- **Engine**: Playwright (Headless)
- **Intelligence**: Small OSS Models (e.g., Llama-3-8b, Mistral-7b) via generic API interface.
- **Protocol**:
    1.  **Render**: Load page in Playwright.
    2.  **Vision/Text**: Extract text overlay or simplified DOM.
    3.  **Decision**: LLM decides "Click Next Page" or "Extract Table".
    4.  **Action**: Playwright executes.

## 5. Thesis Validation
Key queries to run:
- **Regulatory Premium**: Avg EBITDA multiple for `moat_type='regulatory'` vs others.
- **Platform Arbitrage**: Avg entry multiple of Platform vs Avg exit multiple of Platform.
- **Strategic vs Financial**: Delta in multiples paid by Strategics vs PE.

## 6. Usage
```python
from src.capital.workflow import scan_capital_flows

# Run full weekly scan
await scan_capital_flows()
```

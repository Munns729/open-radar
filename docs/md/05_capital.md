# Capital Flows Module Documentation

The `src.capital` module tracks the "Money" side of the market. It monitors Private Equity firms, their portfolio companies, and strategic consolidators to understand who is buying what.

## 1. Workflow (`src.capital.workflow`)

The `scan_capital_flows` function orchestrates the intelligence gathering:

1.  **SEC Scraping (`SECEdgarAgent`)**:
    -   Searches SEC EDGAR filings for keywords like "Growth Equity" and "Venture Capital" to discover new PE firms and their AUM.
2.  **Portfolio Enrichment (`PEWebsiteAgent`)**:
    -   Visits the websites of discovered PE firms.
    -   Scrapes their "Portfolio" pages to list all current and past investments.
    -   Extracts sector, description, and exit status.
3.  **Thesis Validation (`ThesisValidator`)**:
    -   Analyzes the aggregated data to see if market activity aligns with RADAR's investment theses.

## 2. Key Data Models (`src.capital.database`)

### PE Firm (`PEFirmModel`)
Represents an investment firm.
-   **Key Fields**: `aum_usd`, `investment_strategy` (Buyout, Growth), `sector_focus`.

### PE Investment (`PEInvestmentModel`)
Represents a portfolio company held by a PE firm.
-   **Usage**: These records are the primary source for the **Valuation Engine** (Module 4) to find comparables.
-   **Enrichment**: We try to capture `entry_multiple`, `entry_valuation_usd`, and `moic` (Multiple on Invested Capital) where public.

### Consolidators (`ConsolidatorModel`)
Tracks "Platform" companies that are aggressively acquiring others.
-   **Type**:
    -   `pe_backed_platform`: A PE-owned company executing a "Buy & Build" strategy.
    -   `public_rollup`: A public company growing via M&A.
-   **Acquisitions**: Linked to `ConsolidatorAcquisitionModel` to track their M&A history.

### Strategic Acquirers (`StrategicAcquirerModel`)
Tracks large corporate buyers (e.g., "Defense Primes", "Big Pharma") to predict exit routes for our targets.

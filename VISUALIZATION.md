# System Visualization: Investor Radar Sourcing Flow

This document maps the **Investor Radar** sourcing engine's architecture. Use this reference to understand the `[FLOW]` logs generated during execution.

## Visual Map (Mermaid.js)

```mermaid
graph TD
    %% Zone 1: Intake
    subgraph "Zone 1: Discovery (The Funnel)"
    A[Twitter/X Search] --> D{New Entity?}
    B[SEC Filings/News] --> D
    C[Crunchbase API] --> D
    end

    %% Zone 2: The Agentic Router
    subgraph "Zone 2: Extraction Strategy"
    D -- "Yes" --> E[Check Website Type]
    E --> F{Bot Protection?}
    
    F -- "Low (Static HTML)" --> G[Software Scraper: BeautifulSoup/Requests]
    F -- "High (React/WAF)" --> H[Browser Agent: Playwright/Stealth]
    
    G --> I{Success?}
    I -- "Fail (403/Empty)" --> H
    end

    %% Zone 3: Enrichment
    subgraph "Zone 3: Intelligence"
    G & H & I -- "Data" --> J[LLM: Clean & Normalize]
    J --> K[LLM: Investor Fit Scoring]
    K --> L[Vector DB: Investor Radar Storage]
    end

    %% Alerts
    L --> M[Slack/Email Alert]
    
    %% Styles
    style H fill:#f96,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333
    style J fill:#dfd,stroke:#333
```

## Interpreting Console Logs

The system now outputs high-level `[FLOW]` logs that correspond to the zones above.

### Zone 1: Discovery
- **Log**: `[FLOW] Zone 1: Discovery (The Funnel)`
- **Action**: The system initiates discovery agents (GoodFirms, Wikipedia, etc.) to find new prospective companies.
- **Agent Logs**:
    - `[FLOW] Hand-off -> GoodFirms Browser Agent...`
    - `[FLOW] Agent Reasoning -> Action: ...`
    - `[FLOW] New Entity Found: ...`

### Zone 2: Extraction Strategy
- **Log**: `[FLOW] Zone 2: Extraction Strategy (Agentic Hand-off)`
- **Action**: The system determines the best extraction method for each target.
- **Key Event**: The "Hand-off" between static scraping and browser automation.
    - `[FLOW] Check Website Type -> ...`
    - `[FLOW] Hand-off -> Browser Agent (Playwright/Stealth): ...`
    - `[FLOW] Fail (Timeout/403) -> ...` (Triggers retry/fallback logic)

### Zone 3: Intelligence
- **Log**: `[FLOW] Zone 3: Intelligence (LLM & Vector DB)`
- **Action**: Data is normalized and scored against the investment thesis.
- **Scoring Logs**:
    - `[FLOW] Hand-off -> LLM: Investment Thesis Grading...`
    - `[FLOW] Classification -> Tier ... (Score: ...)`

## How to Run

Execute the standard build command to see the flow in action:

```bash
python src/universe/workflow.py --mode full --countries FR
```

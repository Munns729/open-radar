# Module 11: Carveout Scanner (Europe Focused)

## Overview
The Carveout Scanner identifies corporate divisions likely to be divested by European public companies. It focuses on the LSE, Euronext, and Deutsche Börse markets. It tracks signals from 2,000+ divisions to find less competitive, high-moat acquisition targets.

## Data Sources
1.  **Annual Reports (PDFs)**: Primary source for segment data.
    -   Parsed via `SegmentReportScraper` (Playwright).
    -   Extracts revenue, EBITDA, and descriptions from "Segmental Analysis" notes (IFRS 8).
2.  **Earnings Call Transcripts**:
    -   Analyzed via `EarningsCallAnalyzer` using NLP (Kimi).
    -   Detects "strategic review", "non-core", and other key phrases.
3.  **Activist Campaigns**:
    -   Tracked via `ActivistTracker`.
    -   Monitors funds like Cevian, Amber Capital, Elliott for divestiture demands.

## Scoring Methodology

### Divestiture Probability (0-100)
Calculated by `SignalDetector`.
-   **Explicit Signals (+40-80)**: Strategic review announced, banker hired, spin-off planned.
-   **Implicit Signals (+15-20)**: Omitted from strategy, CapEx reduction, management churn.
-   **Early Signals (+10-15)**: New CEO "simplification", regulatory pressure.

### Attractiveness Score (0-100)
Calculated by `AttractivenessScorer`.
-   **Size Match (Max 25)**: Revenue £10-100M (~€12-120M) is sweet spot.
-   **Moat Strength (Max 30)**: Regulatory barriers, entrenched contracts.
-   **Financials (Max 20)**: High EBITDA margin preferred.
-   **Complexity (Max 15)**: Standalone/Semi-autonomous preferred for easier separation.

## Usage

### Run Scan
```bash
python -m src.carveout.workflow
```

### Run Tests
```bash
pytest tests/unit/test_carveout.py -v
```

## Classes
-   `CorporateParent`, `Division`: Database models.
-   `SignalDetector`: Probability logic.
-   `AttractivenessScorer`: Investment thesis fit.
-   `SegmentReportScraper`: Browser-based scraper.

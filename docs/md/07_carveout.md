# Carveout Scanner Module Documentation

The `src.carveout` module identifies corporate divestiture opportunities—assets likely to be shed by large parent companies.

## 1. Workflow (`src.carveout.workflow`)

The scanner operates by monitoring large "Corporate Parents" (e.g., Unilever, Siemens) for signs of portfolio rationalization.

1.  **Signal Detection (`SignalDetector`)**:
    -   Scrapes news and investor reports for "trigger phrases".
    -   Keywords: "Strategic Review", "Non-core assets", "Focus on core business", "Spin-off", "Divestiture".
2.  **Division Mapping**:
    -   Maps the parent company's structure to identify specific business units (Divisions).
3.  **Attractiveness Scoring (`AttractivenessScorer`)**:
    -   Rates the likelihood of a carveout and the quality of the asset.

## 2. Scoring Logic

### Carveout Likelihood
-   **High**: Explicit mention of "Strategic Review" for the specific unit.
-   **Medium**: General statement about shedding non-core assets + unit underperformance.
-   **Low**: No specific signals.

### Asset Quality
-   Evaluated similar to the **Universe** module (Financials, Moat potential), but with a focus on standalone viability (can it survive without the parent?).

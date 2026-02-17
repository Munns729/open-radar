# Deal Intelligence Module Documentation

The `src.intelligence` module turns raw data into actionable deal insights. It handles Valuation, Market Trends, and Deal Probability scoring.

## 1. Workflow (`src.intelligence.workflow`)

The workflow runs three key processes in sequence:
1.  **Enrich Deals**: Fills in missing valuation multiples for PE investments using LLM estimation or comparables.
2.  **Update Market Metrics**: Aggregates historical data to tracking sector trends.
3.  **Score Deal Probabilities**: Predicts which companies are likely to transact soon.

## 2. Valuation Engine (`ComparablesEngine`)

Located in `src.intelligence.analytics`, this engine estimates a company's value range using **Comparable Company Analysis (Comps)**.

### Logic
1.  **Find Comparables**: Searches `DealRecord` database for past transactions matching:
    -   **Sector**: Weighted 40% (Exact match preferred).
    -   **Size**: Weighted 30% (Revenue/EV within range).
    -   **Geography**: Weighted 15% (Same region).
    -   **Time**: Weighted 15% (Recency).
2.  **Calculate Similarity**: Assigns a similarity score (0-100) to each potential comp.
3.  **Derive Range**: Uses the multiples (EV/EBITDA, EV/Revenue) of the top matches to calculate Low, Median, and High valuation estimates.

## 3. Market Trends (`MarketTrendsAnalyzer`)

Aggregates `DealRecord` data to spot broader market movements.

### Metrics Tracked
-   **Sector Heat**: Detects "Hot Sectors" based on:
    -   Deal Volume Growth (>20% increase).
    -   Multiple Expansion (rising valuations).
-   **Aggregates**: Median multiples, total deal value, and volume per sector per month.

## 4. Deal Probability (`DealProbabilityScorer`)

Predicts the likelihood (0-100%) of a specific company becoming a target for Private Equity within 6-12 months.

### Signals & Scoring
The score is a weighted sum of various "Distress" or "Opportunity" signals:
-   **Declining Growth**: Revenue slowdown often triggers PE interest (Turnaround/Buyout).
-   **PE Sector Interest**: High activity in the sector recently.
-   **Sweet Spot Size**: £15-100M Revenue (ideal for mid-market PE).
-   **Time Since Last Deal**: Sectors act in cycles; if it's been quiet, activity may be due.
-   **Moat Score**: High quality targets are always in demand.

**Output**:
-   **High (>70%)**: Expected transaction in 6-12 months.
-   **Medium (40-70%)**: 12-24 months.
-   **Low (<40%)**: Long term or unlikely.

# Module 4: Deal Intelligence

The **Deal Intelligence** module provides the analytical brain of RADAR, focusing on valuation, deal probability, and market trends.

## Key Components

### 1. Comparables Engine (`ComparablesEngine`)
Finds precedent transactions to estimate valuation.
- **Matching**: Matches on Sector, Size (Revenue/EBITDA), Geography, and Time.
- **Output**: Generates a valuation range (Low-Median-High) based on EV/Revenue and EV/EBITDA multiples.

### 2. Deal Probability Scorer (`DealProbabilityScorer`)
Estimates the likelihood of a specific company transacting in the next 6-12 months.
**Signals**:
- Declining revenue growth (Seller distress).
- Management changes (CEO/CFO exits).
- High PE interest in the sector (Demand).
- Founder age/tenure.

### 3. Market Trends (`MarketTrendsAnalyzer`)
Aggregates sector-level data to identify "Hot Sectors" (rising volume + rising multiples).

## Usage

Run the intelligence scan (re-calculates metrics for the dashboard):
```bash
python -m src.intel.workflow
```

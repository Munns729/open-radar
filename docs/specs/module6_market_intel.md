# Module 6: Market Intel

## Overview
The Market Intel module aggregates intelligence from 50+ news sources, regulatory bodies, and market data feeds. It uses Kimi K2.5 to synthesize this information into actionable insights, relevance scores, trend detection, and weekly briefings.

## Architecture

### 1. Data Sources (`src/intel/sources`)
- **NewsAggregator**: Fetches RSS feeds and scrapes websites. Handles deduplication via SHA256 hashing.
- **RegulatoryMonitor**: targeted scrapers for FCA, MHRA, CAA, etc.

### 2. Database Models (`src/intel/database.py`)
- `NewsSource`: Configuration for feeds.
- `IntelligenceItem`: The core unit of intelligence (article/snippet).
- `RegulatoryChange`: Specific structured regulatory updates.
- `MarketTrend`: AI-detected trends over time.
- `WeeklyBriefing`: Synthesized outputs.

### 3. Analysis (`src/intel/analyzers`)
- **RelevanceScorer**: Uses Kimi to score items 0-100 based on sector impact, regulatory barriers, M&A relevance, and thesis alignment.
- **TrendDetector**: Analyzes high-relevance items over a lookback period (e.g., 30 days) to identify emerging themes.

### 4. Synthesis (`src/intel/synthesizers`)
- **WeeklyBriefingGenerator**: Compiles top items, regulatory changes, and trends into an executive summary.

## Workflows (`src/intel/workflow.py`)

### Daily Scan
Runs at 08:00.
1. `NewsAggregator` fetches all sources.
2. `RegulatoryMonitor` checks for updates.
3. `RelevanceScorer` scores new items.

### Weekly Briefing
Runs Sunday 18:00.
1. `TrendDetector` updates trend analysis.
2. `WeeklyBriefingGenerator` creates the briefing.
3. (Future) Email delivery.

## Usage

```python
import asyncio
from src.intel.workflow import run_intel_scan, generate_market_briefing

# Run daily scan manually
asyncio.run(run_intel_scan())

# Generate weekly briefing
asyncio.run(generate_market_briefing())
```

## Testing
Run unit tests:
```bash
pytest tests/unit/test_intel.py -v
```

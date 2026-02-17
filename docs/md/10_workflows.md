# Common Workflows & Scripts

This guide lists the primary CLI entry points for running RADAR's intelligence modules manually.

## 1. Discovery & Universe
**Goal**: Find new companies and score them.

```bash
# Full Discovery (Scrape -> Enrich -> Score)
python -m src.universe.workflow --mode full --countries FR DE

# Enrichment Only (No new scraping, just update data for existing companies)
python -m src.universe.workflow --mode enrich
```

## 2. Competitive Radar
**Goal**: Check LinkedIn for new VC investments.

```bash
# Run the visual scraper and AI analyzer
python -m src.competitive.workflow
```

## 3. Capital Flows
**Goal**: Find new PE firms and scrape their portfolios.

```bash
# Scrape SEC and PE websites
python -m src.capital.workflow
```

## 4. Deal Intelligence
**Goal**: Update valuation multiples and market trends.

```bash
# Run full analytics pipeline
python -m src.intelligence.workflow
```

## 5. Target Tracker
**Goal**: Update status of specific watchlist companies.

```bash
# Update all high-priority targets
python -m src.tracker.workflow update --force

# Add a company to tracker
python -m src.tracker.workflow add 123 --priority high --notes "Interesting moat"
```

## 6. Relationships
**Goal**: Sync emails and update contact scores.

```bash
# Run daily sync
python -m src.relationships.workflow
```

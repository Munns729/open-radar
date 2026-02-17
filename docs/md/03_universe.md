# Universe Module Documentation

The `src.universe` module is the entry point of the RADAR funnel. It is responsible for discovering companies, populating the database, enriching data, and performing the initial "Moat Score" to filter for quality.

## 1. Workflow Orchestration (`src.universe.workflow`)

The main entry point is `build_universe`, which runs in three phases:

### Phase 1: Discovery
Scrapers run to find "raw" company targets.
-   **AS9100 & ISO Registries**: Manufacturing/Engineering targets.
-   **Clutch & GoodFirms**: Tech services and agencies.
-   **Wikipedia**: specialized lists (e.g., "Software companies of France").

**Deduplication**: Companies are saved to the DB with a check against existing names to prevent duplicates.

### Phase 2: Enrichment (`enrich_companies`)
Once companies are in the DB, this phase fills in the gaps:
1.  **Companies House**: Fetches financial data (Revenue, EBITDA, Employees) for UK companies using the API.
2.  **Website Scraping**: Extracts meta descriptions and keywords to help the AI understand the business.
3.  **Relationship Enrichment**: Finds customers/suppliers to build the knowledge graph.

### Phase 3: Scoring (`run_scoring_pipeline`)
Runs the `MoatScorer` and `GraphAnalyzer` to assign a Tier (1A/1B/2) to each company.

## 2. Moat Scoring (`src.universe.moat_scorer`)

The `MoatScorer` implements the **5-Pillar Investment Thesis**. It combines deterministic signals (certifications) with AI analysis.

### The 5 Pillars
1.  **Regulatory (Lock)**:
    -   *Evidence*: Certifications like AS9100, Pyrotechnic licenses, FDA approvals.
2.  **Network Effects (Share)**:
    -   *Evidence*: Platform business models, high centrality in the `CompanyRelationship` graph.
3.  **Intellectual Property (Shield)**:
    -   *Evidence*: Patents, deep tech descriptions.
4.  **Brand & Reputation (Award)**:
    -   *Evidence*: "Trusted partner" status, liability transfer (e.g., Testing/Inspection firms like Intertek).
5.  **Cost/Structural (Coins)**:
    -   *Evidence*: Economies of scale, vertical integration.

### Scoring Logic
-   **LLM Analysis**: `LLMMoatAnalyzer` reads the company description and website text to argue for/against each pillar.
-   **Hard Signals**: 
    -   Specific certifications (e.g., AS9100 = +50 points).
    -   Known platform keywords in name (e.g., "Zoopla").
    -   Revenue scale (>£15M adds points).

**Total Score Calculation**: Each pillar contributes independently, with different maximum scores:
- Regulatory: Max **100** points
- Network: Max **100** points  
- Liability: Max **75** points
- Physical: Max **60** points
- IP: Max **60** points
- **Total possible**: **395** points

The `moat_score` field in the database stores the **total additive score** (0-395 scale), not a normalized 0-100 value.
    
**Tiering Thresholds** (based on total score):
-   **Tier 1A**: Score ≥ 120 (Strong Moat)
-   **Tier 1B**: Score ≥ 70 (Good Defensibility)
-   **Tier 2**: Score ≥ 30 (Watchlist)

## 3. Graph Analysis
`src.universe.graph_analyzer` builds a network graph of companies based on "Customer" and "Supplier" relationships.
-   **Centrality**: Companies that sit at the center of many relationships get a "Network Effect" boost in their Moat Score.

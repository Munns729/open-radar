# Universe Module Documentation

The `src.universe` module is the entry point of the RADAR funnel. It is responsible for discovering companies, populating the database, enriching data, and performing the initial "Moat Score" to filter for quality.

## 1. Workflow Orchestration (`src.universe.workflow` + `src.universe.programs`)

The main entry point is `build_universe`, which runs in four phases. Implementation lives in `programs/`: discovery, extraction, enrichment, scoring.

### Phase 1: Discovery (`programs.discovery.run_discovery`)
Scrapers run to find "raw" company targets.
-   **AS9100 & ISO Registries**: Manufacturing/Engineering targets.
-   **Clutch & GoodFirms**: Tech services and agencies.
-   **Wikipedia**: specialized lists (e.g., "Software companies of France").

**Deduplication**: Companies are saved to the DB with a check against existing names to prevent duplicates.

Discovery is run via the universe workflow or canonical scripts (see **AGENTS.md** and **scripts/README.md**). There is no separate prompt-input document; configuration lives in `config/thesis.yaml` and scraper implementations in `src/universe/scrapers/`.

### Phase 2: Extraction (`programs.extraction.run_extraction`, formerly `enrich_companies`)
Once companies are in the DB, this phase fills in the gaps:
1.  **Companies House / OpenCorporates**: Fetches financial data (Revenue, EBITDA, Employees) for UK/EU companies.
2.  **Website discovery**: Agent finds company website when missing.
3.  **LLM enrichment**: Description, sector, revenue from website.
4.  **Website scraping**: Raw text and keywords for downstream scoring. Sets `extraction_complete_at` when done.

### Phase 3a: Semantic Enrichment (`programs.enrichment.run_enrichment`)
Batch LLM pillar scoring for companies with `raw_website_text` that have not yet been semantically enriched. Writes `moat_analysis["semantic"]` and `semantic_enriched_at`.

### Phase 3b: Scoring (`programs.scoring.run_scoring`, formerly `run_scoring_pipeline`)
Runs the `MoatScorer` (no graph) to assign a Tier (1A/1B/2) to each company. Records audit trail in `ScoringEvent`.

**Insufficient data**: Companies without enough content to score (no `raw_website_text`, or only SIC-code descriptions) are **not** sent to the LLM. They are marked with `moat_analysis.scoring_status = "insufficient_data"` and `moat_score` is left `NULL` (or cleared if it was 0), so "not scored" is distinct from "scored 0". The UI shows these as "No Data" / N/A.

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

The `moat_score` field in the database stores the **total additive score** (0-395 scale), not a normalized 0-100 value. It may be **NULL** when a company has insufficient data for scoring (see Phase 3b above); in that case `moat_analysis.scoring_status` is `"insufficient_data"`.
    
**Tiering Thresholds** (based on total score):
-   **Tier 1A**: Score ≥ 120 (Strong Moat)
-   **Tier 1B**: Score ≥ 70 (Good Defensibility)
-   **Tier 2**: Score ≥ 30 (Watchlist)

## 3. Graph Analysis (currently unused in pipeline)
`src.universe.graph_analyzer` can build a network graph of companies based on "Customer" and "Supplier" relationships. The pipeline no longer runs graph analysis or relationship enrichment; `MoatScorer` is called with `graph_signals=None`. The graph module remains available for future use.

# Competitive Radar Module Documentation

The `src.competitive` module monitors the Venture Capital landscape to identify emerging threats to our investment thesis or portfolio companies.

## 1. Workflow (`src.competitive.workflow`)

The `run_competitive_radar` function executes a visual surveillance workflow:

1.  **Visual Scraping (`LinkedInScraper`)**:
    -   Logs into a monitored LinkedIn account.
    -   Scrolls the feed to capture screenshots of posts from VCs and tech news sources.
2.  **AI Analysis (`KimiAnalyzer`)**:
    -   Uses a Vision-Language Model (Moonshot/Kimi) to read the screenshots.
    -   Extracts structured data: `Company Name`, `VC Firm`, `Round Amount`, `Round Type`, `Description`.
3.  **Threat Scoring (`ThreatScorer`)**:
    -   Evaluates the announcement to assign a **Threat Level** (Low to Critical).

## 2. Threat Scoring (`src.competitive.threat_scorer`)

The scoring algorithm assigns points (0-100) based on four factors:

### A. VC Tier (Max 30 pts)
-   **Tier A (30 pts)**: Top-tier firms like Sequoia, a16z, Benchmark. Their backing implies high disruption potential.
-   **Tier B (20 pts)**: Recognizable but non-elite firms.
-   **Unknown (10 pts)**: Other investors.

### B. Round Size (Max 25 pts)
-   **>£20M (25 pts)**: Major war chest.
-   **£10-20M (20 pts)**: Significant scale-up capital.
-   **<£5M (10 pts)**: Seed stage validation.

### C. Sector Match (Max 30 pts)
-   keywords matching our core focus areas (Aerospace, Healthcare, Fintech, Regulatory).
-   Higher score for exact sector overlap.

### D. Disruption Signal (Max 15 pts)
-   Keywords like "Generative AI", "LLM", "Automation" indicate a technological threat to incumbents.

### Threat Levels
-   **Critical/High (80-100)**: Immediate strategic threat.
-   **High (60-80)**: Serious competitor.
-   **Medium (40-60)**: Watchlist.
-   **Low (<40)**: Noise.

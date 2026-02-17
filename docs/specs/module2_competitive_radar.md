# Module 2: Competitive Radar

## Overview
The Competitive Radar module is a high-priority system designed to providing early warning of competitive threats to portfolio companies. It monitors VC investment activity, specifically watching for when competitors raise funds from top-tier VCs, signaling potential moat erosion.

## Key Features
- **LinkedIn Surveillance**: Automated scrolling and screenshotting of investment announcements.
- **AI Analysis**: Uses Kimi (Moonshot AI) to extract structured data from unstructured feed screenshots.
- **Threat Scoring**: Algorithmically scores announcements based on VC tier, check size, and sector relevance.
- **Reporting**: Generates alerts for Critical and High threats.

## Architecture

1.  **Scraper (`linkedin_scraper.py`)**:
    - Uses Playwright to navigate LinkedIn.
    - Captures screenshots of the feed to bypass anti-scraping text obfuscation.
    - Persists session state to minimize login requirements.

2.  **Analyzer (`kimi_analyzer.py`)**:
    - Sends batches of screenshots to Moonshot AI (Kimi model).
    - Vision capabilities extract text and structured investment data.
    - Returns JSON list of announcements.

3.  **Scorer (`threat_scorer.py`)**:
    - **VC Tier (30pts)**: Bonus for Tier A (Sequoia, a16z, etc.) and Tier B firms.
    - **Round Size (25pts)**: Higher scores for larger rounds (>£20M).
    - **Sector Match (30pts)**: keyword matching against core portfolio sectors (Aerospace, Healthcare, etc.).
    - **Disruption (15pts)**: Keywords for AI, LLM, automation.
    - **Classification**:
        - 80-100: CRITICAL (Immediate action)
        - 60-79: HIGH (Monitor closely)
        - 40-59: MEDIUM
        - 0-39: LOW

4.  **Database (`database.py`)**:
    - Stores `VCFirm`, `VCAnnouncement`, and `ThreatScore` records.
    - Tracks history of investments and threats.

## Usage

### Running the Workflow
```bash
python -m src.competitive.workflow
```

### Database Initialization
The database is automatically initialized on the first run of the workflow.

## Configuration
Requires the following environment variables in `.env`:
- `MOONSHOT_API_KEY`: Key for Kimi/Moonshot AI.
- `DATABASE_URL`: Connection string (default: sqlite:///data/radar.db).

## Future Enhancements
- Integration with Crunchbase API for cross-verification.
- Email alert delivery via SendGrid.
- Dashboard visualization of threat landscape.

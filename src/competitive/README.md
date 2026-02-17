# Module 2: Competitive Radar

The **Competitive Radar** tracks Venture Capital activity to identify potential threats to our thesis or uncover new high-growth competitors.

## Key Components

### 1. VC Tracker (`src.competitive.web_monitor`)
Monitors the websites and LinkedIn pages of top-tier VC firms (e.g., Sequoia, Index, Accel) for new investment announcements.

### 2. Threat Scorer (`src.competitive.threat_scorer`)
Analyzes new VC investments against our portfolio or target watchlist.
- **Threat Level**: Low, Medium, High.
- **Scoring**: Based on sector overlap, funding amount, and investor tier.

### 3. Setup Following (`src.competitive.setup_following`)
Utility script to automatically "follow" target VCs on LinkedIn using the browser agent.

## Usage

Run the competitive monitor:
```bash
python -m src.competitive.workflow
```

# Module 11: Carveout Scanner

The **Carveout Scanner** identifies subsidiaries or divisions of large corporations that are likely candidates for divestiture (spin-offs/carveouts).

## Key Components

### 1. Structure Analysis
- **CorporateParent**: The holding company (e.g., Unilever, Siemens).
- **Division**: A specific business unit (e.g., Siemens Energy).

### 2. Carveout Probability
We calculate a probability score (0-100) based on:
- **Financial Divergence**: Division growth/margin significantly lower than group average.
- **Strategic Non-Fit**: Division operation outside core "North Star" strategy.
- **Activist Pressure**: Presence of activist investors calling for breakups.
- **News Signals**: Mentions of "strategic review", "exploring options".

## Usage

Run the carveout analysis:
```bash
python -m src.carveout.workflow
```

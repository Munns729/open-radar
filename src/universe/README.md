# Module 1: Universe Scanner

The **Universe Scanner** is responsible for identifying potential investment targets and populating the initial funnel. It continuously monitors various data sources to find companies that match our size and sector criteria.

## Key Components

### 1. Discovery Agent (`src.universe.discovery`)
Scans external sources for companies.
- **Companies House**: Queries the UK registry for companies with:
    - Revenue £15M - £100M (inferred)
    - Specific SIC codes (Technology, B2B Services)
- **LinkedIn**: Discovers companies via "similar to" and employee growth signals.

### 2. Moat Scorer (`src.universe.moat_scorer`)
Assigns a 0-100 score based on the **5-Pillar Analysis**:
1.  **Regulatory (Lock)**: Licenses, compliance barriers.
2.  **Network Effects (Share)**: User adoption value loops.
3.  **IP (Shield)**: Patents, proprietary tech.
4.  **Brand (Award)**: Reputation, customer loyalty.
5.  **Cost (Coins)**: Scale, unique resource access.

### 3. Workflow (`src.universe.workflow`)
Orchestrates the scanning process:
1.  Run `DiscoveryAgent` to find new raw companies.
2.  Enrich data using **Kimi AI**.
3.  Run `MoatScorer` to grade the company.
4.  Save to `CompanyModel` in database.

## Usage

Run the scanner manually:
```bash
python -m src.universe.workflow
```

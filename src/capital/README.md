# Module 10: Capital Flows

The **Capital Flows** module tracks the "Money" side of the equation. It monitors Private Equity firms, their dry powder, and their investment activity.

## Key Components

### 1. PE Firm Discovery (`PEWebsiteAgent`)
Scrapes PE firm websites to extract:
- **Portfolio Companies**: Historical and current investments.
- **Team**: Key partners and investment leads.
- **Focus**: Target sectors and check sizes.

### 2. Investment Database
Stores `PEInvestment` records to build a map of who is buying what. This data feeds into the **Deal Intelligence** comparables engine.

## Usage

Run the capital flows scanner:
```bash
python -m src.capital.workflow
```

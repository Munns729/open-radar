# Module 10: Capital Flows

The **Capital Flows** module tracks the "Money" side of the equation. It monitors Private Equity firms, their dry powder, and their investment activity.

## PE Firm Discovery Sources

| Source | Region | Config | Description |
|--------|--------|--------|-------------|
| **SEC Edgar** | US | — | Investment Adviser Public Disclosure |
| **FCA Register** | UK | `FCA_API_EMAIL`, `FCA_API_KEY` | UK Financial Services Register. [Free registration](https://register.fca.org.uk/Developer/s/) |
| **IMERGEA Atlas** | Europe | — | Free PE/VC directory at [imergea.com/atlas](https://imergea.com/atlas/atlas.html) |

## Usage

```bash
# All sources (SEC + FCA + IMERGEA)
python -m src.capital.workflow

# Europe-only (UK + EU)
python -m src.capital.workflow --sources FCA IMERGEA

# UK-only
python -m src.capital.workflow --sources FCA
```

## Key Components

### 1. PE Firm Discovery
- **SECEdgarAgent**: US PE firms
- **FCARegisterScraper**: UK PE firms (FCA API)
- **IMERGEAAtlasScraper**: European PE firms

### 2. Portfolio Enrichment (`PEWebsiteAgent`)
Scrapes PE firm websites for portfolio companies.

### 3. Investment Database
Stores `PEInvestment` records. Feeds into **Deal Intelligence** and **Thesis Validator**.

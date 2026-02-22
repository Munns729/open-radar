# Universe scrapers

Scrapers are grouped by how they fetch data:

- **`base.py`** — Shared bases: `BaseScraper` (Playwright lifecycle, `safe_goto`/retry) and `ApiScraper` (aiohttp session, rate limiting, `_get`/`_post` with retry and 429). All scrapers (universe and other modules) import from `from src.universe.scrapers.base import BaseScraper, ApiScraper`.

- **`api/`** — REST/JSON APIs (aiohttp). Fixed-target endpoints (Companies House, TED, BOAMP, SIRENE, BSI, Contracts Finder, OpenCorporates). New API scrapers should inherit from `ApiScraper` (from `scrapers.base`).

- **`browser/`** — Playwright-based. Page navigation and DOM extraction (AS9100, Wikipedia, Clutch, G-Cloud, website scraping, etc.). New browser scrapers should inherit from `BaseScraper` (from `scrapers.base`).

The package root re-exports all scraper classes so callers can use `from src.universe.scrapers import CompaniesHouseScraper, ...` without referencing `api` or `browser`.

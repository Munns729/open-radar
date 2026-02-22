"""
Universe scrapers: discovery and enrichment from external sources.

- base.py — BaseScraper (Playwright), ApiScraper (aiohttp).
- api/   — REST/JSON APIs (aiohttp): Companies House, TED, BOAMP, SIRENE, etc.
- browser/ — Playwright: AS9100, Wikipedia, Clutch, G-Cloud, website scraping, etc.
"""
from .base import BaseScraper, ApiScraper
from .api import (
    CompaniesHouseScraper,
    CompaniesHouseDiscoveryScraper,
    ContractsFinderScraper,
    SIRENEScraper,
    TEDScraper,
    BOAMPScraper,
    BSIScraper,
    OpenCorporatesScraper,
)
from .browser import (
    AS9100Scraper,
    WebsiteScraper,
    GCloudScraper,
    WikipediaDiscoveryScraper,
    ClutchDiscoveryScraper,
    GoodFirmsAgentScraper,
    CrunchbaseDiscoveryScraper,
    ISORegistryScraper,
    DeloitteFast50Scraper,
    FT1000Scraper,
    VerticalAssociationsScraper,
    UGAPScraper,
    GoodFirmsDiscoveryScraper,
    ANSSIScraper,
)

__all__ = [
    "BaseScraper",
    "ApiScraper",
    "AS9100Scraper",
    "CompaniesHouseScraper",
    "CompaniesHouseDiscoveryScraper",
    "ClutchDiscoveryScraper",
    "ContractsFinderScraper",
    "CrunchbaseDiscoveryScraper",
    "GoodFirmsAgentScraper",
    "ISORegistryScraper",
    "SIRENEScraper",
    "WikipediaDiscoveryScraper",
    "GCloudScraper",
    "UGAPScraper",
    "TEDScraper",
    "BOAMPScraper",
    "ANSSIScraper",
    "BSIScraper",
    "OpenCorporatesScraper",
    "DeloitteFast50Scraper",
    "FT1000Scraper",
    "VerticalAssociationsScraper",
    "GoodFirmsDiscoveryScraper",
    "WebsiteScraper",
]

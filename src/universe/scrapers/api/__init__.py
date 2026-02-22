"""API-based scrapers (aiohttp/httpx). Fixed-target REST APIs for company/contract data."""
from .companies_house_scraper import CompaniesHouseScraper
from .companies_house_discovery import CompaniesHouseDiscoveryScraper
from .contracts_finder_scraper import ContractsFinderScraper
from .sirene_scraper import SIRENEScraper
from .ted_scraper import TEDScraper
from .boamp_scraper import BOAMPScraper
from .bsi_scraper import BSIScraper
from .opencorporates_scraper import OpenCorporatesScraper

__all__ = [
    "CompaniesHouseScraper",
    "CompaniesHouseDiscoveryScraper",
    "ContractsFinderScraper",
    "SIRENEScraper",
    "TEDScraper",
    "BOAMPScraper",
    "BSIScraper",
    "OpenCorporatesScraper",
]

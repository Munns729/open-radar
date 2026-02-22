"""Browser-based scrapers (Playwright). Page navigation and DOM extraction."""
from .as9100_scraper import AS9100Scraper
from .website_scraper import WebsiteScraper
from .g_cloud_scraper import GCloudScraper
from .wikipedia_discovery import WikipediaDiscoveryScraper
from .clutch_discovery import ClutchDiscoveryScraper
from .goodfirms_agent import GoodFirmsAgentScraper
from .crunchbase_scraper import CrunchbaseDiscoveryScraper
from .iso_registry_scraper import ISORegistryScraper
from .growth_scrapers import DeloitteFast50Scraper, FT1000Scraper
from .vertical_associations_scraper import VerticalAssociationsScraper
from .ugap_scraper import UGAPScraper
from .goodfirms_discovery import GoodFirmsDiscoveryScraper
from .anssi_scraper import ANSSIScraper

__all__ = [
    "AS9100Scraper",
    "WebsiteScraper",
    "GCloudScraper",
    "WikipediaDiscoveryScraper",
    "ClutchDiscoveryScraper",
    "GoodFirmsAgentScraper",
    "CrunchbaseDiscoveryScraper",
    "ISORegistryScraper",
    "DeloitteFast50Scraper",
    "FT1000Scraper",
    "VerticalAssociationsScraper",
    "UGAPScraper",
    "GoodFirmsDiscoveryScraper",
    "ANSSIScraper",
]

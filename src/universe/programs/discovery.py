"""
Discovery program: Run scrapers to find companies.
Zone 1: Scraper registry + dispatch.
"""
import logging
from typing import Callable, List, Optional

from src.universe.programs._shared import save_companies
from src.universe.scrapers import (
    AS9100Scraper,
    CompaniesHouseDiscoveryScraper,
    ClutchDiscoveryScraper,
    ContractsFinderScraper,
    CrunchbaseDiscoveryScraper,
    GoodFirmsAgentScraper,
    ISORegistryScraper,
    SIRENEScraper,
    WikipediaDiscoveryScraper,
)
from src.universe.scrapers.g_cloud_scraper import GCloudScraper
from src.universe.scrapers.ugap_scraper import UGAPScraper
from src.universe.scrapers.ted_scraper import TEDScraper
from src.universe.scrapers.boamp_scraper import BOAMPScraper
from src.universe.scrapers.anssi_scraper import ANSSIScraper
from src.universe.scrapers.bsi_scraper import BSIScraper
from src.universe.scrapers.growth_scrapers import DeloitteFast50Scraper, FT1000Scraper
from src.universe.scrapers.vertical_associations_scraper import VerticalAssociationsScraper
from src.universe.status import reporter

logger = logging.getLogger(__name__)


async def _run_as9100(session, *, countries=None, limit=15):
    async with AS9100Scraper() as scraper:
        data = await scraper.scrape_by_country("United Kingdom")
    return await save_companies(session, data.data, "AS9100")


async def _run_iso9001(session, *, countries=None, limit=15):
    async with ISORegistryScraper() as scraper:
        data = await scraper.scrape_iso9001()
    return await save_companies(session, data.data, "ISO9001")


async def _run_wikipedia(session, *, countries=None, limit=15):
    target_regions = countries if countries else ["FR", "DE", "NL", "BE", "LU"]
    valid_codes = ["FR", "DE", "NL", "BE"]
    total = 0
    async with WikipediaDiscoveryScraper() as scraper:
        for code in target_regions:
            if code in valid_codes:
                data = await scraper.discover_region(code, limit=limit)
                total += await save_companies(session, data.data, f"Wiki-Discovery-{code}")
    return total


async def _run_clutch(session, *, countries=None, limit=15):
    clutch_targets = countries if countries else ["FR", "DE"]
    total = 0
    async with ClutchDiscoveryScraper() as scraper:
        for code in clutch_targets:
            if code in ["FR", "DE", "UK", "NL", "PL"]:
                data = await scraper.discover_tech_services(code, limit=limit)
                total += await save_companies(session, data.data, f"Clutch-Discovery-{code}")
    return total


async def _run_goodfirms(session, *, countries=None, limit=15):
    gf_targets = countries if countries else ["FR"]
    country_map = {"FR": "France", "DE": "Germany", "UK": "United Kingdom", "NL": "Netherlands"}
    total = 0
    async with GoodFirmsAgentScraper(headless=True) as scraper:
        for code in gf_targets:
            country_name = country_map.get(code)
            if country_name:
                for term in ["Cybersecurity", "Artificial Intelligence"]:
                    data = await scraper.discover(term=term, country=country_name, limit=limit)
                    total += await save_companies(session, data.data, f"GoodFirms-Agent-{code}-{term}")
    return total


async def _run_crunchbase(session, *, countries=None, limit=15):
    cb_targets = countries if countries else ["UK", "Europe"]
    total = 0
    async with CrunchbaseDiscoveryScraper() as scraper:
        for code in cb_targets:
            data = await scraper.discover_companies(code, limit=15)
            total += await save_companies(session, data.data, f"Crunchbase-{code}")
    return total


async def _run_companieshouse(session, *, countries=None, limit=15):
    async with CompaniesHouseDiscoveryScraper() as scraper:
        data = await scraper.scrape(limit=max(limit or 50, 50))
    return await save_companies(session, data.data, "CompaniesHouse-UK")


async def _run_contractsfinder(session, *, countries=None, limit=15):
    async with ContractsFinderScraper() as scraper:
        data = await scraper.scrape(limit=max(limit or 30, 30))
    return await save_companies(session, data.data, "ContractsFinder-UK")


async def _run_sirene(session, *, countries=None, limit=15):
    async with SIRENEScraper() as scraper:
        data = await scraper.scrape(limit=max(limit or 50, 50))
    return await save_companies(session, data.data, "SIRENE-FR")


async def _run_gcloud(session, *, countries=None, limit=15):
    async with GCloudScraper() as scraper:
        data = await scraper.scrape(target_lots=["cloud-support"], limit_per_lot=20)
    return await save_companies(session, data.data, "G-Cloud-UK")


async def _run_ugap(session, *, countries=None, limit=15):
    async with UGAPScraper() as scraper:
        data = await scraper.scrape(limit=20)
    return await save_companies(session, data.data, "UGAP-FR")


async def _run_ted(session, *, countries=None, limit=15):
    ted_countries = countries if countries else ["DE", "NL", "BE"]
    async with TEDScraper() as scraper:
        data = await scraper.scrape(
            countries=ted_countries,
            limit_per_country=max(limit or 15, 15),
        )
    return await save_companies(session, data.data, "TED-EU")


async def _run_boamp(session, *, countries=None, limit=15):
    async with BOAMPScraper() as scraper:
        data = await scraper.scrape(limit=max(limit or 20, 20))
    return await save_companies(session, data.data, "BOAMP-FR")


async def _run_anssi(session, *, countries=None, limit=15):
    async with ANSSIScraper(headless=True) as scraper:
        data = await scraper.scrape(limit=max(limit or 30, 30))
    return await save_companies(session, data.data, "ANSSI-FR")


async def _run_bsi(session, *, countries=None, limit=15):
    async with BSIScraper() as scraper:
        data = await scraper.scrape(limit=max(limit or 50, 50))
    return await save_companies(session, data.data, "BSI-DE")


async def _run_deloitte(session, *, countries=None, limit=15):
    async with DeloitteFast50Scraper() as scraper:
        data = await scraper.scrape(region="UK")
    return await save_companies(session, data, "DeloitteFast50-UK")


async def _run_ft1000(session, *, countries=None, limit=15):
    async with FT1000Scraper() as scraper:
        data = await scraper.scrape()
    return await save_companies(session, data, "FT1000-Europe")


async def _run_verticals(session, *, countries=None, limit=15):
    async with VerticalAssociationsScraper() as scraper:
        data = await scraper.scrape()
    return await save_companies(session, data, "VerticalAssocs")


# Fast50 is an alias for Deloitte
async def _run_fast50(session, *, countries=None, limit=15):
    return await _run_deloitte(session, countries=countries, limit=limit)


SCRAPER_REGISTRY: dict[str, Callable] = {
    "AS9100": _run_as9100,
    "ISO9001": _run_iso9001,
    "Wikipedia": _run_wikipedia,
    "Clutch": _run_clutch,
    "GoodFirms": _run_goodfirms,
    "Crunchbase": _run_crunchbase,
    "CompaniesHouse": _run_companieshouse,
    "ContractsFinder": _run_contractsfinder,
    "GCloud": _run_gcloud,
    "SIRENE": _run_sirene,
    "UGAP": _run_ugap,
    "TED": _run_ted,
    "BOAMP": _run_boamp,
    "ANSSI": _run_anssi,
    "BSI": _run_bsi,
    "Deloitte": _run_deloitte,
    "Fast50": _run_fast50,
    "FT1000": _run_ft1000,
    "Verticals": _run_verticals,
}


async def run_discovery(
    session,
    sources: List[str],
    countries: Optional[List[str]] = None,
    limit: int = 15,
) -> int:
    """
    Discovery program: Run scrapers to find companies. Saves readily available data
    (descriptions, revenue, sector, certifications) — no website discovery or enrichment.
    Returns count of new companies saved.
    """
    print("\n" + "=" * 50)
    print("[PROGRAM] Discovery — Scrapers only, no website discovery")
    print("=" * 50 + "\n")
    reporter.set_zone(1, "Discovery Phase")

    total = 0
    for source in sources:
        if source not in SCRAPER_REGISTRY:
            logger.warning(f"Unknown source: {source}")
            continue
        try:
            n = await SCRAPER_REGISTRY[source](session, countries=countries, limit=limit)
            total += n
        except Exception as e:
            logger.warning(f"Discovery source {source} failed: {e}")

    logger.info(f"Discovery complete: {total} new companies saved")
    return total

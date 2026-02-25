"""
Capital Flows Workflow.
Orchestrates the scraping, analysis, and reporting pipeline.
"""
import asyncio
import logging
from typing import List, Optional
from sqlalchemy import select, func
from src.core.database import engine, get_async_db

from src.core.config import settings
from src.capital.database import Base, PEFirmModel, PEInvestmentModel
from src.capital.scrapers.sec_edgar import SECEdgarAgent
from src.capital.scrapers.pe_websites import PEWebsiteAgent
from src.capital.scrapers.fca_register import FCARegisterScraper
from src.capital.scrapers.imergea_atlas import IMERGEAAtlasScraper
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default sources: SEC (US) + FCA (UK) + IMERGEA (Europe) when configured
DEFAULT_SOURCES = ["SEC", "FCA", "IMERGEA"]


async def _store_firms(session, firms_data: List[dict], strategy: str, default_country: str) -> int:
    """Store discovered firms, deduplicating by name. Returns count of new firms added."""
    term_new = 0
    for firm in firms_data:
        firm_name = firm.get("name") or firm.get("Name")
        if not firm_name:
            continue
        hq_country = firm.get("hq_country") or firm.get("location") or firm.get("Location") or default_country
        result = await session.execute(select(PEFirmModel).where(PEFirmModel.name == firm_name))
        existing = result.scalar_one_or_none()
        if not existing:
            logger.info("Adding NEW firm: %s", firm_name)
            session.add(PEFirmModel(
                name=firm_name,
                hq_country=hq_country,
                aum_usd=0,
                investment_strategy=strategy,
            ))
            term_new += 1
    await session.commit()
    return term_new


async def scan_capital_flows(sources: Optional[List[str]] = None):
    """
    Main entry point for capital flows scanning.
    sources: List of "SEC", "FCA", "IMERGEA" - which discovery sources to run.
    Defaults to all three (SEC for US, FCA for UK, IMERGEA for Europe).
    """
    sources = sources or DEFAULT_SOURCES
    logger.info("Starting Capital Flows Scan (sources: %s)...", sources)
    
    # 1. Database Setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with get_async_db() as session:
        try:
            total_new = 0

            # 2a. SEC (US) - PE firm discovery
            if "SEC" in sources:
                logger.info("Scraping SEC for US PE Firms...")
                sec_agent = SECEdgarAgent(headless=True, model_name=settings.browsing_model)
                for term in ["Growth Equity", "Venture Capital"]:
                    try:
                        firms_data = await sec_agent.run(search_term=term)
                        term_new = await _store_firms(session, firms_data, term, default_country="US")
                        total_new += term_new
                    except Exception as e:
                        logger.error(f"SEC term '{term}' failed: {e}")
                        await session.rollback()

            # 2b. FCA Register (UK) - PE firm discovery
            if "FCA" in sources:
                logger.info("Scraping FCA Register for UK PE Firms...")
                try:
                    fca_scraper = FCARegisterScraper()
                    firms_data = fca_scraper.scrape(limit_per_term=30)
                    term_new = await _store_firms(session, firms_data, "FCA-UK", default_country="UK")
                    total_new += term_new
                except Exception as e:
                    logger.warning("FCA Register skipped or failed: %s", e)
                    await session.rollback()

            # 2c. IMERGEA Atlas (Europe) - PE firm discovery
            if "IMERGEA" in sources:
                logger.info("Scraping IMERGEA Atlas for European PE Firms...")
                try:
                    imergea_agent = IMERGEAAtlasScraper(headless=True, model_name=settings.browsing_model)
                    firms_data = await imergea_agent.run(region="Europe", firm_type="PE", limit=80)
                    term_new = await _store_firms(session, firms_data, "IMERGEA-EU", default_country="EU")
                    total_new += term_new
                except Exception as e:
                    logger.warning("IMERGEA Atlas skipped or failed: %s", e)
                    await session.rollback()

            logger.info(f"Total new firms added: {total_new}")
            
            if total_new == 0: # If scrape failed, verify DB content
                 # Check database count if scraped count is 0, to be sure
                try:
                    result = await session.execute(select(func.count(PEFirmModel.id)))
                    total_new = result.scalar() or 0
                except Exception:
                     pass # keep as 0 if DB error
            
            # 3. Scrape Portfolios for Top Firms (Enrichment)
            logger.info("Starting Portfolio Enrichment...")
            # Get firms without websites first, or all firms?
            # For this run, get top 10 firms by AUM (or just all valid ones)
            result = await session.execute(select(PEFirmModel).limit(10))
            firms_to_enrich = result.scalars().all()
            
            from src.capital.scrapers.url_finder import UrlFinderAgent
            
            url_agent = UrlFinderAgent(headless=True, model_name=settings.browsing_model)
            pe_agent = PEWebsiteAgent(headless=True, model_name=settings.browsing_model) # Headless for speed? or False for complex sites?
            # Use headless=False if debugging, but True for prod
            
            for firm in firms_to_enrich:
                if not firm.website:
                    logger.info(f"Finding URL for {firm.name}...")
                    found_url = await url_agent.run(firm.name)
                    if found_url:
                        firm.website = found_url
                        await session.commit()
                
                if firm.website:
                    logger.info(f"Scraping portfolio for {firm.name} at {firm.website}...")
                    try:
                        portfolio = await pe_agent.run(firm.website)
                        logger.info(f"Found {len(portfolio)} companies for {firm.name}")
                        
                        for co in portfolio:
                            # Extract parsed fields
                            c_name = co.get('name') or co.get('Company Name')
                            if not c_name: continue

                            inv = PEInvestmentModel(
                                pe_firm_id=firm.id,
                                company_name=c_name,
                                sector=co.get('sector') or co.get('Industry'),
                                description=co.get('description') or co.get('Business Description'),
                                is_exited=(str(co.get('status')).lower() in ['exited', 'realized'])
                            )
                            session.add(inv)

                            try:
                                from src.universe.database import CompanyModel
                                from src.canon.service import get_or_create_canon

                                matched_result = await session.execute(
                                    select(CompanyModel).where(
                                        CompanyModel.name.ilike(f"%{c_name}%")
                                    ).limit(1)
                                )
                                matched_co = matched_result.scalar_one_or_none()
                                if matched_co:
                                    await get_or_create_canon(matched_co.id)
                            except Exception as e:
                                logger.error("Canon initialisation failed for %s: %s", c_name, e)

                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to scrape {firm.website}: {e}")
            
            logger.info("Scan complete.")
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Capital Flows Scanner")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=DEFAULT_SOURCES,
        choices=["SEC", "FCA", "IMERGEA"],
        help="Discovery sources: SEC (US), FCA (UK), IMERGEA (Europe). Default: all",
    )
    args = parser.parse_args()
    asyncio.run(scan_capital_flows(sources=args.sources))

"""
Capital Flows Workflow.
Orchestrates the scraping, analysis, and reporting pipeline.
"""
import asyncio
import logging
from typing import List
from sqlalchemy import select, func
from src.core.database import engine, get_async_db

from src.core.config import settings
from src.capital.database import Base, PEFirmModel, PEInvestmentModel
from src.capital.scrapers.sec_edgar import SECEdgarAgent
from src.capital.scrapers.pe_websites import PEWebsiteAgent
from src.capital.analyzers.thesis_validator import ThesisValidator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scan_capital_flows():
    """
    Main entry point for capital flows scanning.
    """
    logger.info("Starting Capital Flows Scan...")
    
    # 1. Database Setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with get_async_db() as session:
        try:
            # 2. Scrape SEC for PE Firms (Multi-Keyword)
            logger.info("Scraping SEC for PE Firms...")
            sec_agent = SECEdgarAgent(headless=True, model_name=settings.kimi_model)
            
            SEARCH_TERMS = [
                # "Private Equity", # Skip common one for now to verify expansion
                "Growth Equity",
                "Venture Capital" 
            ]
            
            total_new = 0
            for term in SEARCH_TERMS:
                logger.info(f"Scanning for term: '{term}'...")
                try:
                    firms_data = await sec_agent.run(search_term=term)
                    
                    logger.info(f"Term '{term}' returned {len(firms_data)} raw results.")
                    
                    # Store firms
                    term_new = 0
                    for firm in firms_data:
                        firm_name = firm.get('name')
                        if not firm_name: continue
                        
                        # Robust upsert
                        # Check partial match/case insensitive? For now exact match on name.
                        result = await session.execute(select(PEFirmModel).where(PEFirmModel.name == firm_name))
                        existing = result.scalar_one_or_none()
                        
                        if not existing:
                            logger.info(f"Adding NEW firm: {firm_name}")
                            new_firm = PEFirmModel(
                                name=firm_name,
                                hq_country=firm.get('location', 'US'), # Map location to country loosely
                                aum_usd=0, # Default
                                investment_strategy=term 
                            )
                            session.add(new_firm)
                            term_new += 1
                    
                    await session.commit()
                    logger.info(f"Committed {term_new} new firms for '{term}'.")
                    total_new += term_new
                    
                except Exception as e:
                    logger.error(f"Error processing term '{term}': {e}")
                    await session.rollback() # Rollback only this term's batch
                
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
            
            url_agent = UrlFinderAgent(headless=True, model_name=settings.kimi_model)
            pe_agent = PEWebsiteAgent(headless=True, model_name=settings.kimi_model) # Headless for speed? or False for complex sites?
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
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to scrape {firm.website}: {e}")
            
            # 4. Run Thesis Validation
            logger.info("Running Thesis Validation...")
            validator = ThesisValidator(session)
            report = await validator.generate_report()
            
            logger.info("Scan Complete. Thesis Report:")
            for item in report:
                logger.info(f"{item['hypothesis']}: {item['supports_thesis']}")
                
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    # Example usage
    asyncio.run(scan_capital_flows())

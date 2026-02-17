
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import Config
from src.capital.database import PEFirmModel, PEInvestmentModel
from src.capital.scrapers.enrichment_agent import CompanyEnrichmentAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Reduce Playwright logging
logging.getLogger("playwright").setLevel(logging.WARNING)

async def enrich_firm(firm_name: str, batch_size: int = 5):
    """Enrich companies for a specific firm."""
    
    engine = create_engine(Config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        firm = session.query(PEFirmModel).filter_by(name=firm_name).first()
        if not firm:
            logger.error(f"Firm {firm_name} not found.")
            return
            
        # Get unenriched companies
        companies = session.query(PEInvestmentModel).filter_by(
            pe_firm_id=firm.id,
            is_enriched=False  # Only pick unenriched ones
        ).filter(
            PEInvestmentModel.investment_thesis.is_(None)
        ).limit(batch_size).all()
        
        if not companies:
            logger.info(f"No unenriched companies found for {firm_name}.")
            return
            
        logger.info(f"Enriching {len(companies)} companies for {firm_name}...")
        
        agent = CompanyEnrichmentAgent(headless=True) # Use same agent? Or new per company? 
        # BaseBrowsingAgent starts/stops browser in run() usually or start().
        # Actually CompanyEnrichmentAgent.run() calls start() and stop().
        # So we should verify if we can reuse it or create new one.
        # run() calls start() which launches browser. stop() closes it.
        # So we create a new instance each time or modify run to not close if we want reuse.
        # For safety/simplicity, new instance per company (slower but robust).
        
        for i, company in enumerate(companies):
            try:
                logger.info(f"[{i+1}/{len(companies)}] Enriching {company.company_name}...")
                
                # Create fresh agent for clean state
                company_agent = CompanyEnrichmentAgent(headless=True)
                
                data = await company_agent.run(
                    company_name=company.company_name, 
                    pe_firm_website=firm.website,
                    direct_url=None # Let it find it via search/click
                )
                
                if data.get("investment_thesis"):
                    company.investment_thesis = data["investment_thesis"]
                    company.strategic_rationale = str(data["strategic_rationale"])
                    company.target_moats = str(data["pe_identified_moats"])
                    company.exit_thesis = data["exit_thesis"]
                    company.investment_year = data["investment_year"]
                    company.exit_year = data["exit_year"]
                    company.entry_valuation_usd = data.get("entry_valuation_usd")
                    company.moic = data.get("moic")
                    company.is_enriched = True
                    company.enriched_at = logging.datetime.datetime.utcnow()
                    
                    session.commit()
                    logger.info(f"Saved data for {company.company_name}")
                else:
                    logger.warning(f"No data found for {company.company_name}")
            
            except Exception as e:
                logger.error(f"Error enriching {company.company_name}: {e}")
                session.rollback()
                
    finally:
        session.close()

async def main():
    # Enrich Mayfair and Synova
    # Synova has specialized button handling in the agent, so it should work.
    
    await enrich_firm("Mayfair Equity Partners", batch_size=5)
    await enrich_firm("Synova", batch_size=5)

if __name__ == "__main__":
    asyncio.run(main())

"""
Enrich portfolio companies with investment theses from PE firm websites.
Run this script opportunistically to add context to existing portfolio data.
"""
import sys
import os
sys.path.append(os.getcwd())

import asyncio
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import Config
from src.capital.database import PEFirmModel, PEInvestmentModel
from src.capital.scrapers.enrichment_agent import CompanyEnrichmentAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enrichment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Enrichment")

async def enrich_companies(
    pe_firm_name: str = None,
    limit: int = None,
    only_unenriched: bool = True
):
    """
    Enrich portfolio companies with investment theses.
    
    Args:
        pe_firm_name: Optional - only enrich companies from this PE firm
        limit: Optional - max number of companies to enrich
        only_unenriched: If True, skip already enriched companies
    """
    engine = create_engine(Config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Build query
        query = session.query(PEInvestmentModel).join(PEFirmModel)
        
        if pe_firm_name:
            query = query.filter(PEFirmModel.name.like(f'%{pe_firm_name}%'))
        
        if only_unenriched:
            query = query.filter(PEInvestmentModel.is_enriched == False)
        
        companies = query.limit(limit).all() if limit else query.all()
        
        logger.info(f"Found {len(companies)} companies to enrich")
        
        enriched_count = 0
        failed_count = 0
        
        for company in companies:
            pe_firm = session.query(PEFirmModel).filter_by(id=company.pe_firm_id).first()
            
            if not pe_firm or not pe_firm.website:
                logger.warning(f"Skipping {company.company_name} - no PE firm website")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Enriching: {company.company_name}")
            logger.info(f"PE Firm: {pe_firm.name}")
            logger.info(f"Website: {pe_firm.website}")
            logger.info(f"{'='*60}")
            
            try:
                agent = CompanyEnrichmentAgent(
                    headless=True,
                    model_name=Config.KIMI_MODEL
                )
                
                enrichment_data = await agent.run(
                    company_name=company.company_name,
                    pe_firm_website=pe_firm.website
                )
                
                # Update database
                if enrichment_data.get("investment_thesis"):
                    company.investment_thesis = enrichment_data.get("investment_thesis")
                    company.strategic_rationale = enrichment_data.get("strategic_rationale")
                    company.exit_thesis = enrichment_data.get("exit_thesis")
                    company.deal_announcement_url = enrichment_data.get("deal_announcement_url")
                    company.investment_year = enrichment_data.get("investment_year")
                    company.exit_year = enrichment_data.get("exit_year")
                    company.pe_identified_moats = enrichment_data.get("pe_identified_moats")
                    company.thesis_keywords = enrichment_data.get("thesis_keywords")
                    company.is_enriched = True
                    company.enriched_at = datetime.utcnow()
                    
                    session.commit()
                    enriched_count += 1
                    
                    logger.info(f"✓ Enriched {company.company_name}")
                    logger.info(f"  Thesis: {enrichment_data.get('investment_thesis', 'N/A')[:100]}...")
                    
                else:
                    logger.warning(f"✗ No thesis found for {company.company_name}")
                    failed_count += 1
                
            except Exception as e:
                logger.exception(f"Failed to enrich {company.company_name}: {e}")
                failed_count += 1
                session.rollback()
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ENRICHMENT COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✓ Successfully enriched: {enriched_count}")
        logger.info(f"✗ Failed: {failed_count}")
        
    except Exception as e:
        logger.exception(f"Enrichment workflow failed: {e}")
        session.rollback()
    finally:
        session.close()

async def test_single_company():
    """Test enrichment on a single company"""
    await enrich_companies(
        pe_firm_name="Silver Lake",
        limit=1,
        only_unenriched=True
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich portfolio companies with investment theses')
    parser.add_argument('--firm', type=str, help='PE firm name to filter by')
    parser.add_argument('--limit', type=int, help='Max number of companies to enrich')
    parser.add_argument('--all', action='store_true', help='Enrich all companies (including already enriched)')
    parser.add_argument('--test', action='store_true', help='Test on single company from Silver Lake')
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_single_company())
    else:
        asyncio.run(enrich_companies(
            pe_firm_name=args.firm,
            limit=args.limit,
            only_unenriched=not args.all
        ))

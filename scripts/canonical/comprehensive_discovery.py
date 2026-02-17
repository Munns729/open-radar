"""
Comprehensive Universe Discovery Script.
Iterates through key SIC codes AND incorporation years to discover all registered UK companies.
Sharding by year allows bypassing the 5,000-10,000 offset limit of the API.
"""
import asyncio
import logging
from typing import List
from src.universe.scrapers.companies_house_scraper import CompaniesHouseScraper
from src.universe.database import CompanyModel, CertificationModel
from src.universe.workflow import SessionLocal, init_db, run_scoring
from src.universe.moat_scorer import MoatScorer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Discovery")

# Target SIC Codes
SIC_CODES = {
    "Aerospace & Defense": [
        "30300", "25400", "30400"
    ],
    "High-Tech Manufacturing": [
        "26110", "26120", "26200", "26301", "26309", "26400", "26511", "26513", "26600", "26701", "27900"
    ],
    "Software & Services": [
        "62012", "62020", "62090", "63110"
    ]
}

async def save_batch(session, companies_data: List[dict], sector_tag: str):
    count = 0
    for item in companies_data:
        co_number = item.get('company_number')
        exists = session.query(CompanyModel).filter(CompanyModel.companies_house_number == co_number).first()
        
        if not exists:
            c = CompanyModel(
                name=item.get('company_name'),
                legal_name=item.get('company_name'),
                companies_house_number=co_number,
                hq_country="GB",
                hq_address=item.get('registered_office_address', {}).get('locality', 'UK'),
                sector=item.get('company_type', '') + f" ({sector_tag})",
                sic_codes=item.get('sic_codes', []),
                discovered_via=f"SIC Discovery ({sector_tag})"
            )
            session.add(c)
            count += 1
    session.commit()
    return count

async def run_discovery_sharded(start_year=2000, end_year=2025):
    await init_db()
    session = SessionLocal()
    
    async with CompaniesHouseScraper() as scraper:
        total_discovered = 0
        
        for sector, sics in SIC_CODES.items():
            logger.info(f"--- Starting Sector: {sector} ---")
            
            for sic in sics:
                logger.info(f"Scanning SIC {sic} by year ({start_year}-{end_year})...")
                
                for year in range(start_year, end_year + 1):
                    # Define date range for this shard
                    date_from = f"{year}-01-01"
                    date_to = f"{year}-12-31"
                    
                    start_index = 0
                    has_more = True
                    shard_count = 0
                    
                    while has_more:
                        try:
                            # Add delay between pages
                            await asyncio.sleep(0.2)
                            
                            results = await scraper.advanced_search(
                                [sic], 
                                start_index=start_index,
                                incorporated_from=date_from,
                                incorporated_to=date_to
                            )
                            
                            if not results:
                                has_more = False
                                break
                                
                            new_count = await save_batch(session, results, sector)
                            total_discovered += new_count
                            shard_count += len(results)
                            
                            if len(results) < 100:
                                has_more = False
                            else:
                                start_index += len(results)
                                
                            # Safety limit per year shard (shouldn't hit API limit easily now)
                            if start_index > 4000: 
                                has_more = False
                                
                        except Exception as e:
                            logger.error(f"Error SIC {sic} Year {year} offset {start_index}: {e}")
                            has_more = False
                    
                    logger.info(f"SIC {sic} [{year}]: Found {shard_count} companies.")

        session.close()
        logger.info(f"Deep Discovery Complete. Total New: {total_discovered}")
        
    logger.info("Running scoring pass...")
    session = SessionLocal()
    await run_scoring(session)
    session.close()

if __name__ == "__main__":
    asyncio.run(run_discovery_sharded(1995, 2025))

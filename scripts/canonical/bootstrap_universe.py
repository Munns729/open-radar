"""
Bootstrap the Universe with a manual list of targets.
Useful when scrapers are blocked or in early development.
"""
import asyncio
import logging
from src.universe.database import CompanyModel
from src.universe.workflow import enrich_companies, run_scoring, SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bootstrap")

TARGETS = [
    # Aerospace / Defense
    "BAE Systems plc",
    "Rolls-Royce plc",
    "Babcock International Group",
    "QinetiQ Group plc",
    "Meggitt", # Acquired but historically relevant
    "Cobham", # Acquired
    "Ultra Electronics",
    "Senior plc",
    "Chemring Group",
    "Avon Protection",
    
    # Tech / Semi
    "Arm Limited",
    "Graphcore",
    "Darktrace",
    "Oxford Instruments",
    "Renishaw plc",
    "Spirent Communications",
    "Spectris",
    "Halma plc",
    "Softcat",
    "Computacenter",
    
    # Space
    "Surrey Satellite Technology",
    "Clyde Space",
    "Reaction Engines",
    
    # Other Industrials
    "Rotork",
    "Spirax-Sarco Engineering",
    "Melrose Industries",
    "Smiths Group"
]

async def bootstrap():
    await init_db()
    session = SessionLocal()
    
    count = 0
    for name in TARGETS:
        exists = session.query(CompanyModel).filter(CompanyModel.name == name).first()
        if not exists:
            logger.info(f"Adding {name}...")
            c = CompanyModel(
                name=name, 
                hq_country="GB", 
                discovered_via="Bootstrap"
            )
            session.add(c)
            count += 1
    
    session.commit()
    logger.info(f"Added {count} new companies.")
    
    if count > 0:
        logger.info("Enriching with Companies House data...")
        await enrich_companies(session)
        
        logger.info("Running Scoring...")
        await run_scoring(session)
        
    session.close()

if __name__ == "__main__":
    asyncio.run(bootstrap())

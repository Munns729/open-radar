
import sys
import os
sys.path.append(os.getcwd())

import asyncio
import logging
from sqlalchemy import select, func, text
from sqlalchemy.orm import sessionmaker
from src.core.database import async_session_factory, engine
from src.universe.database import CompanyModel, CertificationModel
from src.capital.database import PEFirmModel, PEInvestmentModel
from src.deal_intelligence.database import DealRecord
from src.competitive.database import ThreatScoreModel, VCAnnouncementModel
from src.relationships.database import Contact, Interaction

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def run_health_check():
    print("\nXXX RADAR SYSTEM HEALTH CHECK XXX\n")
    
    async with async_session_factory() as session:
        # --- 1. UNIVERSE SCANNER ---
        print("--- MODULE 1: UNIVERSE SCANNER ---")
        try:
            total_companies = await session.scalar(select(func.count(CompanyModel.id)))
            with_revenue = await session.scalar(select(func.count(CompanyModel.id)).where(CompanyModel.revenue_gbp.isnot(None)))
            with_moat = await session.scalar(select(func.count(CompanyModel.id)).where(CompanyModel.moat_score.isnot(None)))
            tiered = await session.scalar(select(func.count(CompanyModel.id)).where(CompanyModel.tier.isnot(None)))
            
            print(f"Total Companies: {total_companies}")
            print(f"  - With Revenue Data: {with_revenue} ({_pct(with_revenue, total_companies)})")
            print(f"  - With Moat Score:   {with_moat} ({_pct(with_moat, total_companies)})")
            print(f"  - Assigned Tier:     {tiered} ({_pct(tiered, total_companies)})")
            
            if total_companies > 0 and with_revenue == 0:
                 print("  [!] CRITICAL: No revenue data found. Prioritization will fail.")
        except Exception as e:
            print(f"  Error checking Universe: {e}")

        # --- 2. COMPETITIVE RADAR ---
        print("\n--- MODULE 2: COMPETITIVE RADAR ---")
        try:
            total_threats = await session.scalar(select(func.count(ThreatScoreModel.id)))
            total_announcements = await session.scalar(select(func.count(VCAnnouncementModel.id)))
            
            print(f"Total VC Announcements: {total_announcements}")
            print(f"Total Threat Scores:    {total_threats}")
        except Exception as e:
            print(f"  Error checking Competitive: {e}")

        # --- 4. DEAL INTELLIGENCE ---
        print("\n--- MODULE 4: DEAL INTELLIGENCE ---")
        try:
            total_deals = await session.scalar(select(func.count(DealRecord.id)))
            with_ev_ebitda = await session.scalar(select(func.count(DealRecord.id)).where(DealRecord.ev_ebitda_multiple.isnot(None)))
            with_ev_rev = await session.scalar(select(func.count(DealRecord.id)).where(DealRecord.ev_revenue_multiple.isnot(None)))
            
            print(f"Total Historical Deals: {total_deals}")
            print(f"  - With EV/EBITDA:    {with_ev_ebitda} ({_pct(with_ev_ebitda, total_deals)})")
            print(f"  - With EV/Revenue:   {with_ev_rev} ({_pct(with_ev_rev, total_deals)})")
            
            if total_deals > 0 and with_ev_ebitda == 0:
                 print("  [!] WARNING: No valuation multiples. Valuation engine will struggle.")
        except Exception as e:
            print(f"  Error checking Deal Intel: {e}")

        # --- 5. RELATIONSHIPS ---
        print("\n--- MODULE 5: RELATIONSHIP MANAGER ---")
        try:
            total_contacts = await session.scalar(select(func.count(Contact.id)))
            total_interactions = await session.scalar(select(func.count(Interaction.id)))
            
            print(f"Total Contacts:     {total_contacts}")
            print(f"Total Interactions: {total_interactions}")
        except Exception as e:
            print(f"  Error checking Relationships: {e}")

        # --- 10. CAPITAL FLOWS ---
        print("\n--- MODULE 10: CAPITAL FLOWS ---")
        try:
            total_firms = await session.scalar(select(func.count(PEFirmModel.id)))
            total_investments = await session.scalar(select(func.count(PEInvestmentModel.id)))
            inv_with_sector = await session.scalar(select(func.count(PEInvestmentModel.id)).where(PEInvestmentModel.sector.isnot(None)))
            
            print(f"Total PE Firms:      {total_firms}")
            print(f"Total Investments:   {total_investments}")
            print(f"  - With Sector:     {inv_with_sector} ({_pct(inv_with_sector, total_investments)})")
        except Exception as e:
            print(f"  Error checking Capital Flows: {e}")

def _pct(part, whole):
    if whole == 0:
        return "0%"
    return f"{int((part/whole)*100)}%"

if __name__ == "__main__":
    try:
        asyncio.run(run_health_check())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")

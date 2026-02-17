"""Public service interface for the Search module."""
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.universe.database import CompanyModel
from src.relationships.database import Contact
from src.capital.database import PEInvestmentModel

async def search_all(query: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Global search across companies, contacts, and deals.
    """
    results = {"companies": [], "contacts": [], "deals": []}
    
    async with get_async_db() as db:
        # Search Companies
        try:
            company_result = await db.execute(
                select(CompanyModel).where(CompanyModel.name.ilike(f"%{query}%")).limit(limit)
            )
            results["companies"] = [
                {"id": c.id, "name": c.name, "sector": c.sector or "Unknown"}
                for c in company_result.scalars()
            ]
        except Exception:
            pass

        # Search Contacts
        try:
            contact_result = await db.execute(
                select(Contact).where(Contact.full_name.ilike(f"%{query}%")).limit(limit)
            )
            results["contacts"] = [
                {"id": c.id, "name": c.full_name, "company": c.company_name or "", "role": c.job_title or ""}
                for c in contact_result.scalars()
            ]
        except Exception:
            pass

        # Search Deals
        try:
            deal_result = await db.execute(
                select(PEInvestmentModel)
                .where(PEInvestmentModel.company_name.ilike(f"%{query}%"))
                .limit(limit)
            )
            results["deals"] = [
                {"id": d.id, "name": d.company_name, "type": "PE Investment"}
                for d in deal_result.scalars()
            ]
        except Exception:
            pass

    return results

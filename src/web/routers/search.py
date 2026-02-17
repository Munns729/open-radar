"""Search router — global cross-domain search."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.universe.database import CompanyModel
from src.relationships.database import Contact
from src.capital.database import PEInvestmentModel
from src.core.database import get_db
from src.core.schemas import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("/", response_model=StandardResponse[dict], summary="Global Search")
async def global_search(
    q: str = Query(..., min_length=1),
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Search across companies, contacts, and deals."""
    results = {"companies": [], "contacts": [], "deals": []}

    company_result = await db.execute(
        select(CompanyModel).where(CompanyModel.name.ilike(f"%{q}%")).limit(limit)
    )
    results["companies"] = [
        {"id": c.id, "name": c.name, "sector": c.sector or "Unknown"}
        for c in company_result.scalars()
    ]

    try:
        contact_result = await db.execute(
            select(Contact).where(Contact.full_name.ilike(f"%{q}%")).limit(limit)
        )
        results["contacts"] = [
            {"id": c.id, "name": c.full_name, "company": c.company_name or "", "role": c.job_title or ""}
            for c in contact_result.scalars()
        ]
    except Exception:
        pass

    try:
        deal_result = await db.execute(
            select(PEInvestmentModel)
            .where(PEInvestmentModel.company_name.ilike(f"%{q}%"))
            .limit(limit)
        )
        results["deals"] = [
            {"id": d.id, "name": d.company_name, "type": "PE Investment"}
            for d in deal_result.scalars()
        ]
    except Exception:
        pass

    return StandardResponse(data=results)

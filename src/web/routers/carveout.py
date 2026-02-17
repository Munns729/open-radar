"""Carveout router — scan trigger and target listing."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.carveout.workflow import scan_carveouts
from src.carveout.database import Division, CorporateParent
from src.core.database import get_db
from src.web.responses import accepted
from src.core.schemas import StandardResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/carveout", tags=["Carveout"])


class CarveoutScanRequest(BaseModel):
    pass


@router.post("/scan", summary="Trigger Carveout Scan")
async def trigger_carveout_scan(background_tasks: BackgroundTasks):
    """Trigger the carveout identification scanner in the background."""

    async def run_scan():
        try:
            logger.info("Starting carveout scan")
            await scan_carveouts()
            logger.info("Carveout scan completed")
        except Exception:
            logger.exception("Carveout scan failed")

    background_tasks.add_task(run_scan)
    return accepted("Carveout scan started in background")


@router.get("/targets", response_model=StandardResponse[list], summary="Carveout Targets")
async def get_carveout_targets(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get potential corporate carveout targets."""
    stmt = (
        select(Division, CorporateParent)
        .join(CorporateParent, Division.parent_id == CorporateParent.id)
        .order_by(desc(Division.carveout_probability))
        .limit(limit)
    )
    result = await db.execute(stmt)

    data = [
        {
            "id": div.id,
            "division_name": div.division_name,
            "parent_name": parent.name,
            "probability": div.carveout_probability,
            "timeline": div.carveout_timeline,
            "revenue": div.revenue_eur,
            "attractiveness_score": div.attractiveness_score,
            "autonomy_level": div.autonomy_level,
            "strategic_autonomy": div.strategic_autonomy,
        }
        for div, parent in result.all()
    ]
    return StandardResponse(data=data)

"""Deals router — workflow triggers for enrichment, scoring, and full pipeline."""

import logging
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src.deal_intelligence.workflow import (
    enrich_deals,
    score_deal_probabilities,
    run_full_intelligence_workflow,
)

from src.core.schemas import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deals", tags=["Deal Intelligence"])


class EnrichRequest(BaseModel):
    batch_size: int = 20


class ScoreRequest(BaseModel):
    batch_size: int = 50
    tier_filter: Optional[List[str]] = ["1A", "1B"]


@router.post("/enrich", summary="Trigger Deal Enrichment")
async def trigger_enrichment(request: EnrichRequest, background_tasks: BackgroundTasks):
    """Trigger validation enrichment for deals lacking multiples."""

    async def run_enrichment():
        try:
            logger.info(f"Starting deal enrichment (batch={request.batch_size})")
            count = await enrich_deals(batch_size=request.batch_size)
            logger.info(f"Enrichment complete — processed {count} deals")
        except Exception:
            logger.exception("Deal enrichment failed")

    background_tasks.add_task(run_enrichment)

    return StandardResponse(status="accepted", message="Deal enrichment started in background")


@router.post("/score", summary="Trigger Probability Scoring")
async def trigger_scoring(request: ScoreRequest, background_tasks: BackgroundTasks):
    """Trigger deal probability scoring for companies."""

    async def run_scoring():
        try:
            logger.info(f"Starting scoring (tiers={request.tier_filter})")
            count = await score_deal_probabilities(
                tier_filter=request.tier_filter,
                batch_size=request.batch_size,
            )
            logger.info(f"Scoring complete — scored {count} companies")
        except Exception:
            logger.exception("Deal scoring failed")

    background_tasks.add_task(run_scoring)

    return StandardResponse(status="accepted", message="Deal scoring started in background")


@router.post("/workflow", summary="Run Full Intelligence Workflow")
async def trigger_full_workflow(background_tasks: BackgroundTasks):
    """Run the complete Deal Intelligence pipeline: enrich → metrics → score."""

    async def run_workflow():
        try:
            logger.info("Starting full deal intelligence workflow")
            results = await run_full_intelligence_workflow()
            logger.info(f"Full workflow complete: {results}")
        except Exception:
            logger.exception("Full intelligence workflow failed")

    background_tasks.add_task(run_workflow)

    return StandardResponse(status="accepted", message="Full intelligence workflow started")

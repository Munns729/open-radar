from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Optional, List
import logging
import ast
from pydantic import BaseModel
from sqlalchemy import select, desc, func

from src.capital.workflow import scan_capital_flows
from src.capital.database import PEInvestmentModel, PEFirmModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.schemas import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/capital",
    tags=["Capital Flows"]
)

class CapitalScanRequest(BaseModel):
    headless: bool = True
    terms: Optional[List[str]] = None
    sources: Optional[List[str]] = None  # SEC, FCA, IMERGEA - default all

@router.post("/scan", summary="Trigger Capital Flows Scan")
async def trigger_capital_scan(
    request: CapitalScanRequest, 
    background_tasks: BackgroundTasks
):
    """
    Trigger the Capital Flows scanning workflow in the background.
    Sources: SEC (US), FCA (UK), IMERGEA (Europe). Default: all.
    """
    sources = request.sources

    async def run_scan():
        try:
            logger.info("Starting background capital flows scan (sources=%s)...", sources)
            await scan_capital_flows(sources=sources)
            logger.info("Background capital flows scan completed.")
        except Exception as e:
            logger.error(f"Background capital flows scan failed: {e}", exc_info=True)

    background_tasks.add_task(run_scan)

    return {
        "status": "accepted",
        "message": "Capital flows scan started in background",
        "sources": sources,
        "details": "Check logs for progress. Sources: SEC (US), FCA (UK), IMERGEA (Europe).",
    }

@router.get("/status", summary="Check Scan Status")
async def get_scan_status():
    """
    Check the status of the capital flows scanner.
    (Placeholder implementation - real version would check a job queue or DB status flag)
    """
    # TODO: Implement real status tracking in database
    return {
        "status": "idle", 
        "last_run": "Unknown",
        "message": "Status tracking not yet implemented"
    }


@router.get("/investments", response_model=StandardResponse[List[dict]], summary="List PE Investments")
async def get_capital_investments(
    limit: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """Get recent PE investments and capital flows."""
    try:
        stmt = (
            select(PEInvestmentModel, PEFirmModel.name.label("firm_name"))
            .join(PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id)
            .order_by(desc(PEInvestmentModel.entry_date))
            .limit(limit)
        )
        result = await session.execute(stmt)
        investments = []
        for inv, firm_name in result:
            investments.append({
                "id": inv.id,
                "date": inv.entry_date.isoformat() if inv.entry_date else None,
                "target": inv.company_name,
                "investor": firm_name,
                "amount_usd": None,
                "sector": inv.sector,
                "thesis": (inv.investment_thesis[:100] + "...") if inv.investment_thesis else None,
            })
        return StandardResponse(data=investments)
    except Exception as e:
        logger.exception("Error fetching capital investments")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StandardResponse[List[dict]], summary="Capital Flow Statistics")
async def get_capital_stats(session: AsyncSession = Depends(get_db)):
    """Get statistics on tracked firms, enrichment progress, themes, and deal sizes."""
    try:
        stmt = (
            select(PEInvestmentModel, PEFirmModel.name.label("firm_name"))
            .join(PEFirmModel, PEInvestmentModel.pe_firm_id == PEFirmModel.id)
        )
        result = await session.execute(stmt)

        firm_data = {}
        for inv, firm_name in result:
            if firm_name not in firm_data:
                firm_data[firm_name] = {
                    "total": 0, "enriched": 0,
                    "valuations": [], "moat_counts": {}, "sectors": {},
                    "moat_returns": {},
                }
            stats = firm_data[firm_name]
            stats["total"] += 1
            if inv.investment_thesis:
                stats["enriched"] += 1
            if inv.entry_valuation_usd:
                stats["valuations"].append(inv.entry_valuation_usd)
            if inv.sector:
                stats["sectors"][inv.sector] = stats["sectors"].get(inv.sector, 0) + 1

            has_moats = False
            active_moats = []
            if inv.pe_identified_moats:
                try:
                    moats = (
                        inv.pe_identified_moats
                        if isinstance(inv.pe_identified_moats, dict)
                        else ast.literal_eval(str(inv.pe_identified_moats))
                    )
                    if isinstance(moats, dict):
                        for k, v in moats.items():
                            if v:
                                stats["moat_counts"][k] = stats["moat_counts"].get(k, 0) + 1
                                active_moats.append(k)
                                has_moats = True
                except Exception:
                    pass

            if inv.moic and has_moats:
                for m in active_moats:
                    if m not in stats["moat_returns"]:
                        stats["moat_returns"][m] = []
                    stats["moat_returns"][m].append(float(inv.moic))

        output_stats = []
        for firm, data in firm_data.items():
            sorted_sectors = sorted(data["sectors"].items(), key=lambda x: x[1], reverse=True)[:3]
            top_themes = [s[0] for s in sorted_sectors]
            sorted_moats = sorted(data["moat_counts"].items(), key=lambda x: x[1], reverse=True)[:3]
            top_moats = [m[0].replace("_", " ").title() for m in sorted_moats]

            returns_by_moat = []
            for moat, returns in data["moat_returns"].items():
                if returns:
                    avg_ret = sum(returns) / len(returns)
                    returns_by_moat.append({
                        "moat": moat.replace("_", " ").title(),
                        "avg_moic": round(avg_ret, 2),
                        "count": len(returns),
                    })
            returns_by_moat.sort(key=lambda x: x["avg_moic"], reverse=True)

            avg_deal = 0
            if data["valuations"]:
                avg_deal = sum(data["valuations"]) / len(data["valuations"])

            output_stats.append({
                "firm": firm,
                "total_companies": data["total"],
                "enriched_companies": data["enriched"],
                "coverage_pct": round((data["enriched"] / data["total"]) * 100, 1) if data["total"] > 0 else 0,
                "top_themes": top_themes,
                "top_moats": top_moats,
                "avg_deal_size_usd": avg_deal,
                "returns_by_moat": returns_by_moat,
            })

        return StandardResponse(data=output_stats)
    except Exception as e:
        logger.exception("Error fetching capital stats")
        raise HTTPException(status_code=500, detail=str(e))

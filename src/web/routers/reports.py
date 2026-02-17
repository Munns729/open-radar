"""Reports router — generation, preview, download, history, and CSV export."""

import csv
import io
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select

from src.core.database import get_db
from src.core.schemas import StandardResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.universe.database import CompanyModel
from src.carveout.database import Division, CorporateParent
from src.reporting.workflow import generate_report
from src.reporting.filters import ReportFilters

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/reports",
    tags=["Reporting"]
)


@router.get("/history", summary="Report History")
async def get_report_history():
    """Get list of generated reports."""
    output_dir = Path("outputs")
    if not output_dir.exists():
        return []

    files = []
    for ext in ["*.html", "*.xlsx", "*.txt"]:
        for f in output_dir.glob(ext):
            files.append({
                "filename": f.name,
                "type": f.suffix[1:].upper(),
                "date": f.stat().st_mtime,
                "size": f.stat().st_size,
            })

    return sorted(files, key=lambda x: x["date"], reverse=True)


@router.get("/preview", response_model=StandardResponse[list], summary="Preview Report")
async def preview_report(
    tier: Optional[str] = "all",
    sector: Optional[str] = None,
    min_moat: int = 50,
    max_moat: int = 100,
    hot_only: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """Get live preview of report data based on filters."""
    try:
        filters = ReportFilters(
            tier=tier if tier != "all" else None,
            sector=[sector] if sector else None,
            min_moat=min_moat,
            max_moat=max_moat,
            priority="hot" if hot_only else None,
        )

        from src.reporting.filters import apply_filters as fetch_filtered_companies

        companies = await fetch_filtered_companies(session, filters)
        data = []
        for c in companies:
            data.append({
                "id": c.id,
                "name": c.name,
                "sector": c.sector,
                "tier": c.tier,
                "revenue_gbp": c.revenue_gbp,
                "moat_score": c.moat_score,
                "moat_analysis": c.moat_analysis,
                "growth_score": getattr(c, "growth_score", None),
                "employees": c.employees,
                "hq_country": c.hq_country,
            })
        return StandardResponse(data=data)
    except Exception as e:
        logger.exception("Report preview error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=StandardResponse[dict], summary="Generate Report")
async def generate_new_report(
    format: str = Query(..., regex="^(html|excel|table)$"),
    tier: Optional[str] = "all",
    sector: Optional[str] = None,
    min_moat: int = 50,
    max_moat: int = 100,
    hot_only: bool = False,
):
    """Trigger report generation."""
    try:
        filters = ReportFilters(
            tier=tier if tier != "all" else None,
            sector=[sector] if sector else None,
            min_moat=min_moat,
            max_moat=max_moat,
            priority="hot" if hot_only else None,
        )

        output_files = await generate_report(
            report_type="targets",
            output_format=format,
            filters=filters,
        )

        if not output_files:
            raise HTTPException(status_code=500, detail="Report generation failed to produce output files")

        output_file = output_files[0]
        return StandardResponse(data={
            "message": "Report generated successfully",
            "filename": Path(output_file).name,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}", summary="Download Report")
async def download_report(filename: str):
    """Download a report file."""
    file_path = Path("outputs") / filename

    if not file_path.resolve().is_relative_to(Path("outputs").resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "application/octet-stream"
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(file_path, media_type=media_type, filename=filename)


@router.get("/export/{module}", summary="Export Data")
async def export_data(module: str, session: AsyncSession = Depends(get_db)):
    """Export module data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    if module == "universe":
        stmt = select(CompanyModel)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        writer.writerow(["Name", "Sector", "Tier", "Revenue GBP", "Moat Score"])
        for r in rows:
            writer.writerow([r.name, r.sector, r.tier, r.revenue_gbp, r.moat_score])

    elif module == "carveout":
        stmt = select(Division, CorporateParent).join(CorporateParent)
        result = await session.execute(stmt)
        rows = result.all()
        writer.writerow(["Division", "Parent", "Probability", "Revenue EUR", "Timeline"])
        for div, parent in rows:
            writer.writerow([div.division_name, parent.name, div.carveout_probability, div.revenue_eur, div.carveout_timeline])

    else:
        raise HTTPException(status_code=400, detail="Unknown module")

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={module}_export.csv"},
    )

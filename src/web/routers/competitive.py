"""Competitive router — VC threat feed, firm tracking, and VC portfolio sourcing intelligence."""

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitive.database import VCAnnouncementModel, ThreatScoreModel, VCFirmModel
from src.competitive.vc_portfolio_models import CompanyVCHoldingModel, VCExitSignalModel
from src.core.database import get_db
from src.core.utils import normalize_name, fuzzy_match_company
from src.universe.database import CompanyModel
from src.core.schemas import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/competitive", tags=["Competitive"])


# ── Existing endpoints (unchanged) ────────────────────────────────────────────

@router.get("/feed", response_model=StandardResponse[list], summary="Competitive Feed")
async def get_competitive_feed(
    limit: int = 50,
    firm_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get feed of competitive threats and announcements."""
    try:
        stmt = (
            select(ThreatScoreModel, VCAnnouncementModel, VCFirmModel)
            .join(VCAnnouncementModel, ThreatScoreModel.announcement_id == VCAnnouncementModel.id)
            .join(VCFirmModel, VCAnnouncementModel.vc_firm_id == VCFirmModel.id)
        )
        if firm_id:
            stmt = stmt.where(VCFirmModel.id == firm_id)
        stmt = stmt.order_by(desc(ThreatScoreModel.created_at)).limit(limit)

        result = await db.execute(stmt)

        data = [
            {
                "id": threat.id,
                "type": "threat",
                "company": announcement.company_name,
                "competitor": firm.name,
                "competitor_id": firm.id,
                "threat_level": threat.threat_level,
                "score": threat.threat_score,
                "description": threat.reasoning,
                "date": threat.created_at,
            }
            for threat, announcement, firm in result.all()
        ]
        return StandardResponse(data=data)
    except Exception:
        logger.exception("Competitive feed error")
        raise HTTPException(status_code=500, detail="Failed to load competitive feed")


@router.get("/firms", response_model=StandardResponse[list], summary="Competitive Firms")
async def get_competitive_firms(db: AsyncSession = Depends(get_db)):
    """Get list of VC firms with their threat stats."""
    try:
        stmt = (
            select(
                VCFirmModel,
                func.count(ThreatScoreModel.id).label("threat_count"),
                func.max(ThreatScoreModel.created_at).label("last_threat"),
            )
            .outerjoin(VCAnnouncementModel, VCFirmModel.id == VCAnnouncementModel.vc_firm_id)
            .outerjoin(ThreatScoreModel, VCAnnouncementModel.id == ThreatScoreModel.announcement_id)
            .group_by(VCFirmModel.id)
            .order_by(desc("last_threat"), VCFirmModel.name)
        )
        result = await db.execute(stmt)

        data = [
            {
                "id": firm.id,
                "name": firm.name,
                "tier": firm.tier,
                "focus_sectors": firm.focus_sectors,
                "threat_count": count,
                "last_activity": last_date,
            }
            for firm, count, last_date in result.all()
        ]
        return StandardResponse(data=data)
    except Exception:
        logger.exception("Error fetching competitive firms")
        raise HTTPException(status_code=500, detail="Failed to load firms")


# ── NEW: VC Portfolio Sourcing Intelligence ────────────────────────────────────

@router.get("/vc-portfolio/targets", response_model=StandardResponse[list], summary="VC Portfolio Targets")
async def get_vc_portfolio_targets(
    priority_tier: Optional[str] = Query(None, description="Filter by tier: A, B, C"),
    dual_use_only: bool = Query(False, description="Show only dual-use companies"),
    exit_pressure_only: bool = Query(False, description="Show only funds under LP exit pressure"),
    holding_status: Optional[str] = Query(None, description="Filter by holding status: current, exited, or omit for all"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Get ranked list of VC portfolio companies (holdings) as PE acquisition targets.
    Companies come from universe; joined with holdings and signals. Sorted by deal_quality_score.
    """
    try:
        stmt = (
            select(
                CompanyVCHoldingModel,
                CompanyModel,
                VCExitSignalModel,
                VCFirmModel.name.label("vc_fund_name"),
                VCFirmModel.tier.label("vc_fund_tier"),
            )
            .join(CompanyModel, CompanyVCHoldingModel.company_id == CompanyModel.id)
            .join(VCFirmModel, CompanyVCHoldingModel.vc_firm_id == VCFirmModel.id)
            .outerjoin(VCExitSignalModel, VCExitSignalModel.holding_id == CompanyVCHoldingModel.id)
        )

        if priority_tier:
            stmt = stmt.where(VCExitSignalModel.priority_tier == priority_tier.upper())
        if dual_use_only:
            stmt = stmt.where(CompanyModel.is_dual_use == True)
        if exit_pressure_only:
            stmt = stmt.where(VCExitSignalModel.fund_exit_pressure == True)
        if holding_status and holding_status.lower() in ("current", "exited"):
            stmt = stmt.where(CompanyVCHoldingModel.holding_status == holding_status.lower())

        stmt = stmt.order_by(desc(VCExitSignalModel.deal_quality_score)).limit(limit)

        result = await db.execute(stmt)

        data = []
        for holding, company, signal, fund_name, fund_tier in result.all():
            data.append({
                "id": holding.id,
                "company_id": company.id,
                "name": company.name,
                "website": company.website,
                "description": (company.description or "")[:200],
                "vc_fund": fund_name,
                "vc_fund_tier": fund_tier,
                "first_funding_date": company.first_funding_date.isoformat() if company.first_funding_date else None,
                "sector_tags": [company.sector] if company.sector else [],
                "is_dual_use": company.is_dual_use or False,
                "dual_use_confidence": float(company.dual_use_confidence or 0),
                "has_gov_contract": company.has_gov_contract or False,
                "has_export_cert": company.has_export_cert or False,
                "deal_quality_score": signal.deal_quality_score if signal else 0,
                "priority_tier": signal.priority_tier if signal else "C",
                "exit_readiness_score": signal.exit_readiness_score if signal else 0,
                "fund_exit_pressure": signal.fund_exit_pressure if signal else False,
                "nato_lp_backed": signal.nato_lp_backed if signal else False,
                "eif_lp_backed": signal.eif_lp_backed if signal else False,
                "years_held": signal.years_held if signal else None,
                "notes": signal.notes if signal else None,
                "in_radar_universe": company.extraction_complete_at is not None,
                "universe_company_id": company.id,
                "holding_status": holding.holding_status or "current",
                "exited_at": holding.exited_at.isoformat() if holding.exited_at else None,
            })

        return StandardResponse(data=data)

    except Exception:
        logger.exception("Error fetching VC portfolio targets")
        raise HTTPException(status_code=500, detail="Failed to load VC portfolio targets")


@router.get("/vc-portfolio/stats", response_model=StandardResponse[dict], summary="VC Portfolio Stats")
async def get_vc_portfolio_stats(db: AsyncSession = Depends(get_db)):
    """Summary stats for the VC sourcing funnel (holdings = company + fund pairs)."""
    try:
        total = await db.execute(func.count(CompanyVCHoldingModel.id))
        total_count = total.scalar() or 0

        tier_a = await db.execute(
            select(func.count()).where(VCExitSignalModel.priority_tier == "A")
        )
        tier_b = await db.execute(
            select(func.count()).where(VCExitSignalModel.priority_tier == "B")
        )
        dual_use = await db.execute(
            select(func.count()).select_from(CompanyVCHoldingModel).join(CompanyModel).where(CompanyModel.is_dual_use == True)
        )
        exit_pressure = await db.execute(
            select(func.count()).where(VCExitSignalModel.fund_exit_pressure == True)
        )
        in_universe = await db.execute(
            select(func.count()).select_from(CompanyVCHoldingModel).join(CompanyModel).where(CompanyModel.extraction_complete_at.isnot(None))
        )
        current_holdings = await db.execute(
            select(func.count()).select_from(CompanyVCHoldingModel).where(CompanyVCHoldingModel.holding_status == "current")
        )
        exited_holdings = await db.execute(
            select(func.count()).select_from(CompanyVCHoldingModel).where(CompanyVCHoldingModel.holding_status == "exited")
        )

        return StandardResponse(data={
            "total_portfolio_companies": total_count,
            "current_holdings": current_holdings.scalar() or 0,
            "exited_holdings": exited_holdings.scalar() or 0,
            "priority_a": tier_a.scalar() or 0,
            "priority_b": tier_b.scalar() or 0,
            "dual_use_flagged": dual_use.scalar() or 0,
            "exit_pressure": exit_pressure.scalar() or 0,
            "already_in_universe": in_universe.scalar() or 0,
        })

    except Exception:
        logger.exception("Error fetching VC portfolio stats")
        raise HTTPException(status_code=500, detail="Failed to load stats")


@router.post("/vc-portfolio/scrape", summary="Trigger VC Portfolio Scrape")
async def trigger_vc_portfolio_scrape(background_tasks: BackgroundTasks):
    """Trigger background scrape of all configured VC portfolio pages."""
    async def run():
        from src.competitive.vc_portfolio_scraper import scrape_all_funds
        results = await scrape_all_funds()
        logger.info("VC portfolio scrape complete: %s", results)

    background_tasks.add_task(run)
    return {"status": "accepted", "message": "VC portfolio scrape started in background"}


@router.post("/vc-portfolio/score", summary="Re-score VC Portfolio Signals")
async def trigger_vc_scoring(background_tasks: BackgroundTasks):
    """Re-compute exit-readiness and deal quality scores for all portfolio companies."""
    async def run():
        from src.competitive.vc_signal_scorer import score_all_portfolio_companies
        count = await score_all_portfolio_companies()
        logger.info("VC scoring complete: %d companies scored", count)

    background_tasks.add_task(run)
    return {"status": "accepted", "message": "VC signal scoring started in background"}


@router.post("/vc-portfolio/run-moat-pipeline", summary="Run Moat Pipeline for VC Portfolio")
async def trigger_vc_moat_pipeline(background_tasks: BackgroundTasks, limit: int | None = None):
    """
    Sync VC portfolio companies to universe (create or link), then run extraction + moat scoring.
    Use limit to cap how many portfolio companies to process (default: all without a universe link).
    """
    async def run():
        from src.competitive.vc_portfolio_to_universe import run_moat_pipeline_for_vc_portfolio
        result = await run_moat_pipeline_for_vc_portfolio(limit=limit)
        logger.info("VC moat pipeline complete: %s", result)

    background_tasks.add_task(run)
    return {
        "status": "accepted",
        "message": "VC portfolio → universe sync + extraction + moat scoring started in background",
        "limit": limit,
    }


@router.post("/vc-portfolio/enrich-existing", summary="Enrich Existing Linked Companies")
async def trigger_vc_enrich_existing(background_tasks: BackgroundTasks, limit: int | None = None):
    """
    Run extraction + moat scoring on universe companies that are already linked from VC portfolio.
    No new companies created or linked. Use to refresh moat or run extraction for the first time on linked companies.
    """
    async def run():
        from src.competitive.vc_portfolio_to_universe import run_enrich_existing_vc_linked
        result = await run_enrich_existing_vc_linked(limit=limit)
        logger.info("VC enrich existing complete: %s", result)

    background_tasks.add_task(run)
    return {
        "status": "accepted",
        "message": "Extraction + moat scoring started for already-linked VC portfolio companies",
        "limit": limit,
    }


@router.post("/vc-portfolio/crosscheck-contracts", summary="Cross-check Contracts Finder")
async def trigger_contracts_finder_crosscheck(
    background_tasks: BackgroundTasks,
    published_from_days: int = 730,
    max_suppliers: int = 5000,
):
    """
    Cross-check VC portfolio companies against UK Contracts Finder award notices.
    Sets has_gov_contract=True and gov_contract_notes on companies that appear as contract winners.
    Runs in background; indexes up to max_suppliers from the last published_from_days.
    """
    async def run():
        from src.core.database import get_async_db
        from src.competitive.vc_contracts_crosscheck import run_contracts_finder_crosscheck
        async with get_async_db() as db:
            result = await run_contracts_finder_crosscheck(
                db,
                published_from_days=published_from_days,
                max_suppliers=max_suppliers,
            )
        logger.info("VC contracts cross-check complete: %s", result)

    background_tasks.add_task(run)
    return {
        "status": "accepted",
        "message": "Contracts Finder cross-check started (VC portfolio companies vs UK award notices)",
        "published_from_days": published_from_days,
        "max_suppliers": max_suppliers,
    }


@router.patch("/vc-portfolio/holdings/{holding_id}", summary="Update Holding (status / exited)")
async def update_vc_holding(
    holding_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a VC holding: holding_status ('current' | 'exited') and optionally exited_at (YYYY-MM-DD).
    """
    result = await db.execute(select(CompanyVCHoldingModel).where(CompanyVCHoldingModel.id == holding_id))
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    if "holding_status" in updates:
        v = (updates.get("holding_status") or "").strip().lower()
        if v in ("current", "exited"):
            holding.holding_status = v
    if "exited_at" in updates:
        raw = updates.get("exited_at")
        if raw is None or raw == "":
            holding.exited_at = None
        else:
            try:
                holding.exited_at = datetime.strptime(str(raw).strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="exited_at must be YYYY-MM-DD")
    await db.commit()
    return {"status": "updated", "holding_id": holding_id}


@router.patch("/vc-portfolio/companies/{company_id}", summary="Update Company (VC fields)")
async def update_portfolio_company(
    company_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Update VC-related fields on a company (has_gov_contract, has_export_cert, gov_contract_notes, etc).
    company_id is the universe company id. Re-score via /vc-portfolio/score after updating.
    """
    result = await db.execute(
        select(CompanyModel).where(CompanyModel.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    allowed_fields = {
        "has_gov_contract", "gov_contract_notes", "has_export_cert",
        "regulatory_notes", "sector", "is_dual_use", "dual_use_confidence", "first_funding_date",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(company, field, value)

    await db.commit()
    return {"status": "updated", "company_id": company_id}


def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url or not url.strip():
        return None
    from urllib.parse import urlparse
    u = url.strip().lower()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
        host = (parsed.netloc or "").strip()
        if host and "." in host:
            return host
    except Exception:
        pass
    return None


@router.post("/vc-portfolio/import-csv", summary="Bulk import VC portfolio from CSV")
async def import_vc_portfolio_csv(
    file: UploadFile = File(..., description="CSV with columns: name, vc_fund, website (optional), first_funding_date (optional), sector (optional)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import portfolio companies from CSV. Resolves vc_fund by name (must match vc_firms.name).
    For each row: find or create company (by normalized name or website domain), upsert holding.
    Returns counts of companies created, holdings added, and any row errors.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload must be a CSV file")

    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames or "vc_fund" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV must have headers including 'name' and 'vc_fund'"
        )

    # Load all VC firms by name
    firms_result = await db.execute(select(VCFirmModel.id, VCFirmModel.name))
    firms_by_name = {row[1]: row[0] for row in firms_result.all()}

    # Load existing companies for matching (exact + fuzzy)
    companies_result = await db.execute(select(CompanyModel.id, CompanyModel.name, CompanyModel.website))
    company_rows = companies_result.all()
    by_name_norm = {}
    by_domain = {}
    for row in company_rows:
        cid, name, website = row[0], row[1], row[2]
        if name:
            key = normalize_name(name)
            if key and key not in by_name_norm:
                by_name_norm[key] = cid
        if website:
            d = _extract_domain(website)
            if d and d not in by_domain:
                by_domain[d] = cid

    created_companies = 0
    new_holdings = 0
    errors = []
    total_rows = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for i, row in enumerate(reader):
        total_rows += 1
        name = (row.get("name") or "").strip()
        vc_fund = (row.get("vc_fund") or "").strip()
        website = (row.get("website") or "").strip() or None
        first_funding_date = None
        if row.get("first_funding_date"):
            try:
                first_funding_date = datetime.strptime(row["first_funding_date"].strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                errors.append({"row": i + 2, "error": "Invalid first_funding_date (use YYYY-MM-DD)"})
                continue
        sector = (row.get("sector") or "").strip() or None

        if not name:
            errors.append({"row": i + 2, "error": "Missing name"})
            continue
        vc_firm_id = firms_by_name.get(vc_fund)
        if not vc_firm_id:
            errors.append({"row": i + 2, "error": f"Unknown vc_fund: {vc_fund}"})
            continue

        name_norm = normalize_name(name)
        domain = _extract_domain(website) if website else None

        company_id = None
        if name_norm and name_norm in by_name_norm:
            company_id = by_name_norm[name_norm]
        elif domain and domain in by_domain:
            company_id = by_domain[domain]

        if company_id is None:
            match = fuzzy_match_company(name, [(r[0], r[1]) for r in company_rows], threshold=80)
            if match:
                company_id, _score = match
                if name_norm:
                    by_name_norm[name_norm] = company_id
                if domain:
                    by_domain[domain] = company_id
        if company_id is None:
            company = CompanyModel(
                name=name,
                website=website,
                sector=sector,
                first_funding_date=first_funding_date,
                discovered_via="vc_portfolio_csv",
            )
            db.add(company)
            await db.flush()
            company_id = company.id
            by_name_norm[name_norm] = company_id
            if domain:
                by_domain[domain] = company_id
            created_companies += 1
        else:
            comp = (await db.execute(select(CompanyModel).where(CompanyModel.id == company_id))).scalar_one()
            if first_funding_date and not comp.first_funding_date:
                comp.first_funding_date = first_funding_date
            if sector and not comp.sector:
                comp.sector = sector
            if website and not comp.website:
                comp.website = website

        existing = await db.execute(
            select(CompanyVCHoldingModel).where(
                CompanyVCHoldingModel.company_id == company_id,
                CompanyVCHoldingModel.vc_firm_id == vc_firm_id,
            )
        )
        hold = existing.scalar_one_or_none()
        if not hold:
            hold = CompanyVCHoldingModel(
                company_id=company_id,
                vc_firm_id=vc_firm_id,
                source="csv_import",
                first_seen_at=now,
                last_scraped_at=now,
            )
            db.add(hold)
            new_holdings += 1

    await db.commit()
    return {
        "created_companies": created_companies,
        "new_holdings": new_holdings,
        "errors": errors[:50],
        "total_rows": total_rows,
    }

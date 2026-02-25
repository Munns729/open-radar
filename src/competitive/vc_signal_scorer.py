"""
VC Exit Signal Scorer

Runs nightly (or on-demand) to compute exit-readiness and quality scores
for all VC portfolio companies and upsert into vc_exit_signals.

Algorithm:
  exit_readiness (0-100):  40 pts max for years held, 30 pts for fund vintage pressure, 30 pts for fund AUM (LP pressure)
  vc_quality (0-100):      50 pts for NATO/EIF LP, 30 pts for tier, 20 pts for co-investor count
  dual_use_validation (0-100): 40 pts for regulatory cert, 30 pts for gov contract, 30 pts for DIANA/EDF

  deal_quality_score = exit_readiness * 0.40 + vc_quality * 0.30 + dual_use_validation * 0.30

  priority_tier:
    A = deal_quality_score >= 70
    B = deal_quality_score >= 45
    C = below 45
"""
import asyncio
import logging
from datetime import date
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.competitive.database import VCFirmModel
from src.competitive.vc_portfolio_models import CompanyVCHoldingModel, VCExitSignalModel
from src.universe.database import CompanyModel

logger = logging.getLogger(__name__)


def _years_since_first_funding(company) -> float | None:
    """Company may be CompanyModel with first_funding_date."""
    if not getattr(company, "first_funding_date", None):
        return None
    return (date.today() - company.first_funding_date).days / 365.25

# Fund-level metadata not in the DB schema (stored here for scoring)
# Keyed by vc_firms.name
FUND_METADATA = {
    "Expeditions":            {"nato_lp": True,  "eif_lp": False, "tier": 1, "aum_eur": 150_000_000,  "vintage": 2021},
    "NATO Innovation Fund":   {"nato_lp": False, "eif_lp": False, "tier": 1, "aum_eur": 1_000_000_000,"vintage": 2022},
    "Vsquared Ventures":      {"nato_lp": True,  "eif_lp": True,  "tier": 1, "aum_eur": 450_000_000,  "vintage": 2020},
    "Alpine Space Ventures":  {"nato_lp": True,  "eif_lp": False, "tier": 1, "aum_eur": 60_000_000,   "vintage": 2020},
    "OTB Ventures":           {"nato_lp": True,  "eif_lp": False, "tier": 1, "aum_eur": 100_000_000,  "vintage": 2019},
    "Join Capital":           {"nato_lp": True,  "eif_lp": False, "tier": 1, "aum_eur": 120_000_000,  "vintage": 2019},
    "Paladin Capital Group":  {"nato_lp": False, "eif_lp": False, "tier": 1, "aum_eur": 1_000_000_000,"vintage": 2018},
    "IQ Capital":             {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 400_000_000,  "vintage": 2018},
    "Frst":                   {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 200_000_000,  "vintage": 2018},
    "Kompas VC":              {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": None,          "vintage": 2023},
    "Cavalry Ventures":       {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 60_000_000,   "vintage": 2021},
    "Air Street Capital":     {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 50_000_000,   "vintage": 2019},
    "Lakestar":               {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 1_000_000_000,"vintage": 2022},
    "Molten Ventures":        {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": 1_000_000_000,"vintage": 2016},
    "Presto Tech Horizons":   {"nato_lp": False, "eif_lp": False, "tier": 2, "aum_eur": None,          "vintage": 2024},
    "Lunar Ventures":         {"nato_lp": False, "eif_lp": False, "tier": 3, "aum_eur": 70_000_000,   "vintage": 2021},
}

CURRENT_YEAR = date.today().year


def _score_exit_readiness(company, fund_meta: dict) -> tuple[float, str, float | None]:
    """
    Returns (score 0-100, rationale string, years_held used for scoring).
    Company is CompanyModel (universe). When first_funding_date is missing, uses fund vintage as proxy.
    """
    score = 0.0
    notes = []
    vintage = fund_meta.get("vintage", CURRENT_YEAR)
    fund_age = CURRENT_YEAR - vintage

    # 1. Years held (40 pts): sweet spot is 4-7 years
    years_held = _years_since_first_funding(company)
    if years_held is None and vintage is not None:
        years_held = (CURRENT_YEAR - vintage) + 0.5
        notes.append(f"~{years_held:.1f}y held (est. from fund vintage {vintage})")
    elif years_held is not None:
        notes.append(f"{years_held:.1f}y held (from funding data)")

    if years_held is not None:
        if years_held >= 5:
            score += 40
            notes[-1] += " (exit sweet spot)"
        elif years_held >= 4:
            score += 28
            notes[-1] += " (approaching window)"
        elif years_held >= 3:
            score += 15
            notes[-1] += " (building)"
        else:
            notes[-1] += " (too early)"

    # 2. Fund vintage pressure (30 pts): fund age 4+ = LP pressure
    if fund_age >= 7:
        score += 30
        notes.append(f"Fund vintage {vintage} ({fund_age}y old — high LP pressure)")
    elif fund_age >= 5:
        score += 22
        notes.append(f"Fund vintage {vintage} ({fund_age}y old — moderate LP pressure)")
    elif fund_age >= 4:
        score += 12
        notes.append(f"Fund vintage {vintage} ({fund_age}y old — early pressure)")
    else:
        notes.append(f"Fund vintage {vintage} ({fund_age}y — no LP pressure yet)")

    # 3. Fund AUM (30 pts): larger AUM = more pressure to return capital at scale
    aum = fund_meta.get("aum_eur") or 0
    if aum >= 500_000_000:
        score += 30
        notes.append("Large fund (€500M+) — needs PE-scale exits")
    elif aum >= 100_000_000:
        score += 20
        notes.append("Mid-size fund (€100-500M)")
    elif aum > 0:
        score += 10
        notes.append(f"Smaller fund (€{aum/1e6:.0f}M)")

    return min(score, 100.0), " | ".join(notes), years_held


def _score_vc_quality(fund_meta: dict) -> tuple[float, str]:
    """
    Returns (score 0-100, rationale string)
    """
    score = 0.0
    notes = []

    # 1. NATO / EIF LP (50 pts)
    if fund_meta.get("nato_lp"):
        score += 35
        notes.append("NATO Innovation Fund LP (gov-validated)")
    if fund_meta.get("eif_lp"):
        score += 15
        notes.append("EIF LP (EU-validated)")

    # 2. Fund tier (30 pts)
    tier = fund_meta.get("tier", 3)
    if tier == 1:
        score += 30
        notes.append("Tier 1 specialist fund")
    elif tier == 2:
        score += 18
        notes.append("Tier 2 quality generalist")
    else:
        score += 6
        notes.append("Tier 3 generalist")

    # 3. AUM as proxy for brand/validation (20 pts)
    aum = fund_meta.get("aum_eur") or 0
    if aum >= 500_000_000:
        score += 20
        notes.append("Marquee fund (€500M+ AUM)")
    elif aum >= 100_000_000:
        score += 12
        notes.append("Established fund (€100M+ AUM)")
    elif aum > 0:
        score += 5

    return min(score, 100.0), " | ".join(notes)


def _score_dual_use_validation(company) -> tuple[float, str]:
    """
    Returns (score 0-100, rationale string). Company is CompanyModel (universe).
    """
    score = 0.0
    notes = []

    if getattr(company, "has_export_cert", False):
        score += 40
        notes.append("Export cert confirmed (regulatory moat)")

    if getattr(company, "has_gov_contract", False):
        score += 30
        notes.append("Government contract confirmed")

    du = getattr(company, "is_dual_use", False)
    conf = getattr(company, "dual_use_confidence", 0) or 0
    if du and conf >= 0.8:
        score += 20
        notes.append(f"High dual-use confidence ({company.dual_use_confidence:.0%})")
    elif du:
        score += 10
        notes.append(f"Dual-use flagged ({conf:.0%} confidence)")

    if score == 0:
        notes.append("No dual-use validation yet — needs manual review")

    return min(score, 100.0), " | ".join(notes)


def _compute_composite(exit_r: float, vc_q: float, dv: float) -> float:
    return round(exit_r * 0.40 + vc_q * 0.30 + dv * 0.30, 1)


def _priority_tier(score: float) -> str:
    if score >= 70:
        return "A"
    if score >= 45:
        return "B"
    return "C"


async def score_all_portfolio_companies() -> int:
    """
    Re-score all VC holdings (company + fund) and upsert into vc_exit_signals.
    Returns number of records processed.
    """
    async with get_async_db() as session:
        stmt = (
            select(CompanyVCHoldingModel, VCFirmModel.name.label("firm_name"))
            .join(VCFirmModel, CompanyVCHoldingModel.vc_firm_id == VCFirmModel.id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        processed = 0
        for holding, firm_name in rows:
            # Load company for dual-use and years_held
            company_result = await session.execute(
                select(CompanyModel).where(CompanyModel.id == holding.company_id)
            )
            company = company_result.scalar_one_or_none()
            if not company:
                continue

            fund_meta = FUND_METADATA.get(firm_name, {"nato_lp": False, "eif_lp": False, "tier": 3, "aum_eur": None, "vintage": CURRENT_YEAR})

            exit_r, exit_notes, years_held_used = _score_exit_readiness(company, fund_meta)
            vc_q, vc_notes = _score_vc_quality(fund_meta)
            dv, dv_notes = _score_dual_use_validation(company)
            composite = _compute_composite(exit_r, vc_q, dv)
            tier = _priority_tier(composite)

            rationale = (
                f"EXIT READINESS ({exit_r:.0f}/100): {exit_notes} | "
                f"VC QUALITY ({vc_q:.0f}/100): {vc_notes} | "
                f"DUAL-USE ({dv:.0f}/100): {dv_notes}"
            )

            existing = await session.execute(
                select(VCExitSignalModel).where(VCExitSignalModel.holding_id == holding.id)
            )
            signal = existing.scalar_one_or_none()

            if signal:
                signal.exit_readiness_score = exit_r
                signal.deal_quality_score = composite
                signal.priority_tier = tier
                signal.vc_quality_tier = fund_meta.get("tier", 3)
                signal.nato_lp_backed = fund_meta.get("nato_lp", False)
                signal.eif_lp_backed = fund_meta.get("eif_lp", False)
                signal.fund_vintage_year = fund_meta.get("vintage")
                signal.years_held = years_held_used
                signal.fund_exit_pressure = (CURRENT_YEAR - (fund_meta.get("vintage") or CURRENT_YEAR)) >= 4
                signal.regulatory_moat_confirmed = getattr(company, "has_export_cert", False)
                signal.notes = rationale
                signal.scored_at = date.today()
            else:
                signal = VCExitSignalModel(
                    holding_id=holding.id,
                    exit_readiness_score=exit_r,
                    deal_quality_score=composite,
                    priority_tier=tier,
                    vc_quality_tier=fund_meta.get("tier", 3),
                    nato_lp_backed=fund_meta.get("nato_lp", False),
                    eif_lp_backed=fund_meta.get("eif_lp", False),
                    fund_vintage_year=fund_meta.get("vintage"),
                    years_held=years_held_used,
                    fund_exit_pressure=(CURRENT_YEAR - (fund_meta.get("vintage") or CURRENT_YEAR)) >= 4,
                    regulatory_moat_confirmed=getattr(company, "has_export_cert", False),
                    notes=rationale,
                )
                session.add(signal)

            processed += 1

        await session.commit()
        logger.info("VC signal scoring complete: %d holdings processed", processed)
        return processed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(score_all_portfolio_companies())
    print(f"Scored {count} portfolio companies.")

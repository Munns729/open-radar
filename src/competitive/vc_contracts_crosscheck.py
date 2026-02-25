"""
Cross-check VC portfolio companies against UK Contracts Finder (award notices).
Sets has_gov_contract and gov_contract_notes on companies that appear as contract winners.
"""
import logging
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitive.vc_portfolio_models import CompanyVCHoldingModel
from src.core.utils import normalize_name
from src.universe.database import CompanyModel
from src.universe.scrapers.api.contracts_finder_scraper import ContractsFinderScraper

logger = logging.getLogger(__name__)

# Max notice URLs to store in gov_contract_notes (first N)
MAX_NOTES_URLS = 3
NOTES_PREFIX = "UK Contracts Finder (award notices): "


async def run_contracts_finder_crosscheck(
    db: AsyncSession,
    published_from_days: int = 730,
    max_suppliers: int = 5000,
) -> Dict[str, int]:
    """
    Load companies that have VC holdings; fetch award supplier names from Contracts Finder;
    set has_gov_contract=True and gov_contract_notes for matches.
    Returns dict: companies_checked, suppliers_indexed, companies_matched, companies_updated.
    """
    # Distinct company IDs that have at least one VC holding
    stmt = select(CompanyVCHoldingModel.company_id).distinct()
    result = await db.execute(stmt)
    company_ids = [r[0] for r in result.all()]
    if not company_ids:
        return {"companies_checked": 0, "suppliers_indexed": 0, "companies_matched": 0, "companies_updated": 0}

    # Load company id -> name
    stmt = select(CompanyModel.id, CompanyModel.name).where(CompanyModel.id.in_(company_ids))
    rows = (await db.execute(stmt)).all()
    companies_by_id = {r[0]: r[1] for r in rows if r[1]}

    # Build supplier name -> URLs from Contracts Finder
    async with ContractsFinderScraper() as scraper:
        supplier_urls: Dict[str, List[str]] = await scraper.get_award_supplier_urls(
            published_from_days=published_from_days,
            max_unique=max_suppliers,
        )
    suppliers_indexed = len(supplier_urls)

    # Optional fuzzy match when exact normalized name misses (e.g. "Acme Ltd" vs "Acme Limited")
    supplier_keys = list(supplier_urls.keys())

    matched: List[Tuple[int, str]] = []  # (company_id, notes)
    for cid, name in companies_by_id.items():
        key = normalize_name(name)
        urls = supplier_urls.get(key) if key else None
        if not urls and supplier_keys:
            from rapidfuzz import fuzz
            from rapidfuzz.process import extractOne
            out = extractOne(name, supplier_keys, scorer=fuzz.token_set_ratio, score_cutoff=80)
            if out:
                _best_key, _score, idx = out
                urls = supplier_urls.get(supplier_keys[idx])
        if not urls:
            continue
        # First N URLs for notes
        urls_str = ", ".join(urls[:MAX_NOTES_URLS])
        if len(urls) > MAX_NOTES_URLS:
            urls_str += f" (+{len(urls) - MAX_NOTES_URLS} more)"
        notes = f"{NOTES_PREFIX}{urls_str}"
        matched.append((cid, notes))

    # Update companies
    updated = 0
    for cid, notes in matched:
        stmt = select(CompanyModel).where(CompanyModel.id == cid)
        company = (await db.execute(stmt)).scalar_one_or_none()
        if company:
            company.has_gov_contract = True
            company.gov_contract_notes = notes
            updated += 1

    await db.commit()
    logger.info(
        "Contracts Finder cross-check: checked=%s, suppliers_indexed=%s, matched=%s, updated=%s",
        len(companies_by_id), suppliers_indexed, len(matched), updated,
    )
    return {
        "companies_checked": len(companies_by_id),
        "suppliers_indexed": suppliers_indexed,
        "companies_matched": len(matched),
        "companies_updated": updated,
    }

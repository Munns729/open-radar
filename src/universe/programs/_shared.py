"""
Shared utilities for RADAR Universe programs.
"""
import logging
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic
from openai import AsyncOpenAI
from sqlalchemy import or_, select

from src.core.database import engine
from src.core.utils import normalize_name
from src.universe.database import Base, CertificationModel, CompanyModel, CompanyRelationshipModel
from src.universe.ops.filters import PreEnrichmentFilter
from src.universe.status import reporter

logger = logging.getLogger(__name__)

# EU/EEA country codes for SME band logic
_EU_COUNTRIES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "NO", "IS", "LI",  # EEA
})


async def init_db():
    """Initialize database tables."""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_companies(session, companies_data: List[Dict], source: str) -> int:
    """Save scraped companies to DB with efficient deduplication. Returns count of new companies saved."""
    reporter.increment_stat("total_found", len(companies_data))

    if not companies_data:
        return 0

    count = 0

    # Efficiently find existing companies by collecting identifiers from the batch
    ch_numbers = [d['companies_house_number'] for d in companies_data if d.get('companies_house_number')]
    reg_numbers = [d['registration_number'] for d in companies_data if d.get('registration_number')]
    websites = [d['website'] for d in companies_data if d.get('website')]
    names = [d['name'] for d in companies_data if d.get('name')]

    # Normalize websites for lookup
    def norm_url(u):
        if not u:
            return ""
        return u.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")

    # Build filters
    filters = []
    if ch_numbers:
        filters.append(CompanyModel.companies_house_number.in_(ch_numbers))
    if reg_numbers:
        filters.append(CompanyModel.registration_number.in_(reg_numbers))
    if websites:
        filters.append(CompanyModel.website.in_(websites))
    if names:
        filters.append(CompanyModel.name.in_(names))

    existing_companies = []
    if filters:
        stmt = select(CompanyModel).where(or_(*filters))
        result = await session.execute(stmt)
        existing_companies = list(result.scalars().all())

    for data in companies_data:
        # Pre-Enrichment Filter (Lightweight)
        should_proc, reason = PreEnrichmentFilter.should_process(data)
        if not should_proc:
            pass

        existing = None

        # 1. Check Reg Numbers (Highest Confidence)
        if data.get('companies_house_number'):
            for ec in existing_companies:
                if ec.companies_house_number == data['companies_house_number']:
                    existing = ec
                    break

        if not existing and data.get('registration_number'):
            for ec in existing_companies:
                if ec.registration_number == data['registration_number']:
                    existing = ec
                    break

        # 2. Check Website (High Confidence)
        if not existing and data.get('website'):
            w_new = norm_url(data['website'])
            if w_new:
                for ec in existing_companies:
                    if norm_url(ec.website) == w_new:
                        existing = ec
                        break

        # 3. Check Name (Exact & Normalized)
        if not existing:
            norm_new = normalize_name(data['name'])
            for ec in existing_companies:
                if ec.name == data['name'] or normalize_name(ec.name) == norm_new:
                    existing = ec
                    break

        if not existing:
            company = CompanyModel(
                name=data['name'],
                hq_address=data.get('address'),
                hq_country=data.get('hq_country') or data.get('metadata', {}).get('country', 'GB'),
                discovered_via=source,
                website=data.get('website'),
                description=data.get('description')
            )
            existing_companies.append(company)
            session.add(company)
            await session.flush()

            # Add Certification
            if data.get('certification_number'):
                cert = CertificationModel(
                    company_id=company.id,
                    certification_type=data.get('certification_type'),
                    certification_number=data.get('certification_number'),
                    scope=data.get('scope'),
                    issuing_body=data.get('issuing_body'),
                    source_url=data.get('source_url')
                )
                session.add(cert)

            if reason:
                company.exclusion_reason = reason

            count += 1
        elif not existing.website and data.get('website'):
            existing.website = data.get('website')
            logger.info(f"Updated website for existing company {existing.name}: {existing.website}")

    await session.commit()
    logger.info(f"Saved {count} new companies from {source}")
    if count > 0:
        reporter.log(f"committed {count} new entities to database")
    return count


async def save_relationships(session, company_id: int, relationships: List[Dict]):
    """Save discovered relationships (kept for future use)."""
    count = 0
    company = await session.get(CompanyModel, company_id)
    if not company:
        return

    for rel in relationships:
        target_name = rel['entity_name']
        rel_type = rel['type']

        result = await session.execute(select(CompanyModel).where(CompanyModel.name == target_name))
        target = result.scalar_one_or_none()
        if not target:
            target = CompanyModel(name=target_name, discovered_via="relationship_enrichment")
            session.add(target)
            await session.flush()

        edge = CompanyRelationshipModel(
            company_a_id=company.id,
            company_b_id=target.id,
            relationship_type=rel_type,
            confidence=rel.get('confidence', 0.5),
            discovered_via=rel.get('source', 'unknown')
        )
        session.add(edge)
        count += 1

    await session.commit()
    if count > 0:
        logger.info(f"Saved {count} relationships for {company.name}")


async def _resolve_revenue_with_source(company, llm_revenue: int, ch_scraper, oc_scraper) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve revenue and source: validate LLM revenue against registry band,
    use band midpoint when misaligned. Returns (revenue_gbp, revenue_source).
    """
    from src.universe.revenue_bands import (
        revenue_plausible_uk,
        infer_eu_band_from_employees,
        infer_eu_band_from_officers_count,
    )
    from src.universe.scrapers.companies_house_scraper import CompaniesHouseScraper

    revenue = None
    source = None

    # --- UK: Companies House ---
    accounts_for_check = None
    ch_number = company.companies_house_number
    if ch_number:
        ch_details = await ch_scraper.get_company(ch_number)
        accounts_for_check = ch_details.get("accounts", {}) if ch_details else None
    elif company.hq_country == "GB":
        results = await ch_scraper.search_companies(company.name)
        if results:
            match = results[0]
            ch_number = match.get("company_number")
            if ch_number:
                ch_details = await ch_scraper.get_company(ch_number)
                accounts_for_check = ch_details.get("accounts", {}) if ch_details else None

    if accounts_for_check is not None:
        if revenue_plausible_uk(accounts_for_check, llm_revenue):
            revenue = llm_revenue
            source = "llm_website"
        else:
            band_result = CompaniesHouseScraper.get_band_midpoint(accounts_for_check)
            if band_result:
                midpoint, src = band_result
                revenue = midpoint
                source = src
                logger.info(
                    f"Using CH band midpoint £{midpoint:,} for {company.name} "
                    f"(LLM £{llm_revenue:,} misaligned with account type)"
                )
            else:
                logger.warning(
                    f"Rejecting LLM revenue £{llm_revenue:,} for {company.name} "
                    f"(CH band has no midpoint: dormant/no-accounts)"
                )
        return (revenue, source)

    # --- Non-UK: EU SME band (employees or officers_count) ---
    if company.hq_country in _EU_COUNTRIES:
        eu_band = None
        if company.employees and company.employees > 0:
            eu_band = infer_eu_band_from_employees(company.employees)
        if eu_band is None and company.registration_number:
            try:
                oc_results = await oc_scraper.search_companies(company.name, company.hq_country)
                if oc_results:
                    best = oc_results[0]
                    jur = best.get("jurisdiction")
                    reg = best.get("company_number")
                    if jur and reg:
                        profile = await oc_scraper.get_company(jur, reg)
                        if profile:
                            officers = profile.get("officers_count", 0)
                            eu_band = infer_eu_band_from_officers_count(officers)
            except Exception as e:
                logger.debug(f"OpenCorporates lookup for EU band failed: {e}")

        if eu_band is not None:
            cap, midpoint, src = eu_band[0], eu_band[1], eu_band[2]
            if llm_revenue <= cap:
                revenue = llm_revenue
                source = "llm_website"
            else:
                revenue = midpoint
                source = src
                logger.info(
                    f"Using EU band midpoint £{midpoint:,} for {company.name} "
                    f"(LLM £{llm_revenue:,} exceeds inferred band)"
                )
            return (revenue, source)

    # --- No registry data: hallucination guard ---
    if llm_revenue > 500_000_000:
        logger.warning(
            f"Rejecting LLM revenue £{llm_revenue:,} for {company.name} "
            f"(no registry data to verify; unverified large figures rejected)"
        )
        return (None, None)
    revenue = llm_revenue
    source = "llm_website"
    return (revenue, source)


def build_llm_clients(analysis_model: str = "auto") -> Tuple[Optional[Anthropic], Optional[AsyncOpenAI], Optional[str]]:
    """
    Build LLM clients for semantic enrichment based on config + override.
    Returns (anthropic_client, openai_client, openai_model_override).

    Priority: anthropic > moonshot > ollama
    analysis_model: "auto" | "ollama" | "moonshot" — overrides auto-detection.
    """
    from src.core.config import settings

    effective = analysis_model if analysis_model != "auto" else None

    anthropic_client = None
    openai_client = None
    openai_model_override = None

    if effective == "ollama":
        base = settings.openai_api_base or "http://localhost:11434/v1"
        openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key or "ollama",
            base_url=base,
        )
        openai_model_override = settings.browsing_model
    elif effective == "moonshot":
        openai_client = AsyncOpenAI(
            api_key=settings.moonshot_api_key or settings.openai_api_key,
            base_url=settings.kimi_api_base,
        )
    elif settings.anthropic_api_key and effective != "ollama":
        anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    elif settings.moonshot_api_key or settings.openai_api_key or settings.openai_api_base:
        base = settings.kimi_api_base if settings.moonshot_api_key else settings.openai_api_base
        openai_client = AsyncOpenAI(
            api_key=settings.moonshot_api_key or settings.openai_api_key or "ollama",
            base_url=base,
        )

    return (anthropic_client, openai_client, openai_model_override)

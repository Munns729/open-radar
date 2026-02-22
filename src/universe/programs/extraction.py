"""
Extraction program: CH, OC, website discovery, LLM description, website scrape.
Zone 2: Companies House, OpenCorporates, website discovery, LLM enrichment, scraping.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import or_, select, update, nulls_first
from sqlalchemy.orm import selectinload

from src.core.thesis import thesis
from src.universe.database import CompanyModel
from src.universe.ops.filters import PreEnrichmentFilter
from src.universe.programs._shared import _resolve_revenue_with_source
from src.universe.scrapers import (
    CompaniesHouseScraper,
    OpenCorporatesScraper,
    WebsiteScraper,
)
from src.universe.agents import WebsiteExtractionAgent
from src.universe.agents.website_extraction_agent import _is_blocked_url
from src.universe.ops.website_validator import is_likely_company_site, is_url_acceptable_for_company
from src.universe.status import reporter

logger = logging.getLogger(__name__)


async def run_extraction(
    session,
    target_ids: Optional[List[int]] = None,
    min_revenue: Optional[int] = None,
    countries: Optional[List[str]] = None,
    force: bool = False,
    limit: int = 50,
) -> None:
    """
    Extraction & Enrichment: Run on companies where extraction_complete_at IS NULL.
    1. Companies House / OpenCorporates (financials, SIC, registration)
    2. Website discovery (agent search) + LLM enrichment + scraping
    3. Sets extraction_complete_at when done (required for Scoring)
    """
    stmt = select(CompanyModel).where(CompanyModel.extraction_complete_at == None)

    if target_ids:
        stmt = stmt.where(CompanyModel.id.in_(target_ids))

    if min_revenue:
        stmt = stmt.where(CompanyModel.revenue_gbp >= min_revenue)

    if countries:
        stmt = stmt.where(CompanyModel.hq_country.in_(countries))

    pf = thesis.pipeline_filters
    if pf.max_revenue_exclude is not None:
        stmt = stmt.where(
            or_(CompanyModel.revenue_gbp == None, CompanyModel.revenue_gbp <= pf.max_revenue_exclude)
        )
    if pf.exclude_sectors:
        stmt = stmt.where(
            or_(CompanyModel.sector == None, ~CompanyModel.sector.in_(pf.exclude_sectors))
        )
    if not force:
        days = getattr(pf, "enrichment_skip_days", 7.0)
        if days and days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(
                or_(CompanyModel.last_updated == None, CompanyModel.last_updated < cutoff)
            )
    stmt = stmt.order_by(nulls_first(CompanyModel.last_updated.asc()))

    if limit:
        stmt = stmt.limit(limit)

    stmt = stmt.options(selectinload(CompanyModel.certifications))

    result = await session.execute(stmt)
    companies = result.scalars().all()

    logger.info(f"Enriching {len(companies)} companies...")

    logger.info("=" * 50)
    logger.info("Zone 2: Extraction Strategy (Agentic Hand-off)")
    logger.info("=" * 50)
    reporter.set_zone(2, "Extraction & Enrichment Phase")
    reporter.update_stats("total_found", len(companies))

    ch_scraper = CompaniesHouseScraper()
    web_scraper = WebsiteScraper()
    oc_scraper = OpenCorporatesScraper()

    async with ch_scraper, WebsiteExtractionAgent() as extraction_agent:
        for company in companies:
            should_enr, reason = PreEnrichmentFilter.should_enrich(company)
            if not should_enr and not force:
                logger.debug(f"Skipping enrichment for {company.name}: {reason}")
                await session.execute(
                    update(CompanyModel).where(CompanyModel.id == company.id).values(exclusion_reason=reason)
                )
                await session.commit()
                continue

            if company.exclusion_reason:
                company.exclusion_reason = None

            skip_days = getattr(thesis.pipeline_filters, "enrichment_skip_days", 7.0) or 7.0
            if skip_days > 0 and not force and company.last_updated:
                last_upd = company.last_updated
                if last_upd.tzinfo is None:
                    last_upd = last_upd.replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                if (now_utc - last_upd).total_seconds() < skip_days * 86400:
                    logger.debug(f"Skipping recently updated company: {company.name}")
                    continue

            logger.info(f"Entity: {company.name}")
            reporter.set_action(f"Processing {company.name}...")
            reporter.log(f"Enriching Data for {company.name}")
            updated = False

            # A0. Companies House turnover from filed accounts (iXBRL)
            if company.hq_country == "GB" and company.companies_house_number and not company.revenue_gbp:
                try:
                    turnover = await ch_scraper.get_turnover_from_filings(company.companies_house_number)
                    if turnover and turnover > 0:
                        company.revenue_gbp = turnover
                        company.revenue_source = "ch_filing"
                        updated = True
                        logger.info(f"Set revenue £{turnover:,} from CH filings for {company.name}")
                except Exception as e:
                    logger.debug(f"CH filings turnover fetch failed for {company.name}: {e}")

            # A. Companies House (UK ONLY) - match and enrich when no CH number
            if company.hq_country == 'GB' and not company.companies_house_number:
                results = await ch_scraper.search_companies(company.name)
                if results:
                    match = results[0]
                    ch_number = match.get('company_number')

                    result = await session.execute(select(CompanyModel).where(CompanyModel.companies_house_number == ch_number))
                    existing_ch = result.scalar_one_or_none()
                    if existing_ch and existing_ch.id != company.id:
                        logger.warning(f"Collision: {company.name} matches {ch_number} which belongs to {existing_ch.name}. Skipping update.")
                    else:
                        company.companies_house_number = ch_number
                        company.legal_name = match.get('title')

                        details = await ch_scraper.get_company(company.companies_house_number)
                        if details:
                            company.description = ch_scraper._get_sic_description(details.get("sic_codes", []))

                            est = ch_scraper._estimate_size(details.get("accounts", {}))
                            if est.get("employees"):
                                company.employees = est["employees"]
                            if not company.revenue_gbp:
                                try:
                                    turnover = await ch_scraper.get_turnover_from_filings(company.companies_house_number)
                                    if turnover and turnover > 0:
                                        company.revenue_gbp = turnover
                                        company.revenue_source = "ch_filing"
                                        logger.info(f"Set revenue £{turnover:,} from CH filings for {company.name}")
                                except Exception as e:
                                    logger.debug(f"CH filings turnover fetch failed: {e}")

                            updated = True

            # A1b. OpenCorporates (non-GB European companies)
            if company.hq_country != 'GB' and not company.registration_number:
                try:
                    oc_results = await oc_scraper.search_companies(company.name, company.hq_country)
                    if oc_results:
                        best = oc_results[0]
                        reg_num = best.get('company_number')
                        if reg_num and isinstance(reg_num, str):
                            company.registration_number = reg_num

                        legal = best.get('name')
                        if legal and isinstance(legal, str) and not company.legal_name:
                            company.legal_name = legal

                        comp_type = best.get('company_type')
                        if comp_type and isinstance(comp_type, str) and not company.description:
                            company.description = f"{comp_type} ({company.hq_country})"

                        jurisdiction = best.get('jurisdiction')
                        if jurisdiction and reg_num:
                            profile = await oc_scraper.get_company(jurisdiction, reg_num)
                            if profile and not company.employees:
                                est = OpenCorporatesScraper.estimate_company_size(profile.get('officers_count', 0))
                                if est and isinstance(est, int):
                                    company.employees = est

                        updated = True
                        logger.info(f"OpenCorporates enriched {company.name}: reg={reg_num}")
                except Exception as e:
                    logger.warning(f"OpenCorporates lookup failed for {company.name}: {e}")

            # A2. Website Discovery
            if not company.website and company.hq_country == "GB" and company.companies_house_number:
                if not company.description or company.description.startswith("Discovered on"):
                    try:
                        details = await ch_scraper.get_company(company.companies_house_number)
                        if details:
                            sic_desc = ch_scraper._get_sic_description(details.get("sic_codes", []))
                            if sic_desc and "unknown" not in sic_desc.lower():
                                company.description = sic_desc
                                updated = True
                    except Exception as e:
                        logger.debug(f"CH fetch for search context failed: {e}")
            if not company.website:
                try:
                    logger.info("No website found, using Agent to search...")
                    cert_types = [c.certification_type for c in (company.certifications or []) if c.certification_type]
                    discovered_url = await extraction_agent.find_website_url(
                        company.name,
                        description=company.description,
                        sector=company.sector,
                        sub_sector=company.sub_sector,
                        certifications=cert_types if cert_types else None,
                        hq_city=company.hq_city,
                        hq_address=company.hq_address,
                        hq_country=company.hq_country,
                    )
                    if discovered_url and isinstance(discovered_url, str):
                        if _is_blocked_url(discovered_url):
                            logger.debug(f"Rejecting registry URL for {company.name}: {discovered_url}")
                        else:
                            url_ok, url_reason = is_url_acceptable_for_company(discovered_url, company.name)
                            if not url_ok:
                                logger.info(f"Rejecting discovered URL for {company.name}: {url_reason}")
                            else:
                                company.website = discovered_url
                                logger.info(f"Discovered website for {company.name}: {discovered_url}")
                                updated = True
                except Exception as e:
                    logger.warning(f"Website discovery failed for {company.name}: {e}")

            # A3. LLM-based Enrichment
            is_placeholder = company.description and company.description.startswith("Discovered on")
            if company.website and (not company.description or is_placeholder):
                try:
                    logger.info(f"Running LLM enrichment for {company.name}...")
                    enrichment_data = await extraction_agent.run(company.name, company.website)

                    if enrichment_data.get("_url_valid") is False:
                        logger.info(f"Rejecting URL for {company.name} (failed website check)")
                        company.website = None
                        if company.raw_website_text:
                            company.raw_website_text = None
                        updated = True
                    else:
                        desc = enrichment_data.get("description")
                        if desc and isinstance(desc, str):
                            company.description = desc
                            logger.info(f"LLM enriched description for {company.name}")

                        sector = enrichment_data.get("sector")
                        if sector and isinstance(sector, str) and not company.sector:
                            company.sector = sector

                        sub_sector = enrichment_data.get("sub_sector")
                        if sub_sector and isinstance(sub_sector, str) and not company.sub_sector:
                            company.sub_sector = sub_sector

                        city = enrichment_data.get("city")
                        if city and isinstance(city, str) and not company.hq_city:
                            company.hq_city = city

                        employees = enrichment_data.get("employees")
                        if employees and isinstance(employees, int):
                            company.employees = employees
                            logger.info(f"Updated employee count for {company.name}: {employees}")

                        revenue = enrichment_data.get("revenue")
                        if revenue and isinstance(revenue, int):
                            resolved_rev, resolved_src = await _resolve_revenue_with_source(
                                company, revenue, ch_scraper, oc_scraper
                            )
                            if resolved_rev is not None:
                                company.revenue_gbp = resolved_rev
                                company.revenue_source = resolved_src

                        updated = True
                except Exception as e:
                    logger.warning(f"LLM enrichment failed for {company.name}: {e}")

            # B. Website Scraping (Keywords + Description Refinement)
            if company.website:
                if _is_blocked_url(company.website):
                    logger.debug(f"Skipping scrape of registry URL for {company.name}: {company.website}")
                    company.website = None
                    if company.raw_website_text:
                        company.raw_website_text = None
                        updated = True
                else:
                    try:
                        logger.debug(f"Check Website Type -> {company.website}")
                        web_data = await web_scraper.scrape(company.website)
                        raw_text = web_data.get("raw_text")
                        if raw_text and isinstance(raw_text, str):
                            valid, reason = is_likely_company_site(company.name, raw_text)
                            if not valid:
                                logger.info(f"Website validation failed for {company.name}: {reason}")
                                company.website = None
                                company.raw_website_text = None
                                updated = True
                            else:
                                company.raw_website_text = raw_text
                                logger.info(f"Stored {len(raw_text)} chars of website text for {company.name}")
                                web_desc = web_data.get("description")
                                if web_desc and isinstance(web_desc, str):
                                    company.description = (company.description or "") + " | " + web_desc
                                if not company.moat_attributes:
                                    company.moat_attributes = {}
                                keywords = web_data.get("keywords_found", {})
                                if isinstance(keywords, dict):
                                    for k, v in keywords.items():
                                        if v:
                                            company.moat_attributes[f"keyword_{k}"] = True
                                updated = True
                    except Exception as e:
                        logger.warning(f"Website scrape failed for {company.website}: {e}")
                        company.website = None
                        if company.raw_website_text:
                            company.raw_website_text = None
                        updated = True

            company.extraction_complete_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()

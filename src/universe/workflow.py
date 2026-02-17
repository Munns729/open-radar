"""
Orchestrator for Universe Scanner (Module 1).
"""
import asyncio
import logging
import argparse
import os
from typing import List, Dict, Any
from datetime import datetime

from src.universe.database import Base, CompanyModel, CertificationModel, CompanyRelationshipModel
from src.universe.scrapers import AS9100Scraper, CompaniesHouseScraper, ISORegistryScraper, WebsiteScraper, RelationshipEnricher, EuropeanDiscoveryScraper, WikipediaDiscoveryScraper, ClutchDiscoveryScraper, GoodFirmsAgentScraper, UniverseEnrichmentAgent, CrunchbaseDiscoveryScraper
from src.universe.scrapers.g_cloud_scraper import GCloudScraper
from src.universe.scrapers.ugap_scraper import UGAPScraper
from src.universe.scrapers.growth_scrapers import DeloitteFast50Scraper, FT1000Scraper
from src.universe.scrapers.vertical_associations_scraper import VerticalAssociationsScraper
from src.universe.scrapers.opencorporates_scraper import OpenCorporatesScraper
from src.universe.moat_scorer import MoatScorer
from src.universe.graph_analyzer import GraphAnalyzer
from src.universe.discovery.semantic_enrichment import enrich_companies_batched
from src.core.utils import normalize_name
from src.universe.ops.filters import PreEnrichmentFilter
from src.universe.ops.cost_tracker import cost_tracker
from sqlalchemy import or_, and_, select, func
from anthropic import Anthropic
from datetime import datetime
from src.core.models import CompanyTier, MoatType
from src.universe.status import reporter # Use shared instance
from src.core.database import engine, get_async_db

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database tables"""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_companies(session, companies_data: List[Dict], source: str):
    """Save scraped companies to DB with efficient deduplication."""
    reporter.increment_stat("total_found", len(companies_data))
    
    if not companies_data:
        return

    count = 0
    
    # Efficiently find existing companies by collecting identifiers from the batch
    ch_numbers = [d['companies_house_number'] for d in companies_data if d.get('companies_house_number')]
    reg_numbers = [d['registration_number'] for d in companies_data if d.get('registration_number')]
    websites = [d['website'] for d in companies_data if d.get('website')]
    names = [d['name'] for d in companies_data if d.get('name')]
    
    # Normalize websites for lookup
    def norm_url(u):
        if not u: return ""
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
            # We still save them so the user can see WHY they were excluded
            # but we mark them as excluded. 
            pass
            # Actually, the user might not want junk. 
            # But the user specifically asked to see the reason in the filter.
            # Let's proceed with saving them but marking them.

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
            await session.flush() # get ID
            
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

async def save_relationships(session, company_id: int, relationships: List[Dict]):
    """Save discovered relationships"""
    count = 0
    company = await session.get(CompanyModel, company_id)
    if not company:
        return

    for rel in relationships:
        target_name = rel['entity_name']
        rel_type = rel['type'] # customer, supplier, partner
        
        # simple check: Find or create target company (as node only)
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

async def enrich_companies(session, target_ids: List[int] = None, min_revenue: int = None, countries: List[str] = None, force: bool = False, limit: int = 50):
    """
    Phase 2: Data Enrichment on existing companies.
    1. Companies House Data (Financials, SIC)
    2. Website Content (Description, Keywords)
    3. Relationships (Customers, Suppliers)
    """
    # 1. Get companies needing enrichment
    # For now, we enrich all countries, but CH is only for GB
    stmt = select(CompanyModel)
    
    if target_ids:
        stmt = stmt.where(CompanyModel.id.in_(target_ids))
    
    if min_revenue:
        stmt = stmt.where(CompanyModel.revenue_gbp >= min_revenue)
    
    if countries:
        stmt = stmt.where(CompanyModel.hq_country.in_(countries))
    
    # If no specific filters, default to companies lacking critical data
    if not target_ids and not min_revenue and not countries:
        # Enrich if: Missing Description OR (Is GB & Missing CH) OR (Not GB & Missing Reg)
        stmt = stmt.where(or_(
            CompanyModel.description == None,
            and_(CompanyModel.hq_country == 'GB', CompanyModel.companies_house_number == None),
            and_(CompanyModel.hq_country != 'GB', CompanyModel.registration_number == None)
        ))
        
    # Apply limit to prevent OOM with large datasets (e.g. 225k pending)
    if limit:
        stmt = stmt.limit(limit)
        
    result = await session.execute(stmt)
    companies = result.scalars().all()
    
    logger.info(f"Enriching {len(companies)} companies...")
    
    # VISUALIZATION: Zone 2
    print("\n" + "="*50)
    print("[FLOW] Zone 2: Extraction Strategy (Agentic Hand-off)")
    print("="*50 + "\n")
    reporter.set_zone(2, "Extraction & Enrichment Phase")
    reporter.update_stats("total_found", len(companies))
    
    # Agents
    ch_scraper = CompaniesHouseScraper()
    web_scraper = WebsiteScraper()
    rel_enricher = RelationshipEnricher()
    oc_scraper = OpenCorporatesScraper()
    
    # Run scrapers inside context
    async with ch_scraper, rel_enricher, UniverseEnrichmentAgent() as enrichment_agent:
        for company in companies:
            # Pre-Enrichment Filter (Database level)
            should_enr, reason = PreEnrichmentFilter.should_enrich(company)
            if not should_enr and not force:
                logger.info(f"Skipping enrichment for {company.name}: {reason}")
                company.exclusion_reason = reason
                await session.commit()
                continue
            
            # If it was excluded before but now should be enriched, clear reason
            if company.exclusion_reason:
                company.exclusion_reason = None

            # Retry/Checkpoint Logic (Optimization)
            # Skip if updated in last 7 days (unless forcing)
            if not force and company.last_updated and (datetime.utcnow() - company.last_updated).days < 7:
                logger.info(f"Skipping recently updated company: {company.name}")
                continue

            print(f"\n[FLOW] Entity: {company.name}")
            reporter.set_action(f"Processing {company.name}...")
            reporter.log(f"Enriching Data for {company.name}")
            updated = False
            
            # A. Companies House (UK ONLY)
            if company.hq_country == 'GB' and not company.companies_house_number:
                results = await ch_scraper.search_companies(company.name)
                if results:
                    match = results[0]
                    ch_number = match.get('company_number')
                    
                    # Check for collision
                    result = await session.execute(select(CompanyModel).where(CompanyModel.companies_house_number == ch_number))
                    existing_ch = result.scalar_one_or_none()
                    if existing_ch and existing_ch.id != company.id:
                        logger.warning(f"Collision: {company.name} matches {ch_number} which belongs to {existing_ch.name}. Skipping update.")
                        pass
                    else:
                        company.companies_house_number = ch_number
                        company.legal_name = match.get('title')
                        
                        # Fetch Full Profile for SIC/Accounts
                        details = await ch_scraper.get_company(company.companies_house_number)
                        if details:
                            company.description = ch_scraper._get_sic_description(details.get("sic_codes", []))
                            
                            # Size: Strict Actuals Only (No Estimates)
                            est = ch_scraper._estimate_size(details.get("accounts", {}))
                            if est.get("employees"):
                                company.employees = est["employees"]
                            if est.get("revenue_int") and not company.revenue_gbp:
                                company.revenue_gbp = est["revenue_int"]
                            
                            updated = True

            # A1b. OpenCorporates (non-GB European companies)
            if company.hq_country != 'GB' and not company.registration_number:
                try:
                    oc_results = await oc_scraper.search_companies(company.name, company.hq_country)
                    if oc_results:
                        best = oc_results[0]
                        reg_num = best.get('company_number')
                        if reg_num and isinstance(reg_num, str):
                            company.registration_number = reg_num  # Use dedicated field for non-UK
                        
                        legal = best.get('name')
                        if legal and isinstance(legal, str) and not company.legal_name:
                            company.legal_name = legal
                        
                        comp_type = best.get('company_type')
                        if comp_type and isinstance(comp_type, str) and not company.description:
                            company.description = f"{comp_type} ({company.hq_country})"
                        
                        # Try to get full profile for officer-based size estimate
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

            # A2. Website Discovery (reuses shared browser)
            if not company.website:
                try:
                    print(f"[FLOW] No website found, using Agent to search...")
                    discovered_url = await enrichment_agent.find_website_url(company.name)
                    if discovered_url and isinstance(discovered_url, str):
                        company.website = discovered_url
                        logger.info(f"Discovered website for {company.name}: {discovered_url}")
                        updated = True
                except Exception as e:
                    logger.warning(f"Website discovery failed for {company.name}: {e}")
            
            # A3. LLM-based Enrichment (reuses shared browser)
            # Allow strings starting with "Discovered on" to be overwritten
            is_placeholder = company.description and company.description.startswith("Discovered on")
            if company.website and (not company.description or is_placeholder):
                try:
                    print(f"[FLOW] Running LLM enrichment for {company.name}...")
                    enrichment_data = await enrichment_agent.run(company.name, company.website)
                    
                    # Type-safe DB writes: validate types before assigning to columns
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
                    
                    # Size (Prioritize extracted actuals over CH estimates)
                    employees = enrichment_data.get("employees")
                    if employees and isinstance(employees, int):
                        company.employees = employees
                        logger.info(f"Updated employee count for {company.name}: {employees}")
                        
                    revenue = enrichment_data.get("revenue")
                    if revenue and isinstance(revenue, int):
                        company.revenue_gbp = revenue
                    
                    updated = True
                except Exception as e:
                    logger.warning(f"LLM enrichment failed for {company.name}: {e}")

            # B. Website Scraping (Keywords + Description Refinement)
            if company.website:
                # Basic scraping (or Deep if configured/needed)
                try:
                    print(f"[FLOW] Check Website Type -> {company.website}")
                    web_data = await web_scraper.scrape(company.website)
                    
                    # Store raw website text for LLM analysis
                    raw_text = web_data.get("raw_text")
                    if raw_text and isinstance(raw_text, str):
                        company.raw_website_text = raw_text
                        logger.info(f"Stored {len(raw_text)} chars of website text for {company.name}")
                    
                    web_desc = web_data.get("description")
                    if web_desc and isinstance(web_desc, str):
                         company.description = (company.description or "") + " | " + web_desc
                    
                    # Keywords -> Moat Attributes
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
                
            # C. Relationship Enrichment (All Regions)
            if company.website:
                try:
                    rels = await rel_enricher.find_relationships(company.name, company.website)
                    await save_relationships(session, company.id, rels)
                except Exception as e:
                    logger.warning(f"Relationship enrichment failed for {company.name}: {e}")

            if updated:
                await session.commit()

async def run_scoring_pipeline(session, min_revenue: int = None, countries: List[str] = None):
    """
    Phase 3: Graph Analysis & Scoring.
    """
    logger.info("Running Scoring Pipeline...")
    
    # VISUALIZATION: Zone 3
    print("\n" + "="*50)
    print("[FLOW] Zone 3: Intelligence (LLM & Vector DB)")
    print("="*50 + "\n")
    reporter.set_zone(3, "Intelligence & Scoring Phase")
    
    # 1. Graph Analysis
    analyzer = GraphAnalyzer(session)
    await analyzer.build_graph()
    
    # Initialize Anthropic client for semantic enrichment
    # Initialize LLM client for semantic enrichment (Anthropic or OpenAI/Moonshot)
    from src.core.config import settings
    anthropic_client = None
    openai_client = None
    
    if settings.anthropic_api_key:
        anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    elif settings.moonshot_api_key or settings.openai_api_key:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(
            api_key=settings.moonshot_api_key or settings.openai_api_key,
            base_url=settings.kimi_api_base if settings.moonshot_api_key else None
        )
    
    # 2. Update Scores
    # Only score companies that have been enriched or are targets
    # 2. Update Scores
    # Only score companies that have been enriched or are targets
    from sqlalchemy.orm import selectinload
    stmt = select(CompanyModel).options(
        selectinload(CompanyModel.certifications),
        selectinload(CompanyModel.relationships_as_a),
        selectinload(CompanyModel.relationships_as_b)
    )
    if min_revenue:
        stmt = stmt.where(CompanyModel.revenue_gbp >= min_revenue)
    
    if countries:
        stmt = stmt.where(CompanyModel.hq_country.in_(countries))
        
    result = await session.execute(stmt)
    companies = result.scalars().all()
    
    # 2. Batch Semantic Enrichment (Claude Haiku)
    # Only enrich companies that have website text and haven't been semantically enriched
    to_semantic_enrich = [
        c for c in companies 
        if c.raw_website_text and not c.semantic_enriched_at
    ]
    
    if to_semantic_enrich:
        print(f"[FLOW] Batch Semantically Enriching {len(to_semantic_enrich)} companies...")
        # Prepare data for batch processing
        batch_input = [
            {
                "id": c.id,
                "name": c.name,
                "country": c.hq_country,
                "website_text": c.raw_website_text,
                "description": c.description,
                "certifications": [cert.certification_type for cert in (c.certifications or [])]
            }
            for c in to_semantic_enrich
        ]
        
        # Run batch enrichment (handles batching internally)
        results = await enrich_companies_batched(
            batch_input, 
            anthropic_client=anthropic_client,
            openai_client=openai_client  # Pass the fallback client
        )
        
        # Map results back to companies
        result_map = {r.company_id: r for r in results}
        for c in to_semantic_enrich:
            res = result_map.get(c.id)
            if res and res.enrichment_successful:
                if not c.moat_analysis:
                    c.moat_analysis = {}
                c.moat_analysis["semantic"] = res.to_dict()
                c.semantic_enriched_at = datetime.utcnow()
                logger.info(f"Semantically enriched {c.name}")
        
        await session.commit()

    # 3. Update Scores
    from src.universe.database import ScoringEvent
    
    for company in companies:
        result = await session.execute(select(CertificationModel).where(CertificationModel.company_id == company.id))
        certs = result.scalars().all()
        
        # Get Graph Signals
        graph_signals = analyzer.get_moat_signals(company.id)
        
        # Score with LLM (Enhanced Deep Logic)
        raw_website_text = company.raw_website_text or ""
        await MoatScorer.score_with_llm(company, certs, graph_signals, raw_website_text)
        
        # --- Audit Trail: Record ScoringEvent ---
        previous_score = getattr(company, '_previous_moat_score', None)
        previous_attrs = getattr(company, '_previous_moat_attributes', None)
        
        # Compute per-pillar diff
        changes = {}
        for pillar in ["regulatory", "network", "geographic", "liability", "physical"]:
            old_s = (previous_attrs or {}).get(pillar, {}).get("score", 0) if isinstance(previous_attrs, dict) else 0
            new_s = (company.moat_attributes or {}).get(pillar, {}).get("score", 0) if isinstance(company.moat_attributes, dict) else 0
            if old_s != new_s:
                changes[pillar] = {
                    "old": old_s,
                    "new": new_s,
                    "delta": new_s - old_s,
                    "old_justification": (previous_attrs or {}).get(pillar, {}).get("justification", "") if isinstance(previous_attrs, dict) else "",
                    "new_justification": (company.moat_attributes or {}).get(pillar, {}).get("justification", "") if isinstance(company.moat_attributes, dict) else "",
                }
        
        # Determine trigger type
        trigger = "initial" if previous_score is None or previous_score == 0 else "rescan"
        
        event = ScoringEvent(
            company_id=company.id,
            moat_score=company.moat_score,
            tier=company.tier.value if company.tier else "waitlist",
            moat_attributes=company.moat_attributes,
            weights_used=MoatScorer.MOAT_WEIGHTS,
            previous_score=previous_score if previous_score else None,
            score_delta=(company.moat_score - previous_score) if previous_score else None,
            changes=changes if changes else None,
            trigger=trigger,
        )
        session.add(event)
        
        await session.commit()
    
    logger.info("Scoring Complete.")

async def build_universe(mode: str, sources: List[str] = None, min_revenue: int = None, countries: List[str] = None, force: bool = False, limit: int = 15):
    """
    Orchestrator function.
    """
    logger.info(f"Starting Universe Build (Mode: {mode}, Sources: {sources}, Min Revenue: {min_revenue}, Countries: {countries}, Limit: {limit})")
    
    # VISUALIZATION: Zone 1
    print("\n" + "="*50)
    print("[FLOW] Zone 1: Discovery (The Funnel)")
    print("="*50 + "\n")
    reporter.set_active()
    reporter.set_zone(1, "Discovery Phase Initiated")
    
    await init_db()
    
    # Database Context
    async with get_async_db() as session:
        try:
            # Default sources if None
            if not sources:
                sources = ["AS9100", "ISO9001", "Wikipedia", "Clutch", "GoodFirms"]

            # 1. Discover New Leads (Mocks)
            if mode == "full":
                # (Discovery logic remains same for now)
                
                # AS9100 (Mock)
                if "AS9100" in sources:
                    async with AS9100Scraper() as scraper:
                        as9100 = await scraper.scrape_by_country("United Kingdom")
                        await save_companies(session, as9100.data, "AS9100")
                
                # ISO9001 (Mock)
                if "ISO9001" in sources:
                    async with ISORegistryScraper() as scraper:
                        iso9001 = await scraper.scrape_iso9001()
                        await save_companies(session, iso9001.data, "ISO9001")

                # European Discovery (NEW - Wikipedia)
                if "Wikipedia" in sources:
                    async with WikipediaDiscoveryScraper() as scraper:
                        target_regions = countries if countries else ["FR", "DE", "NL", "BE", "LU"]
                        valid_codes = ["FR", "DE", "NL", "BE"]
                        for code in target_regions:
                            if code in valid_codes:
                                eu_data = await scraper.discover_region(code, limit=limit)
                                await save_companies(session, eu_data.data, f"Wiki-Discovery-{code}")
                
                # Clutch Discovery (Niche Tech Services)
                if "Clutch" in sources:
                    async with ClutchDiscoveryScraper() as scraper:
                        clutch_targets = countries if countries else ["FR", "DE"]
                        clutch_valid = ["FR", "DE", "UK", "NL", "PL"]
                        for code in clutch_targets:
                                clutch_data = await scraper.discover_tech_services(code, limit=limit)
                                await save_companies(session, clutch_data.data, f"Clutch-Discovery-{code}")
                
                # GoodFirms Agent Discovery (High Value Tech Services)
                if "GoodFirms" in sources:
                    async with GoodFirmsAgentScraper(headless=True) as scraper:
                        gf_targets = countries if countries else ["FR"]
                        for code in gf_targets:
                            country_map = {"FR": "France", "DE": "Germany", "UK": "United Kingdom", "NL": "Netherlands"}
                            country_name = country_map.get(code)
                            if country_name:
                                for term in ["Cybersecurity", "Artificial Intelligence"]:
                                    gf_data = await scraper.discover(term=term, country=country_name, limit=limit)
                                    await save_companies(session, gf_data.data, f"GoodFirms-Agent-{code}-{term}")
                
                # Crunchbase Discovery (NEW)
                if "Crunchbase" in sources:
                     async with CrunchbaseDiscoveryScraper() as scraper:
                        cb_targets = countries if countries else ["UK", "Europe"]
                        for code in cb_targets:
                            cb_data = await scraper.discover_companies(code, limit=15)
                            await save_companies(session, cb_data.data, f"Crunchbase-{code}")

                # --- NEW DISCOVERY SOURCES (Tiered Strategy) ---
                
                # Tier 1: Government Procurement (Services Focus)
                if "GCloud" in sources:
                    async with GCloudScraper() as scraper:
                        # Target Lot 3 (Support) mainly
                        gc_data = await scraper.scrape(target_lots=["cloud-support"], limit_per_lot=20)
                        await save_companies(session, gc_data.data, "G-Cloud-UK")
                        
                if "UGAP" in sources:
                    async with UGAPScraper() as scraper:
                        ugap_data = await scraper.scrape(limit=20)
                        await save_companies(session, ugap_data.data, "UGAP-FR")
                        
                # Tier 2: Growth Signals
                if "Deloitte" in sources or "Fast50" in sources:
                    async with DeloitteFast50Scraper() as scraper:
                        # Default to UK for now
                        d_data = await scraper.scrape(region="UK")
                        await save_companies(session, d_data, "DeloitteFast50-UK")
                        
                if "FT1000" in sources:
                    async with FT1000Scraper() as scraper:
                        ft_data = await scraper.scrape()
                        await save_companies(session, ft_data, "FT1000-Europe")
                        
                # Tier 3: Vertical Associations
                if "Verticals" in sources:
                    async with VerticalAssociationsScraper() as scraper:
                        v_data = await scraper.scrape()
                        await save_companies(session, v_data, "VerticalAssocs")
            
            # 2. Enrich (Web + Companies House + Relationships)
            if mode in ["full", "enrich"]:
                await enrich_companies(session, min_revenue=min_revenue, countries=countries, force=force)
            
            # 3. Analyze & Score (Graph + Picard Logic)
            await run_scoring_pipeline(session, min_revenue=min_revenue, countries=countries)
            
            # 4. Report Stats
            result = await session.execute(select(func.count(CompanyModel.id)))
            total = result.scalar() or 0
            
            result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_1A))
            tier1a = result.scalar() or 0
            
            result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_1B))
            tier1b = result.scalar() or 0
            
            result = await session.execute(select(func.count(CompanyModel.id)).where(CompanyModel.tier == CompanyTier.TIER_2))
            tier2 = result.scalar() or 0
            
            print("\n--- PICARD UNIVERSE STATUS ---")
            print(f"Total Companies: {total}")
            print(f"Tier 1A (Permanent Moats): {tier1a}")
            print(f"Tier 1B (Strong Defensibility): {tier1b}")
            print(f"Tier 2 (Opportunistic): {tier2}")
            print(f"Total Session Cost: ${cost_tracker.get_total_cost():.4f}")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Workflow failed: {e}\n{tb}")
            with open("scan_error.log", "w") as f:
                f.write(f"Error: {repr(e)}\n")
                f.write(tb)
            reporter.state["status"] = "error"
            reporter.log(f"CRITICAL ERROR: {repr(e)}")
            raise  # Let context manager handle rollback

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="full", choices=["full", "incremental", "enrich"])
    parser.add_argument("--min-revenue", type=int, default=None, help="Minimum revenue in GBP")
    parser.add_argument("--countries", nargs="+", help="List of country codes to process (e.g. FR DE)")
    parser.add_argument("--sources", nargs="+", help="List of sources (AS9100, ISO9001, Wikipedia, Clutch, GoodFirms, Crunchbase, GCloud, UGAP, Deloitte, FT1000, Verticals)")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment even if recently updated")
    parser.add_argument("--limit", type=int, default=15, help="Number of companies to discover per source/region")
    args = parser.parse_args()
    
    asyncio.run(build_universe(args.mode, args.sources, args.min_revenue, args.countries, args.force, args.limit))

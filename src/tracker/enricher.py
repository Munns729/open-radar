"""
Enrichment pipeline for Module 3 - Target Tracker.

Aggregates data from multiple RADAR modules to build comprehensive
company profiles and detect significant events.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory, async_session_factory
from src.tracker.database import CompanyEvent, EventType, EventSeverity

logger = logging.getLogger(__name__)


class CompanyEnricher:
    """
    Enriches tracked company profiles by aggregating data from
    multiple RADAR modules.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize the enricher.
        
        Args:
            session: Optional async database session. If not provided,
                     will create sessions as needed.
        """
        self.session = session

    async def enrich_tracked_company(self, company_id: int) -> Dict[str, Any]:
        """
        Pull and aggregate data from multiple sources for a tracked company.
        
        Args:
            company_id: The ID of the company in the universe database.
            
        Returns:
            Dict containing aggregated company profile data.
        """
        profile: Dict[str, Any] = {
            "company_id": company_id,
            "enriched_at": datetime.utcnow().isoformat(),
            "base_data": None,
            "vc_activity": [],
            "pe_investments": [],
            "threat_analysis": None,
        }

        # 1. Get base company data from Universe
        try:
            async with async_session_factory() as universe_session:
                from src.universe.database import CompanyModel
                
                stmt = select(CompanyModel).where(CompanyModel.id == company_id)
                result = await universe_session.execute(stmt)
                company = result.scalar_one_or_none()
                
                if company:
                    profile["base_data"] = {
                        "id": company.id,
                        "name": company.name,
                        "legal_name": company.legal_name,
                        "website": company.website,
                        "description": company.description,
                        "sector": company.sector,
                        "revenue_gbp": company.revenue_gbp,
                        "ebitda_gbp": company.ebitda_gbp,
                        "employees": company.employees,
                        "moat_score": company.moat_score,
                        "moat_type": str(company.moat_type) if company.moat_type else None,
                        "tier": str(company.tier) if company.tier else None,
                        "hq_country": company.hq_country,
                    }
        except Exception as e:
            logger.warning(f"Could not fetch universe data for company {company_id}: {e}")

        # 2. Get VC announcement activity (competitive module)
        try:
            async with async_session_factory() as session:
                from src.competitive.database import VCAnnouncementModel
                
                company_name = profile.get("base_data", {}).get("name", "")
                if company_name:
                    stmt = select(VCAnnouncementModel).where(
                        VCAnnouncementModel.company_name.ilike(f"%{company_name}%")
                    ).order_by(VCAnnouncementModel.announced_date.desc()).limit(10)
                    
                    result = await session.execute(stmt)
                    announcements = result.scalars().all()
                    
                    for ann in announcements:
                        profile["vc_activity"].append({
                            "id": ann.id,
                            "round_type": ann.round_type,
                            "amount_gbp": ann.amount_gbp,
                            "announced_date": ann.announced_date.isoformat() if ann.announced_date else None,
                            "description": ann.description,
                            "source_url": ann.source_url,
                        })
        except Exception as e:
            logger.warning(f"Could not fetch VC activity for company {company_id}: {e}")

        # 3. Get PE investment history (capital module)
        try:
            async with async_session_factory() as session:
                from src.capital.database import PEInvestmentModel
                
                company_name = profile.get("base_data", {}).get("name", "")
                if company_name:
                    stmt = select(PEInvestmentModel).where(
                        PEInvestmentModel.company_name.ilike(f"%{company_name}%")
                    ).order_by(PEInvestmentModel.entry_date.desc()).limit(10)
                    
                    result = await session.execute(stmt)
                    investments = result.scalars().all()
                    
                    for inv in investments:
                        profile["pe_investments"].append({
                            "id": inv.id,
                            "entry_date": inv.entry_date.isoformat() if inv.entry_date else None,
                            "exit_date": inv.exit_date.isoformat() if inv.exit_date else None,
                            "is_exited": inv.is_exited,
                            "entry_valuation_usd": inv.entry_valuation_usd,
                            "sector": inv.sector,
                            "moat_type": inv.moat_type,
                        })
        except Exception as e:
            logger.warning(f"Could not fetch PE investments for company {company_id}: {e}")

        # 4. Get threat analysis (competitive module)
        try:
            async with async_session_factory() as session:
                from src.competitive.database import ThreatScoreModel, VCAnnouncementModel
                
                company_name = profile.get("base_data", {}).get("name", "")
                if company_name:
                    # Find announcements that match this company
                    ann_stmt = select(VCAnnouncementModel.id).where(
                        VCAnnouncementModel.company_name.ilike(f"%{company_name}%")
                    )
                    ann_result = await session.execute(ann_stmt)
                    announcement_ids = [row[0] for row in ann_result.all()]
                    
                    if announcement_ids:
                        threat_stmt = select(ThreatScoreModel).where(
                            ThreatScoreModel.announcement_id.in_(announcement_ids)
                        ).order_by(ThreatScoreModel.created_at.desc()).limit(1)
                        
                        threat_result = await session.execute(threat_stmt)
                        threat = threat_result.scalar_one_or_none()
                        
                        if threat:
                            profile["threat_analysis"] = {
                                "category": threat.category,
                                "threat_score": threat.threat_score,
                                "threat_level": threat.threat_level,
                                "reasoning": threat.reasoning,
                                "created_at": threat.created_at.isoformat() if threat.created_at else None,
                            }
        except Exception as e:
            logger.warning(f"Could not fetch threat analysis for company {company_id}: {e}")

        return profile

    async def detect_events(
        self, 
        company_id: int, 
        since: datetime
    ) -> List[CompanyEvent]:
        """
        Detect new events for a tracked company since a given date.
        
        Checks multiple data sources for changes:
        - New funding rounds (capital/competitive modules)
        - Leadership changes (competitive module)
        - News mentions (intel module)
        
        Args:
            company_id: The ID of the company in the universe database.
            since: Only detect events after this datetime.
            
        Returns:
            List of new CompanyEvent objects (not yet persisted).
        """
        events: List[CompanyEvent] = []
        
        # Get company name for searching
        company_name = await self._get_company_name(company_id)
        if not company_name:
            logger.warning(f"Could not find company name for ID {company_id}")
            return events

        # 1. Check for new funding rounds (VC announcements)
        try:
            async with async_session_factory() as session:
                from src.competitive.database import VCAnnouncementModel
                
                stmt = select(VCAnnouncementModel).where(
                    and_(
                        VCAnnouncementModel.company_name.ilike(f"%{company_name}%"),
                        VCAnnouncementModel.created_at > since
                    )
                )
                result = await session.execute(stmt)
                announcements = result.scalars().all()
                
                for ann in announcements:
                    event = CompanyEvent(
                        event_type=EventType.FUNDING.value,
                        event_date=ann.announced_date,
                        title=f"{ann.round_type or 'Funding'} round for {company_name}",
                        description=ann.description or f"Amount: £{ann.amount_gbp:,}" if ann.amount_gbp else ann.description,
                        source_url=ann.source_url,
                        severity=EventSeverity.HIGH.value,
                    )
                    events.append(event)
                    logger.info(f"Detected funding event for {company_name}: {event.title}")
        except Exception as e:
            logger.warning(f"Error checking VC announcements: {e}")

        # 2. Check for PE investments
        try:
            async with async_session_factory() as session:
                from src.capital.database import PEInvestmentModel
                
                stmt = select(PEInvestmentModel).where(
                    and_(
                        PEInvestmentModel.company_name.ilike(f"%{company_name}%"),
                        PEInvestmentModel.created_at > since
                    )
                )
                result = await session.execute(stmt)
                investments = result.scalars().all()
                
                for inv in investments:
                    event = CompanyEvent(
                        event_type=EventType.FUNDING.value,
                        event_date=inv.entry_date,
                        title=f"PE investment in {company_name}",
                        description=inv.description or f"Entry valuation: ${inv.entry_valuation_usd:,}" if inv.entry_valuation_usd else inv.description,
                        source_url=inv.source_url,
                        severity=EventSeverity.CRITICAL.value,
                    )
                    events.append(event)
                    logger.info(f"Detected PE investment for {company_name}: {event.title}")
        except Exception as e:
            logger.warning(f"Error checking PE investments: {e}")

        # 3. Check for news mentions (intel module)
        try:
            async with async_session_factory() as session:
                from src.market_intelligence.database import IntelligenceItem
                
                stmt = select(IntelligenceItem).where(
                    and_(
                        IntelligenceItem.title.ilike(f"%{company_name}%"),
                        IntelligenceItem.created_at > since
                    )
                ).limit(20)
                result = await session.execute(stmt)
                items = result.scalars().all()
                
                for item in items:
                    # Determine severity based on relevance score
                    if item.relevance_score and item.relevance_score >= 80:
                        severity = EventSeverity.HIGH.value
                    elif item.relevance_score and item.relevance_score >= 50:
                        severity = EventSeverity.MEDIUM.value
                    else:
                        severity = EventSeverity.LOW.value
                    
                    event = CompanyEvent(
                        event_type=EventType.NEWS.value,
                        event_date=item.published_date.date() if item.published_date else None,
                        title=item.title[:500],
                        description=item.summary or item.content[:500] if item.content else None,
                        source_url=item.url,
                        severity=severity,
                    )
                    events.append(event)
                    logger.info(f"Detected news event for {company_name}: {event.title[:50]}...")
        except Exception as e:
            logger.warning(f"Error checking intel items: {e}")

        return events

    async def _get_company_name(self, company_id: int) -> Optional[str]:
        """Get company name from universe database."""
        try:
            async with async_session_factory() as session:
                from src.universe.database import CompanyModel
                
                stmt = select(CompanyModel.name).where(CompanyModel.id == company_id)
                result = await session.execute(stmt)
                row = result.first()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting company name: {e}")
            return None

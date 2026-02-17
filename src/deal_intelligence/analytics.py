"""
Analytics Engine for Module 4 - Deal Intelligence.
Provides comparable analysis, market trends, and deal probability scoring.
"""
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.deal_intelligence.database import (
    DealRecord, DealComparable, MarketMetrics, DealProbability, DealType
)
from src.universe.database import CompanyModel
from src.capital.database import PEFirmModel, PEInvestmentModel

logger = logging.getLogger(__name__)


class ComparablesEngine:
    """
    Find and analyze comparable PE transactions for valuation analysis.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_comparables(
        self,
        target: DealRecord,
        limit: int = 10,
        revenue_tolerance: float = 0.30,  # +/- 30%
        max_age_years: int = 3
    ) -> List[DealComparable]:
        """
        Find comparable deals for a target transaction.
        
        Matching criteria:
        - Same or similar sector
        - Revenue within tolerance range
        - Same or similar geography
        - Within time window
        
        Returns ranked list of DealComparable objects.
        """
        comparables = []
        
        # Calculate revenue range
        target_revenue = target.revenue_gbp or 0
        min_revenue = int(target_revenue * (1 - revenue_tolerance))
        max_revenue = int(target_revenue * (1 + revenue_tolerance))
        
        # Calculate date cutoff
        cutoff_date = date.today() - relativedelta(years=max_age_years)
        
        # Build query for potential comparables
        stmt = select(DealRecord).where(
            and_(
                DealRecord.id != target.id,
                DealRecord.deal_date >= cutoff_date,
                DealRecord.ev_ebitda_multiple.isnot(None),  # Must have multiples
            )
        )
        
        # Add revenue filter if target has revenue
        if target_revenue > 0:
            stmt = stmt.where(
                and_(
                    DealRecord.revenue_gbp >= min_revenue,
                    DealRecord.revenue_gbp <= max_revenue
                )
            )
        
        # Prioritize same sector
        if target.sector:
            stmt = stmt.order_by(
                (DealRecord.sector == target.sector).desc(),
                DealRecord.deal_date.desc()
            )
        else:
            stmt = stmt.order_by(DealRecord.deal_date.desc())
        
        stmt = stmt.limit(limit * 3)  # Get more candidates for scoring
        
        result = await self.session.execute(stmt)
        candidates = result.scalars().all()
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            similarity = self._calculate_similarity(target, candidate)
            scored_candidates.append((candidate, similarity))
        
        # Sort by similarity score
        scored_candidates.sort(key=lambda x: x[1]['total'], reverse=True)
        
        # Create DealComparable records for top matches
        for candidate, similarity in scored_candidates[:limit]:
            comparable = DealComparable(
                deal_record_id=target.id,
                comparable_deal_id=candidate.id,
                similarity_score=int(similarity['total']),
                similarity_reasons={
                    'sector_match': similarity['sector'] > 0.8,
                    'size_match': similarity['size'],
                    'geography_match': similarity['geography'] > 0.8,
                    'time_proximity': similarity['time']
                },
                sector_similarity=similarity['sector'],
                size_similarity=similarity['size'],
                geography_similarity=similarity['geography'],
                time_similarity=similarity['time']
            )
            comparables.append(comparable)
        
        return comparables
    
    def _calculate_similarity(
        self, 
        target: DealRecord, 
        candidate: DealRecord
    ) -> Dict[str, float]:
        """
        Calculate similarity score between two deals.
        Returns dict with component scores and total.
        """
        scores = {
            'sector': 0.0,
            'size': 0.0,
            'geography': 0.0,
            'time': 0.0,
            'total': 0.0
        }
        
        # Sector similarity (40% weight)
        if target.sector and candidate.sector:
            if target.sector.lower() == candidate.sector.lower():
                scores['sector'] = 1.0
            elif target.subsector and candidate.subsector:
                if target.subsector.lower() == candidate.subsector.lower():
                    scores['sector'] = 0.9
                else:
                    scores['sector'] = 0.5  # Same broad sector assumed
            else:
                scores['sector'] = 0.5
        
        # Size similarity (30% weight)
        if target.revenue_gbp and candidate.revenue_gbp:
            ratio = min(target.revenue_gbp, candidate.revenue_gbp) / max(target.revenue_gbp, candidate.revenue_gbp)
            scores['size'] = ratio
        elif target.enterprise_value_gbp and candidate.enterprise_value_gbp:
            ratio = min(target.enterprise_value_gbp, candidate.enterprise_value_gbp) / max(target.enterprise_value_gbp, candidate.enterprise_value_gbp)
            scores['size'] = ratio
        
        # Geography similarity (15% weight)
        if target.geography and candidate.geography:
            if target.geography.lower() == candidate.geography.lower():
                scores['geography'] = 1.0
            elif target.region and candidate.region:
                if target.region.lower() == candidate.region.lower():
                    scores['geography'] = 0.7
                else:
                    scores['geography'] = 0.3
            else:
                scores['geography'] = 0.5
        
        # Time proximity (15% weight) - more recent = higher score
        if target.deal_date and candidate.deal_date:
            days_diff = abs((target.deal_date - candidate.deal_date).days)
            if days_diff <= 180:  # 6 months
                scores['time'] = 1.0
            elif days_diff <= 365:  # 1 year
                scores['time'] = 0.8
            elif days_diff <= 730:  # 2 years
                scores['time'] = 0.6
            else:
                scores['time'] = 0.4
        
        # Calculate weighted total
        scores['total'] = (
            scores['sector'] * 40 +
            scores['size'] * 30 +
            scores['geography'] * 15 +
            scores['time'] * 15
        )
        
        return scores
    
    async def calculate_valuation_range(
        self,
        company_id: int = None,
        revenue_gbp: int = None,
        ebitda_gbp: int = None,
        sector: str = None,
        geography: str = "UK"
    ) -> Dict[str, Any]:
        """
        Calculate valuation range for a company based on comparable transactions.
        
        Can use either:
        - company_id to fetch financials from CompanyModel
        - Direct revenue/ebitda inputs
        
        Returns:
        {
            'low': int, 'median': int, 'high': int,
            'multiples': {'ev_revenue': {low, median, high}, 'ev_ebitda': {...}},
            'comparable_count': int,
            'comparables': [...]
        }
        """
        # Get company data if ID provided
        if company_id:
            stmt = select(CompanyModel).where(CompanyModel.id == company_id)
            result = await self.session.execute(stmt)
            company = result.scalar_one_or_none()
            
            if company:
                revenue_gbp = revenue_gbp or company.revenue_gbp
                ebitda_gbp = ebitda_gbp or company.ebitda_gbp
                sector = sector or company.sector
        
        if not revenue_gbp and not ebitda_gbp:
            return {
                'low': 0, 'median': 0, 'high': 0,
                'multiples': {},
                'comparable_count': 0,
                'error': 'No financial data available'
            }
        
        # Find comparable deals
        # Create a temporary target for matching
        temp_target = DealRecord(
            target_company_name="Valuation Target",
            revenue_gbp=revenue_gbp,
            ebitda_gbp=ebitda_gbp,
            sector=sector,
            geography=geography,
            deal_date=date.today()
        )
        
        # Query deals with similar characteristics
        cutoff_date = date.today() - relativedelta(years=3)
        
        stmt = select(DealRecord).where(
            and_(
                DealRecord.deal_date >= cutoff_date,
                or_(
                    DealRecord.ev_revenue_multiple.isnot(None),
                    DealRecord.ev_ebitda_multiple.isnot(None)
                )
            )
        )
        
        if sector:
            stmt = stmt.where(DealRecord.sector == sector)
        
        if revenue_gbp:
            min_rev = int(revenue_gbp * 0.5)
            max_rev = int(revenue_gbp * 2.0)
            stmt = stmt.where(
                DealRecord.revenue_gbp.between(min_rev, max_rev)
            )
        
        stmt = stmt.order_by(DealRecord.deal_date.desc()).limit(20)
        
        result = await self.session.execute(stmt)
        comparables = result.scalars().all()
        
        if not comparables:
            # Fallback to sector-wide metrics
            return await self._get_sector_valuation(sector, revenue_gbp, ebitda_gbp)
        
        # Extract multiples
        ev_revenue_multiples = [d.ev_revenue_multiple for d in comparables if d.ev_revenue_multiple]
        ev_ebitda_multiples = [d.ev_ebitda_multiple for d in comparables if d.ev_ebitda_multiple]
        
        # Calculate ranges
        valuations = []
        
        if ev_revenue_multiples and revenue_gbp:
            ev_revenue_multiples.sort()
            low_mult = ev_revenue_multiples[0]
            high_mult = ev_revenue_multiples[-1]
            median_mult = ev_revenue_multiples[len(ev_revenue_multiples) // 2]
            
            valuations.append({
                'method': 'ev_revenue',
                'low': int(revenue_gbp * low_mult),
                'median': int(revenue_gbp * median_mult),
                'high': int(revenue_gbp * high_mult),
                'multiples': {'low': low_mult, 'median': median_mult, 'high': high_mult}
            })
        
        if ev_ebitda_multiples and ebitda_gbp:
            ev_ebitda_multiples.sort()
            low_mult = ev_ebitda_multiples[0]
            high_mult = ev_ebitda_multiples[-1]
            median_mult = ev_ebitda_multiples[len(ev_ebitda_multiples) // 2]
            
            valuations.append({
                'method': 'ev_ebitda',
                'low': int(ebitda_gbp * low_mult),
                'median': int(ebitda_gbp * median_mult),
                'high': int(ebitda_gbp * high_mult),
                'multiples': {'low': low_mult, 'median': median_mult, 'high': high_mult}
            })
        
        # Calculate blended range
        if valuations:
            all_lows = [v['low'] for v in valuations]
            all_medians = [v['median'] for v in valuations]
            all_highs = [v['high'] for v in valuations]
            
            return {
                'low': min(all_lows),
                'median': sum(all_medians) // len(all_medians),
                'high': max(all_highs),
                'methods': valuations,
                'comparable_count': len(comparables),
                'comparables': [
                    {
                        'name': c.target_company_name,
                        'date': c.deal_date.isoformat() if c.deal_date else None,
                        'ev_revenue': c.ev_revenue_multiple,
                        'ev_ebitda': c.ev_ebitda_multiple
                    }
                    for c in comparables[:5]
                ]
            }
        
        return {
            'low': 0, 'median': 0, 'high': 0,
            'comparable_count': 0,
            'error': 'No valuation multiples available'
        }
    
    async def _get_sector_valuation(
        self,
        sector: str,
        revenue_gbp: int,
        ebitda_gbp: int
    ) -> Dict[str, Any]:
        """Fallback valuation using sector-wide metrics."""
        # Get latest market metrics for sector
        stmt = select(MarketMetrics).where(
            MarketMetrics.sector == sector
        ).order_by(MarketMetrics.time_period.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        metrics = result.scalar_one_or_none()
        
        if not metrics:
            return {
                'low': 0, 'median': 0, 'high': 0,
                'comparable_count': 0,
                'error': f'No market metrics available for sector: {sector}'
            }
        
        valuations = []
        
        if metrics.median_ev_revenue and revenue_gbp:
            valuations.append(int(revenue_gbp * metrics.median_ev_revenue))
        
        if metrics.median_ev_ebitda and ebitda_gbp:
            valuations.append(int(ebitda_gbp * metrics.median_ev_ebitda))
        
        if valuations:
            median_val = sum(valuations) // len(valuations)
            return {
                'low': int(median_val * 0.7),
                'median': median_val,
                'high': int(median_val * 1.3),
                'source': 'sector_metrics',
                'comparable_count': metrics.deal_count or 0
            }
        
        return {'low': 0, 'median': 0, 'high': 0, 'comparable_count': 0}


class MarketTrendsAnalyzer:
    """
    Analyze market trends, sector activity, and pricing trends.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def calculate_sector_metrics(
        self,
        sector: str,
        time_range: Tuple[date, date] = None
    ) -> List[MarketMetrics]:
        """
        Calculate aggregated metrics for a sector over time.
        
        Returns list of MarketMetrics by month.
        """
        if not time_range:
            end_date = date.today()
            start_date = end_date - relativedelta(years=2)
            time_range = (start_date, end_date)
        
        start_date, end_date = time_range
        
        # Query deals in range
        stmt = select(DealRecord).where(
            and_(
                DealRecord.sector == sector,
                DealRecord.deal_date >= start_date,
                DealRecord.deal_date <= end_date
            )
        ).order_by(DealRecord.deal_date)
        
        result = await self.session.execute(stmt)
        deals = result.scalars().all()
        
        # Group by month
        monthly_data = {}
        for deal in deals:
            if not deal.deal_date:
                continue
            
            period = deal.deal_date.strftime('%Y-%m')
            
            if period not in monthly_data:
                monthly_data[period] = {
                    'deals': [],
                    'ev_revenue': [],
                    'ev_ebitda': [],
                    'total_value': 0
                }
            
            monthly_data[period]['deals'].append(deal)
            
            if deal.ev_revenue_multiple:
                monthly_data[period]['ev_revenue'].append(deal.ev_revenue_multiple)
            if deal.ev_ebitda_multiple:
                monthly_data[period]['ev_ebitda'].append(deal.ev_ebitda_multiple)
            if deal.enterprise_value_gbp:
                monthly_data[period]['total_value'] += deal.enterprise_value_gbp
        
        # Create metrics
        metrics = []
        prev_deal_count = None
        
        for period in sorted(monthly_data.keys()):
            data = monthly_data[period]
            deal_count = len(data['deals'])
            
            metric = MarketMetrics(
                sector=sector,
                geography="Europe",
                time_period=period,
                deal_count=deal_count,
                total_value_gbp=data['total_value'],
                average_deal_size_gbp=data['total_value'] // deal_count if deal_count > 0 else 0,
                median_ev_revenue=self._median(data['ev_revenue']),
                median_ev_ebitda=self._median(data['ev_ebitda']),
                avg_ev_revenue=sum(data['ev_revenue']) / len(data['ev_revenue']) if data['ev_revenue'] else None,
                avg_ev_ebitda=sum(data['ev_ebitda']) / len(data['ev_ebitda']) if data['ev_ebitda'] else None
            )
            
            # Calculate change from previous period
            if prev_deal_count is not None:
                if prev_deal_count > 0:
                    metric.deal_count_change_pct = ((deal_count - prev_deal_count) / prev_deal_count) * 100
            
            prev_deal_count = deal_count
            metrics.append(metric)
        
        return metrics
    
    def _median(self, values: List[float]) -> Optional[float]:
        """Calculate median of a list."""
        if not values:
            return None
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        return sorted_values[n//2]
    
    async def detect_hot_sectors(
        self,
        months_lookback: int = 6,
        min_deal_count: int = 3,
        growth_threshold: float = 20.0  # 20% growth
    ) -> List[Dict[str, Any]]:
        """
        Identify sectors with increasing deal activity and/or rising multiples.
        
        Returns ranked list of hot sectors with metrics.
        """
        cutoff_date = date.today() - relativedelta(months=months_lookback)
        prev_cutoff = cutoff_date - relativedelta(months=months_lookback)
        
        # Get current period metrics
        current_stmt = select(
            DealRecord.sector,
            func.count(DealRecord.id).label('deal_count'),
            func.sum(DealRecord.enterprise_value_gbp).label('total_value'),
            func.avg(DealRecord.ev_ebitda_multiple).label('avg_multiple')
        ).where(
            and_(
                DealRecord.deal_date >= cutoff_date,
                DealRecord.sector.isnot(None)
            )
        ).group_by(DealRecord.sector)
        
        current_result = await self.session.execute(current_stmt)
        current_data = {row.sector: row for row in current_result.all()}
        
        # Get previous period metrics
        prev_stmt = select(
            DealRecord.sector,
            func.count(DealRecord.id).label('deal_count'),
            func.sum(DealRecord.enterprise_value_gbp).label('total_value'),
            func.avg(DealRecord.ev_ebitda_multiple).label('avg_multiple')
        ).where(
            and_(
                DealRecord.deal_date >= prev_cutoff,
                DealRecord.deal_date < cutoff_date,
                DealRecord.sector.isnot(None)
            )
        ).group_by(DealRecord.sector)
        
        prev_result = await self.session.execute(prev_stmt)
        prev_data = {row.sector: row for row in prev_result.all()}
        
        # Calculate hot sectors
        hot_sectors = []
        
        for sector, current in current_data.items():
            if current.deal_count < min_deal_count:
                continue
            
            prev = prev_data.get(sector)
            
            deal_growth = 0
            multiple_change = 0
            
            if prev and prev.deal_count > 0:
                deal_growth = ((current.deal_count - prev.deal_count) / prev.deal_count) * 100
            
            if prev and prev.avg_multiple and current.avg_multiple:
                multiple_change = ((current.avg_multiple - prev.avg_multiple) / prev.avg_multiple) * 100
            
            # Calculate heat score
            heat_score = (
                min(deal_growth, 100) * 0.5 +  # Cap at 100%
                min(multiple_change, 50) * 0.3 +  # Cap at 50%
                min(current.deal_count, 20) * 2  # Deal volume bonus
            )
            
            is_hot = deal_growth >= growth_threshold or heat_score >= 50
            
            hot_sectors.append({
                'sector': sector,
                'deal_count': current.deal_count,
                'total_value_gbp': current.total_value or 0,
                'avg_multiple': round(current.avg_multiple, 1) if current.avg_multiple else None,
                'deal_growth_pct': round(deal_growth, 1),
                'multiple_change_pct': round(multiple_change, 1),
                'heat_score': round(heat_score, 1),
                'is_hot': is_hot,
                'prev_deal_count': prev.deal_count if prev else 0
            })
        
        # Sort by heat score
        hot_sectors.sort(key=lambda x: x['heat_score'], reverse=True)
        
        return hot_sectors


class DealProbabilityScorer:
    """
    Score likelihood of a company becoming a PE transaction target.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def score_deal_likelihood(
        self,
        company_id: int
    ) -> Optional[DealProbability]:
        """
        Calculate deal probability for a company based on multiple signals.
        
        Signals evaluated:
        - Recent leadership/management changes
        - Declining revenue growth
        - Parent company carveout signals
        - PE firm sector interest (from capital flows)
        - Time since last transaction
        - Seller distress indicators
        - Advisor engagement
        
        Returns DealProbability with detailed breakdown.
        """
        # Get company data
        stmt = select(CompanyModel).where(CompanyModel.id == company_id)
        result = await self.session.execute(stmt)
        company = result.scalar_one_or_none()
        
        if not company:
            logger.warning(f"Company not found: {company_id}")
            return None
        
        # Initialize signals tracking
        signals = {
            'seller_distress': {'active': False, 'score': 0, 'evidence': ''},
            'advisor_engaged': {'active': False, 'score': 0, 'evidence': ''},
            'management_changes': {'active': False, 'score': 0, 'evidence': ''},
            'declining_growth': {'active': False, 'score': 0, 'evidence': ''},
            'pe_sector_interest': {'active': False, 'score': 0, 'evidence': ''},
            'carveout_potential': {'active': False, 'score': 0, 'evidence': ''},
            'time_since_deal': {'years': None, 'score': 0}
        }
        
        total_score = 0
        reasoning_parts = []
        
        # 1. Check declining growth
        if company.revenue_growth is not None:
            growth_pct = float(company.revenue_growth)
            if growth_pct < 0:
                signals['declining_growth']['active'] = True
                signals['declining_growth']['score'] = min(abs(growth_pct) * 2, 20)
                signals['declining_growth']['evidence'] = f"Revenue declining at {growth_pct}%"
                total_score += signals['declining_growth']['score']
                reasoning_parts.append(f"Declining revenue growth ({growth_pct}%)")
            elif growth_pct < 5:
                signals['declining_growth']['active'] = True
                signals['declining_growth']['score'] = 10
                signals['declining_growth']['evidence'] = f"Low growth at {growth_pct}%"
                total_score += 10
                reasoning_parts.append(f"Low revenue growth ({growth_pct}%)")
        
        # 2. Check PE sector interest
        pe_interest = await self._check_pe_sector_interest(company.sector)
        if pe_interest['active']:
            signals['pe_sector_interest'] = pe_interest
            total_score += pe_interest['score']
            reasoning_parts.append(pe_interest['evidence'])
        
        # 3. Check time since last deal in sector
        last_deal_score = await self._check_sector_deal_activity(company.sector)
        if last_deal_score > 0:
            signals['time_since_deal']['score'] = last_deal_score
            total_score += last_deal_score
            reasoning_parts.append("Sector has recent PE activity")
        
        # 4. Size fit for PE (£15-100M revenue sweet spot)
        if company.revenue_gbp:
            rev_m = company.revenue_gbp / 1_000_000
            if 15 <= rev_m <= 100:
                size_score = 15
                total_score += size_score
                reasoning_parts.append(f"Revenue £{rev_m:.0f}M in PE sweet spot")
            elif 10 <= rev_m < 15 or 100 < rev_m <= 200:
                size_score = 8
                total_score += size_score
                reasoning_parts.append(f"Revenue £{rev_m:.0f}M within expandable range")
        
        # 5. Strong moat makes attractive target
        if company.moat_score and company.moat_score >= 70:
            moat_score = 15
            total_score += moat_score
            reasoning_parts.append(f"Strong moat score ({company.moat_score})")
        elif company.moat_score and company.moat_score >= 50:
            moat_score = 8
            total_score += moat_score
            reasoning_parts.append(f"Moderate moat score ({company.moat_score})")
        
        # Cap at 100
        total_score = min(total_score, 100)
        
        # Determine tier
        if total_score >= 70:
            tier = "high"
        elif total_score >= 40:
            tier = "medium"
        else:
            tier = "low"
        
        # Build reasoning
        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "No significant deal signals identified."
        
        # Create probability record
        probability = DealProbability(
            target_company_id=company_id,
            target_company_name=company.name,
            probability_score=total_score,
            probability_tier=tier,
            reasoning=reasoning,
            signals=signals,
            signal_declining_growth=signals['declining_growth']['active'],
            signal_pe_sector_interest=signals['pe_sector_interest']['active'],
            signal_seller_distress=signals['seller_distress']['active'],
            signal_advisor_engaged=signals['advisor_engaged']['active'],
            signal_management_changes=signals['management_changes']['active'],
            signal_carveout_potential=signals['carveout_potential']['active'],
            expected_timeline=self._estimate_timeline(total_score)
        )
        
        return probability
    
    async def _check_pe_sector_interest(self, sector: str) -> Dict[str, Any]:
        """Check if PE firms are actively investing in this sector."""
        if not sector:
            return {'active': False, 'score': 0, 'evidence': ''}
        
        # Count recent investments in sector
        cutoff = date.today() - relativedelta(years=2)
        
        stmt = select(func.count(PEInvestmentModel.id)).where(
            and_(
                PEInvestmentModel.sector == sector,
                PEInvestmentModel.entry_date >= cutoff
            )
        )
        
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        
        if count >= 5:
            return {
                'active': True,
                'score': 20,
                'evidence': f"High PE interest in {sector} ({count} deals in 2 years)"
            }
        elif count >= 2:
            return {
                'active': True,
                'score': 10,
                'evidence': f"Moderate PE interest in {sector} ({count} deals)"
            }
        
        return {'active': False, 'score': 0, 'evidence': ''}
    
    async def _check_sector_deal_activity(self, sector: str) -> int:
        """Check recent deal activity in sector."""
        if not sector:
            return 0
        
        cutoff = date.today() - relativedelta(months=12)
        
        stmt = select(func.count(DealRecord.id)).where(
            and_(
                DealRecord.sector == sector,
                DealRecord.deal_date >= cutoff
            )
        )
        
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        
        if count >= 3:
            return 10
        elif count >= 1:
            return 5
        return 0
    
    def _estimate_timeline(self, score: int) -> str:
        """Estimate deal timeline based on probability score."""
        if score >= 70:
            return "6-12 months"
        elif score >= 50:
            return "12-24 months"
        elif score >= 30:
            return "2+ years"
        return "Unlikely near-term"

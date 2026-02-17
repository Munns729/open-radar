"""
Exit Matcher Engine.
Matches portfolio companies to potential buyers.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.capital.database import StrategicAcquirerModel, ConsolidatorModel, PEFirmModel
from src.core.data_types import Company

@dataclass
class ExitCandidate:
    buyer_name: str
    buyer_type: str # 'strategic', 'consolidator', 'pe'
    match_score: int # 0-100
    rationale: str
    typical_multiple: Optional[float] = None

class ExitMatcher:
    """
    Ranks potential buyers for a given company.
    """
    
    def __init__(self, session: Session):
        self.session = session

    def find_exit_candidates(self, company: Company) -> List[ExitCandidate]:
        candidates = []
        
        # 1. Check Strategics
        strategics = self.session.query(StrategicAcquirerModel).filter(
            or_(
                StrategicAcquirerModel.category.ilike(f"%{company.sector}%"),
                StrategicAcquirerModel.name.ilike(f"%{company.sector}%") # Simple proxy
            )
        ).all()
        
        for strat in strategics:
            score = 0
            # Sector fit
            score += 40 
            
            # Size fit (Acquirers usually buy <10% of their market cap, or specifically budget)
            if strat.acquisition_budget_annual_usd and company.revenue_gbp:
                rev_usd = company.revenue_gbp * 1.25 # approx check
                if rev_usd < strat.acquisition_budget_annual_usd:
                    score += 20
            
            # Moat preference
            if company.moat_type == "regulatory" and strat.values_regulatory_moats:
                score += 20
            
            # Activity
            if strat.acquisitions_last_24mo > 0:
                score += 20
                
            if score > 50:
                candidates.append(ExitCandidate(
                    buyer_name=strat.name,
                    buyer_type="strategic",
                    match_score=score,
                    rationale=f"Sector match in {strat.category}, Active buyer.",
                    typical_multiple=float(strat.typical_multiple_paid) if strat.typical_multiple_paid else None
                ))

        # 2. Check Consolidators
        consolidators = self.session.query(ConsolidatorModel).filter(
            ConsolidatorModel.sector_focus.ilike(f"%{company.sector}%")
        ).all()
        
        for consol in consolidators:
            score = 0
            score += 30 # Sector baseline
            
            # Size range
            rev_usd = (company.revenue_gbp or 0) * 1.25
            if consol.typical_target_size_min_usd and rev_usd >= consol.typical_target_size_min_usd:
                 if consol.typical_target_size_max_usd and rev_usd <= consol.typical_target_size_max_usd:
                     score += 40
            
            candidates.append(ExitCandidate(
                buyer_name=consol.name,
                buyer_type="consolidator",
                match_score=score + 10, # Bonus for rollups?
                rationale="Roll-up strategy fit.",
                typical_multiple=None 
            ))
            
        return sorted(candidates, key=lambda x: x.match_score, reverse=True)

"""
Operational Autonomy Scorer for Carveout Candidates.
Scores the execution risk and strategic rationale of a separation.
"""
from typing import Dict, Any, Optional

class OperationalAutonomyScorer:
    """
    Scores separation complexity (Operational) and willingness to sell (Strategic).
    Returns a combined modifier score (0-30) to be added to the base Moat Score.
    """
    
    # Operational Autonomy (0-15 pts)
    OPERATIONAL_SCORES = {
        "standalone": 15,       # Easy separation
        "semi_autonomous": 10,  # Moderate complexity
        "integrated": 5         # High complexity / entanglement
    }
    
    # Strategic Autonomy (0-15 pts)
    STRATEGIC_SCORES = {
        "non_core": 15,     # Clear sell
        "peripheral": 10,   # Likely sell
        "core": 3           # Unlikely sell
    }

    @classmethod
    def score(cls, division: Any) -> int:
        """
        Calculate the autonomy modifier score (0-30).
        Expects a Division-like object with 'autonomy_level' and 'strategic_autonomy' attributes.
        """
        score = 0
        
        # 1. Operational Autonomy
        autonomy = getattr(division, 'autonomy_level', None)
        if autonomy in cls.OPERATIONAL_SCORES:
            score += cls.OPERATIONAL_SCORES[autonomy]
        
        # 2. Strategic Autonomy
        strategic = getattr(division, 'strategic_autonomy', None)
        if strategic in cls.STRATEGIC_SCORES:
            score += cls.STRATEGIC_SCORES[strategic]
            
        return score

    @classmethod
    def get_breakdown(cls, division: Any) -> Dict[str, Any]:
        """Return detailed score breakdown."""
        op_score = 0
        strat_score = 0
        
        autonomy = getattr(division, 'autonomy_level', None)
        if autonomy in cls.OPERATIONAL_SCORES:
            op_score = cls.OPERATIONAL_SCORES[autonomy]
            
        strategic = getattr(division, 'strategic_autonomy', None)
        if strategic in cls.STRATEGIC_SCORES:
            strat_score = cls.STRATEGIC_SCORES[strategic]
            
        return {
            "operational_score": op_score,
            "strategic_score": strat_score,
            "total_modifier": op_score + strat_score,
            "operational_status": autonomy,
            "strategic_status": strategic
        }

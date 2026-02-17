"""
Attractiveness Scorer.
Scores divisions based on strategic fit for the active investment thesis.
A thin wrapper composing Moat Score (Company Quality) + Autonomy Modifier (Carveout execution).
"""
from typing import Optional, Any
from src.universe.moat_scorer import MoatScorer
from src.carveout.operational_scorer import OperationalAutonomyScorer
from src.carveout.database import Division

class AttractivenessScorer:
    """
    Scores carveout opportunities against the active thesis.
    Final Score = Base Company Quality (MoatScorer) + Carveout Execution Modifier (OperationalAutonomyScorer)
    """

    async def score(self, division: Division) -> int:
        """
        Calculate score 0-100 based on size, financial, and strategic fit.
        """
        # 1. Base Score: Principles of a good company (Moat, Financials, Competitive)
        base_score = 0
        
        # Try to get score from parent company first (Primary Path)
        if division.parent and hasattr(division.parent, "moat_score") and division.parent.moat_score:
             base_score = division.parent.moat_score
        else:
            # Fallback for orphan divisions or unscored parents: Run the async scorer on the division itself
            # We treat the division as a company-like object (Duck Typing).
            # MoatScorer expects: revenue_gbp, ebitda_margin, market_share, etc. which are now on Division.
            # We pass empty certs/graph signals as we likely don't have them for a raw division.
            base_score = await MoatScorer.score_with_llm(division, certifications=[], graph_signals={}, raw_website_text="")

        # 2. Autonomy Modifier: Execution risk and strategic rationale
        modifier = OperationalAutonomyScorer.score(division)
        
        # 3. Combine
        total_score = base_score + modifier
        
        # Update scalar on the division object
        division.attractiveness_score = min(100, int(total_score))
        
        return division.attractiveness_score

    def classify_tier(self, score: int) -> str:
        if score >= 80: return "1A"
        if score >= 60: return "1B"
        return "2"

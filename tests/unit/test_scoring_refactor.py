import pytest
from decimal import Decimal
from src.universe.moat_scorer import MoatScorer
from src.carveout.operational_scorer import OperationalAutonomyScorer
from src.carveout.attractiveness_scorer import AttractivenessScorer
from src.universe.database import CompanyModel
from src.carveout.database import Division, CorporateParent

class TestScoringRefactor:
    
    def test_moat_scorer_financials(self):
        """Verify MoatScorer correctly scores financial quality."""
        # Case 1: Perfect financials
        company = CompanyModel()
        company.name = "Perfect Co"
        company.revenue_gbp = 50_000_000 # Sweet spot (£10-150M) -> +25
        company.ebitda_margin = Decimal("25.0") # >20% -> +25
        
        score = MoatScorer.score_picard_defensibility(company, [], {})
        
        # Base financial score should be 50
        # NOTE: score_picard_defensibility might have other small implicit points (like employee count fallback if revenue missing, but here revenue is present)
        # Let's check logic. 
        # Financial: 25 (Rev) + 25 (Margin) = 50.
        # Competitive: 0
        # Certs/Network: 0
        assert score == 50, f"Expected 50, got {score}"

    def test_moat_scorer_competitive(self):
        """Verify MoatScorer scores competitive position."""
        company = CompanyModel()
        company.name = "Niche Leader"
        company.market_share = Decimal("25.0") # >20% -> +10
        company.competitor_count = 3 # <5 -> +5
        company.market_growth_rate = Decimal("6.0") # >5% -> +5
        
        score = MoatScorer.score_picard_defensibility(company, [], {})
        
        # Competitive: 10 + 5 + 5 = 20
        assert score == 20, f"Expected 20, got {score}"

    def test_operational_autonomy_scorer(self):
        """Verify autonomy scoring."""
        div = Division()
        div.autonomy_level = "standalone" # +15
        div.strategic_autonomy = "non_core" # +15
        
        score = OperationalAutonomyScorer.score(div)
        assert score == 30
        
        div.autonomy_level = "integrated" # +5
        div.strategic_autonomy = "core" # +3
        score = OperationalAutonomyScorer.score(div)
        assert score == 8

    def test_attractiveness_scorer_composition(self):
        """Verify composition of moat score and autonomy."""
        scorer = AttractivenessScorer()
        
        # Setup: Parent Company with Moat Score
        parent = CorporateParent()
        parent.moat_score = 60 # e.g. Tier 1B
        
        div = Division()
        div.parent = parent
        div.autonomy_level = "semi_autonomous" # +10
        div.strategic_autonomy = "peripheral" # +10
        
        score = scorer.score_for_picard(div)
        
        # Total = 60 (Base) + 20 (Modifier) = 80
        assert score == 80
        assert div.picard_attractiveness_score == 80
        
    def test_attractiveness_scorer_orphan_fallback(self):
        """Verify fallback scoring for orphan division."""
        scorer = AttractivenessScorer()
        
        # Orphan division (no parent) checking MoatScorer fallback
        div = Division()
        div.parent = None
        
        # Set attributes for MoatScorer fallback
        div.revenue_gbp = 20_000_000 # +25 (Financial)
        div.ebitda_margin = Decimal("22.0") # +25 (Financial)
        div.market_share = Decimal("5.0") # 0
        
        # Set attributes for Autonomy Modifier
        div.autonomy_level = "standalone" # +15
        div.strategic_autonomy = "non_core" # +15
        
        score = scorer.score_for_picard(div)
        
        # Base (MoatScorer) = 50
        # Modifier = 30
        # Total = 80
        assert score == 80

"""
Unit tests for the Carveout Attractiveness Scorer.
Covers revenue sizing, moat strength, margin, and autonomy level logic.
"""
import pytest
from src.carveout.attractiveness_scorer import AttractivenessScorer
from src.carveout.database import Division

class TestAttractivenessScorer:
    """Test suite for AttractivenessScorer algorithm."""

    def setup_method(self):
        self.scorer = AttractivenessScorer()

    def test_revenue_sizing(self):
        """Test scoring based on revenue 'sweet spot'."""
        # Sweet Spot (15M - 120M)
        div = Division(revenue_eur=50_000_000)
        score = self.scorer.score_for_picard(div)
        # 25 (Sweet spot) + 0 (No Comp Data) + 5 (Default Margin < 10) = 30
        assert score == 30

        # Upper End (120M - 180M)
        div = Division(revenue_eur=150_000_000)
        score = self.scorer.score_for_picard(div)
        # 20 (Upper) + 0 + 5 = 25
        assert score == 25

        # Lower End (10M - 15M)
        div = Division(revenue_eur=12_000_000)
        score = self.scorer.score_for_picard(div)
        # 15 (Lower) + 0 + 5 = 20
        assert score == 20

        # Out of Scope (<10M)
        div = Division(revenue_eur=5_000_000)
        score = self.scorer.score_for_picard(div)
        assert score == 0  # Returns early 0

        # Out of Scope (>180M)
        div = Division(revenue_eur=200_000_000)
        score = self.scorer.score_for_picard(div)
        assert score == 0

    def test_moat_strength(self):
        """Test scoring based on moat type and strength."""
        # Regulatory Moat (High Strength)
        div = Division(
            revenue_eur=50_000_000, 
            moat_type="regulatory", 
            moat_strength=80
        )
        score = self.scorer.score_for_picard(div)
        # 25 (Rev) + 30 (Reg Moat > 70) + 0 (Comp) + 5 (Low Margin) = 60
        assert score == 60

        # Regulatory Moat (Medium Strength)
        div = Division(
            revenue_eur=50_000_000, 
            moat_type="regulatory", 
            moat_strength=55
        )
        score = self.scorer.score_for_picard(div)
        # 25 + 20 (Reg Moat > 50) + 0 (Comp) + 5 (Low Margin) = 50
        assert score == 50

        # Network Effects (High Strength)
        div = Division(
            revenue_eur=50_000_000, 
            moat_type="network_effects", 
            moat_strength=65
        )
        score = self.scorer.score_for_picard(div)
        # 25 + 20 (Network > 60) + 0 + 5 = 50
        assert score == 50

    def test_financials_margin(self):
        """Test scoring based on EBITDA margin."""
        # High Margin (>20%)
        div = Division(revenue_eur=50_000_000, ebitda_margin=25)
        score = self.scorer.score_for_picard(div)
        # 25 (Rev) + 20 (Margin) + 0 (Comp) = 45
        # Note: No low margin +5 here because margin is 25.
        assert score == 45

        # Low Margin (<10%)
        div = Division(revenue_eur=50_000_000, ebitda_margin=5)
        score = self.scorer.score_for_picard(div)
        # 25 + 5 (Margin) + 0 (Comp) = 30
        assert score == 30

    def test_complexity_autonomy(self):
        """Test scoring based on structural autonomy."""
        # Standalone
        div = Division(revenue_eur=50_000_000, autonomy_level="standalone")
        score = self.scorer.score_for_picard(div)
        # 25 (Rev) + 15 (Standalone) + 0 (Comp) + 5 (Low Margin) = 45
        assert score == 45

        # Integrated
        div = Division(revenue_eur=50_000_000, autonomy_level="integrated")
        score = self.scorer.score_for_picard(div)
        # 25 + 5 (Integrated) + 0 (Comp) + 5 (Low Margin) = 35
        assert score == 35

    def test_competitive_dynamics(self):
        """Test scoring based on competitive landscape."""
        # Strong Position (High Share, Few Competitors, High Growth)
        div = Division(
            revenue_eur=50_000_000,
            market_share=25.0,      # +10
            competitor_count=3,     # +5
            market_growth_rate=6.0  # +5
        )
        score = self.scorer.score_for_picard(div)
        # Base: 25 (Rev) + 5 (Low Margin) = 30
        # Comp: 10 + 5 + 5 = 20
        # Total: 50
        assert score == 50

        # Weak Position
        div = Division(
            revenue_eur=50_000_000,
            market_share=5.0,       # +0
            competitor_count=10,    # +0
            market_growth_rate=2.0  # +0
        )
        score = self.scorer.score_for_picard(div)
        # Base: 30
        # Comp: 0
        # Total: 30
        assert score == 30

    def test_tier_classification(self):
        """Test tier classification based on score."""
        assert self.scorer.classify_tier(85) == "1A"
        assert self.scorer.classify_tier(65) == "1B"
        assert self.scorer.classify_tier(40) == "2"

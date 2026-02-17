"""
Unit tests for the Competitive Threat Scorer.
Covers VC tier logic, round sizing, sector matching, and threat levels.
"""
import pytest
from datetime import datetime
from src.competitive.threat_scorer import ThreatScorer
from src.core.models import ThreatLevel

class TestThreatScorer:
    """Test suite for ThreatScorer algorithm."""

    def setup_method(self):
        self.scorer = ThreatScorer()

    def test_vc_tier_scoring(self):
        """Test scoring based on VC firm tiers."""
        # Tier A VC
        announcement_a = {
            'vc_firm': 'Sequoia Capital',
            'amount_raised_gbp': 0,
            'description': '',
            'sector': ''
        }
        score_a = self.scorer.score_announcement(announcement_a)
        assert "Backed by Tier A VC" in score_a.details
        # Base score for Tier A is 30, plus small round/unknown (10) = 40
        assert "Score: 40" in score_a.details

        # Unknown/Tier B VC
        announcement_b = {
            'vc_firm': 'Random Ventures',
            'amount_raised_gbp': 0
        }
        score_b = self.scorer.score_announcement(announcement_b)
        assert "Backed by Tier B VC" in score_b.details
        # Base Tier B (20) + default round (10) = 30
        assert "Score: 30" in score_b.details

        # No VC
        announcement_none = {'vc_firm': ''}
        score_none = self.scorer.score_announcement(announcement_none)
        assert "Unknown VC Tier" in score_none.details
        # Base Unknown (10) + default round (10) = 20
        assert "Score: 20" in score_none.details

    def test_round_size_scoring(self):
        """Test scoring based on investment amount."""
        # Large Round (>20M)
        ann = {'amount_raised_gbp': 25_000_000, 'vc_firm': ''}
        score = self.scorer.score_announcement(ann)
        assert "Large round >£20M" in score.details
        # 10 (VC) + 25 (Round) = 35

        # Significant Round (10-20M)
        ann = {'amount_raised_gbp': 15_000_000, 'vc_firm': ''}
        score = self.scorer.score_announcement(ann)
        assert "Significant round £10-20M" in score.details
        # 10 + 20 = 30

        # Moderate Round (5-10M)
        ann = {'amount_raised_gbp': 7_000_000, 'vc_firm': ''}
        score = self.scorer.score_announcement(ann)
        assert "Moderate round £5-10M" in score.details
        # 10 + 15 = 25

        # Small Round (<5M)
        ann = {'amount_raised_gbp': 1_000_000, 'vc_firm': ''}
        score = self.scorer.score_announcement(ann)
        assert "Seed/Small/Undisclosed round <£5M" in score.details
        # 10 + 10 = 20

    def test_sector_match_scoring(self):
        """Test scoring for high-interest sectors."""
        # Single match
        ann = {
            'sector': 'Fintech',
            'description': 'New bank',
            'vc_firm': '',
            'amount_raised_gbp': 0
        }
        score = self.scorer.score_announcement(ann)
        assert "Sector match: fintech" in score.details
        # 10 (VC) + 10 (Round) + 6 (Sector) = 26

        # Multiple matches (capped at 30)
        ann = {
            'sector': 'Healthcare Compliance',
            'description': 'ai for regulatory healthcare',
            'vc_firm': '',
            'amount_raised_gbp': 0
        }
        # Matches: healthcare, compliance, regulatory words likely in description/sector
        score = self.scorer.score_announcement(ann)
        assert "Sector match" in score.details

    def test_disruption_keywords(self):
        """Test AI and disruption keyword detection."""
        ann = {
            'description': 'Generative AI platform using LLM',
            'vc_firm': '',
            'amount_raised_gbp': 0
        }
        score = self.scorer.score_announcement(ann)
        assert "AI/Disruption keywords" in score.details
        # Should match 'generative', 'ai', 'llm'
        # 10 (VC) + 10 (Round) + 15 (Keywords maxed or high) = ~35

    def test_threat_level_assignment(self):
        """Test Critical/High/Medium/Low assignment."""
        # High Score Construction: Tier A (30) + Large Round (25) + Sector (30) + AI (15) = 100
        high_threat = {
            'vc_firm': 'Sequoia',
            'amount_raised_gbp': 50_000_000,
            'sector': 'Fintech',
            'description': 'Generative AI for compliance'
        }
        score = self.scorer.score_announcement(high_threat)
        assert score.threat_level == ThreatLevel.HIGH
        assert "CRITICAL" in score.details or "HIGH" in score.details

        # Low Score
        low_threat = {
            'vc_firm': '',
            'amount_raised_gbp': 0,
            'sector': 'Bakery',
            'description': 'Bread'
        }
        score = self.scorer.score_announcement(low_threat)
        assert score.threat_level == ThreatLevel.LOW


import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from src.universe.moat_scorer import MoatScorer
from src.core.models import CompanyTier

class TestTier2Fixes(unittest.TestCase):
    
    def setUp(self):
        self.company = MagicMock()
        self.company.name = "Test Corp"
        self.company.description = "A test company."
        self.company.revenue_gbp = 20_000_000 # > 15M -> +15
        self.company.employees = 50
        self.company.revenue_growth = 0.1
        self.company.moat_analysis = {}
        self.company.raw_website_text = "We are a great company."
        
        self.cert = MagicMock()
        self.cert.certification_type = "AS9100" # Score 50 -> Weight 1.0 -> 50
        self.certs = [self.cert]

    @patch('src.universe.moat_scorer.LLMMoatAnalyzer')
    def test_high_score_recalibration(self, MockAnalyzer):
        # Mock LLM returning high regulatory evidence
        mock_instance = MockAnalyzer.return_value
        mock_instance.analyze = AsyncMock(return_value={
            "regulatory": {"score": 80, "evidence": "Strong certs"},
            "network": {"score": 0},
            "liability": {"score": 0},
            "physical": {"score": 0},
            "ip": {"score": 0}
        })
        
        # Run scoring
        # AS9100 (50) vs LLM (80) -> Max 80.
        # Moat Score parts:
        # Regulatory: 80 * 1.0 = 80 (Cap 80)
        # Financial: +15
        # Total: 95
        
        score = asyncio.run(MoatScorer.score_with_llm(self.company, self.certs, {}, ""))
        
        self.assertEqual(score, 95)
        self.assertEqual(self.company.tier, CompanyTier.TIER_1A) # >= 70

    @patch('src.universe.moat_scorer.LLMMoatAnalyzer')
    def test_negative_signals(self, MockAnalyzer):
        # Mock LLM returning 0
        mock_instance = MockAnalyzer.return_value
        mock_instance.analyze = AsyncMock(return_value={})
        
        # 1. Declining Revenue
        self.company.revenue_growth = -0.1 # Penalty 20
        self.company.revenue_gbp = 100 # No scale bonus
        
        score = asyncio.run(MoatScorer.score_with_llm(self.company, [], {}, ""))
        # Score 0 - 20 -> -20 but capped at min 0?
        # Code says: score = min(int(score), 100). Doesn't max(0).
        # Integers can be negative. But Moat Score is usually 0-100?
        # Let's see behavior. If it's negative, it's fine, just tier will be low.
        
        self.assertLess(score, 0)
        
        # 2. Keylords
        self.company.revenue_growth = 0.1 # Positive
        text = "We are facing insolvency and administration."
        score = asyncio.run(MoatScorer.score_with_llm(self.company, [], {}, text))
        
        # Keywords: insolvency (10), administration (10) -> -20?
        # Loop breaks after > 40?
        # "insolvency" and "administration" are in list.
        # Check logic: for kw in keywords: if kw in text: penalties += 10.
        # "insolvency is bad" -> +10 penalty.
        # "administration process" -> +10 penalty.
        # Total -20.
        
        self.assertEqual(score, -20)

    @patch('src.universe.moat_scorer.LLMMoatAnalyzer')
    def test_semantic_context_passed(self, MockAnalyzer):
        # Setup semantic data
        semantic_data = {"test": "data"}
        self.company.moat_analysis = {"semantic": semantic_data}
        
        mock_instance = MockAnalyzer.return_value
        mock_instance.analyze = AsyncMock(return_value={})
        
        asyncio.run(MoatScorer.score_with_llm(self.company, [], {}, ""))
        
        # Check call args
        mock_instance.analyze.assert_called_with(
            company_name="Test Corp",
            description="A test company.",
            raw_text="",
            certifications=[],
            relationship_count=0,
            semantic_context=semantic_data
        )

if __name__ == '__main__':
    unittest.main()

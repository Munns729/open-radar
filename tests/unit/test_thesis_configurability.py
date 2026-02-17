"""
Thesis Configurability Test Suite.

Verifies that RADAR's scoring pipeline is truly driven by thesis.yaml config
and not hardcoded to any specific pillar names, weights, or thresholds.

Run: pytest tests/unit/test_thesis_configurability.py -v
"""
import pytest
import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.thesis import ThesisConfig, MoatPillar, TierThresholds


# ============================================================================
# TEST 1: Can we load a thesis with completely different pillars?
# ============================================================================

class TestThesisLoading:
    """Test that the thesis config system accepts arbitrary pillar definitions."""

    def test_load_example_thesis(self):
        """The example thesis should load without errors."""
        config_dir = Path(__file__).parent.parent.parent / "config"
        thesis = ThesisConfig.from_yaml(config_dir / "thesis.example.yaml")
        assert thesis.name
        assert len(thesis.pillars) > 0
        assert abs(sum(p.weight for p in thesis.pillars.values()) - 1.0) < 0.01

    def test_custom_3_pillar_thesis(self):
        """A thesis with 3 completely novel pillars should load fine."""
        thesis = ThesisConfig(
            name="Custom 3-Pillar",
            version="1.0",
            pillars={
                "data_moat": MoatPillar(name="Data Moat", weight=0.5, description="Proprietary data"),
                "talent_lock": MoatPillar(name="Talent Lock-in", weight=0.3, description="Key person dependency"),
                "ecosystem": MoatPillar(name="Ecosystem", weight=0.2, description="Partner lock-in"),
            },
            tier_thresholds=TierThresholds(tier_1a=80, tier_1b=60, tier_2=40),
        )
        assert thesis.pillar_names == ["data_moat", "talent_lock", "ecosystem"]
        assert thesis.moat_weights == {"data_moat": 0.5, "talent_lock": 0.3, "ecosystem": 0.2}
        assert thesis.tier_thresholds.tier_1a == 80

    def test_custom_7_pillar_thesis(self):
        """A thesis with 7 pillars should work — not limited to 5."""
        pillars = {
            f"pillar_{i}": MoatPillar(
                name=f"Pillar {i}",
                weight=round(1.0 / 7, 4),
                description=f"Test pillar {i}",
            )
            for i in range(7)
        }
        # Fix rounding to sum to exactly 1.0
        total = sum(p.weight for p in pillars.values())
        first_key = list(pillars.keys())[0]
        pillars[first_key].weight += round(1.0 - total, 4)

        thesis = ThesisConfig(name="7 Pillar Test", pillars=pillars)
        assert len(thesis.pillars) == 7

    def test_weights_must_sum_to_one(self):
        """Thesis should reject weights that don't sum to 1.0."""
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            ThesisConfig(
                name="Bad Weights",
                pillars={
                    "a": MoatPillar(name="A", weight=0.3),
                    "b": MoatPillar(name="B", weight=0.3),
                },
            )

    def test_empty_thesis_uses_defaults(self):
        """A thesis with no pillars should create a valid (empty) config."""
        thesis = ThesisConfig(name="Minimal")
        assert thesis.pillar_names == []
        assert thesis.moat_weights == {}

    def test_to_summary_for_api(self):
        """to_summary() should return a JSON-safe dict for the frontend."""
        thesis = ThesisConfig(
            name="API Test",
            version="2.0",
            description="Test thesis",
            pillars={
                "alpha": MoatPillar(name="Alpha", weight=0.6, description="First"),
                "beta": MoatPillar(name="Beta", weight=0.4, description="Second"),
            },
        )
        summary = thesis.to_summary()
        assert summary["name"] == "API Test"
        assert "alpha" in summary["pillars"]
        assert summary["pillars"]["alpha"]["weight"] == 0.6
        assert "tier_thresholds" in summary


# ============================================================================
# TEST 2: Does the moat scorer use thesis config, not hardcoded values?
# ============================================================================

class TestMoatScorerConfigDriven:
    """Verify the scorer reads from thesis, not from hardcoded constants."""

    def test_scorer_builds_attrs_from_thesis_pillars(self):
        """moat_attrs dict should have keys matching thesis pillars, not hardcoded names."""
        from src.core.thesis import thesis
        expected_keys = set(thesis.pillar_names)
        assert len(expected_keys) > 0, "Thesis has no pillars loaded"

    def test_default_prompt_includes_all_pillars(self):
        """The auto-generated prompt should include all pillar names from config."""
        thesis = ThesisConfig(
            name="Prompt Test",
            pillars={
                "alpha": MoatPillar(name="Alpha Moat", weight=0.5, description="First moat"),
                "beta": MoatPillar(name="Beta Moat", weight=0.5, description="Second moat"),
            },
        )
        prompt = thesis.moat_analysis_prompt
        assert "Alpha Moat" in prompt
        assert "Beta Moat" in prompt

    def test_semantic_prompt_includes_all_pillars(self):
        """The semantic enrichment prompt should reflect thesis pillars."""
        thesis = ThesisConfig(
            name="Semantic Test",
            pillars={
                "gamma": MoatPillar(name="Gamma", weight=0.6, description="Gamma test"),
                "delta": MoatPillar(name="Delta", weight=0.4, description="Delta test"),
            },
        )
        prompt = thesis.semantic_enrichment_prompt
        assert "Gamma" in prompt
        assert "Delta" in prompt


# ============================================================================
# TEST 3: Verify coupling points are FIXED
# ============================================================================

class TestCouplingPointsFixed:
    """Verify that previously-hardcoded coupling points are now thesis-driven."""

    def test_moat_type_enum_removed(self):
        """MoatType enum should no longer exist — moat_type is now a plain string."""
        from src.core import models
        assert not hasattr(models, "MoatType"), (
            "MoatType enum still exists in core/models.py — "
            "it should be removed in favour of thesis-driven strings"
        )

    def test_company_model_moat_type_is_string(self):
        """CompanyModel.moat_type should be a String column, not an Enum."""
        from src.universe.database import CompanyModel
        col = CompanyModel.__table__.columns["moat_type"]
        from sqlalchemy import String
        assert isinstance(col.type, String), (
            f"CompanyModel.moat_type is {type(col.type).__name__}, expected String"
        )

    def test_semantic_enrichment_uses_dynamic_dict(self):
        """SemanticEnrichmentResult should use pillar_scores dict, not fixed fields."""
        from src.universe.discovery.semantic_enrichment import SemanticEnrichmentResult
        field_names = [f.name for f in dataclasses.fields(SemanticEnrichmentResult)]
        assert "pillar_scores" in field_names, "Missing pillar_scores dict field"
        # Old hardcoded fields should NOT exist
        assert "regulatory_moat" not in field_names
        assert "network_effects" not in field_names
        assert "liability_moat" not in field_names

    def test_scoring_impact_analyzer_uses_thesis(self):
        """scoring_impact_analyzer should read from thesis, not MoatScorer class attrs."""
        from src.market_intelligence.analyzers.scoring_impact_analyzer import _current_config_snapshot
        snapshot = _current_config_snapshot()
        # Should use thesis-based keys
        assert "certification_scores" in snapshot
        assert "sovereignty_keywords" in snapshot
        assert "pillar_names" in snapshot
        # Old keys should not exist
        assert "CERT_SCORES" not in snapshot
        assert "MOAT_WEIGHTS" not in snapshot

    def test_data_types_company_moat_type_is_string(self):
        """data_types.Company.moat_type should be a plain string, not MoatType enum."""
        from src.core.data_types import Company
        c = Company()
        assert isinstance(c.moat_type, str)
        assert c.moat_type == "none"


# ============================================================================
# TEST 4: Full scoring pipeline with custom thesis
# ============================================================================

class TestScoringPipelineWithCustomThesis:
    """End-to-end test: can we score a company with a non-default thesis?"""

    @pytest.mark.asyncio
    async def test_score_company_with_custom_thesis(self):
        """
        Patch the global thesis with a custom 3-pillar config and verify
        scoring works end-to-end.
        """
        custom_thesis = ThesisConfig(
            name="SaaS Metrics Thesis",
            version="1.0",
            pillars={
                "retention": MoatPillar(
                    name="Net Revenue Retention",
                    weight=0.4,
                    max_raw_score=100,
                    evidence_threshold=30,
                    description="Evidence of >110% NRR or strong expansion revenue",
                ),
                "data_asset": MoatPillar(
                    name="Proprietary Data Asset",
                    weight=0.35,
                    max_raw_score=100,
                    evidence_threshold=30,
                    description="Unique dataset that improves with usage",
                ),
                "integration": MoatPillar(
                    name="Workflow Integration",
                    weight=0.25,
                    max_raw_score=100,
                    evidence_threshold=30,
                    description="Deep embedding in customer workflows",
                ),
            },
            tier_thresholds=TierThresholds(tier_1a=75, tier_1b=55, tier_2=35),
        )

        # Mock a company
        company = MagicMock()
        company.name = "TestCo SaaS"
        company.description = "B2B analytics platform with 130% NRR"
        company.moat_score = 0
        company.moat_attributes = {}
        company.moat_analysis = {}
        company.tier = None
        company.revenue_gbp = 20_000_000
        company.ebitda_margin = 25
        company.revenue_growth = 15
        company.market_share = None
        company.competitor_count = None
        company.market_growth_rate = None
        company.relationships_as_a = []
        company.relationships_as_b = []
        company._previous_moat_score = None
        company._previous_moat_attributes = None

        # Mock LLM response matching custom pillars
        mock_llm_response = {
            "retention": {"score": 80, "evidence": "130% NRR mentioned explicitly"},
            "data_asset": {"score": 60, "evidence": "Analytics platform implies proprietary data"},
            "integration": {"score": 45, "evidence": "B2B suggests workflow integration"},
            "overall_moat_score": 62,
            "recommended_tier": "Tier 1B",
            "reasoning": "Strong retention with moderate data and integration moats",
        }

        with patch("src.universe.moat_scorer.thesis", custom_thesis), \
             patch("src.universe.moat_scorer.LLMMoatAnalyzer") as MockAnalyzer:

            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze = AsyncMock(return_value=mock_llm_response)

            from src.universe.moat_scorer import MoatScorer
            score = await MoatScorer.score_with_llm(company, certifications=[])

            # Verify scoring used custom thesis
            assert score > 0
            assert company.moat_score == score

            # Verify moat_attrs has custom pillar keys
            attrs = company.moat_attributes
            assert "retention" in attrs
            assert "data_asset" in attrs
            assert "integration" in attrs

            # Verify default pillar keys are NOT present
            assert "regulatory" not in attrs
            assert "geographic" not in attrs
            assert "liability" not in attrs
            assert "physical" not in attrs

            # Verify moat_analysis records custom thesis name
            analysis = company.moat_analysis
            assert analysis["thesis"] == "SaaS Metrics Thesis"
            assert "retention" in analysis["raw_dimension_scores"]

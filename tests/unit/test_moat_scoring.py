"""
Moat Scoring Tests — NEEDS REWRITE.

These tests previously validated Picard-specific pillar logic (geographic, liability,
physical) with hardcoded weights. The scorer is now thesis-driven — pillar names,
weights, and thresholds all come from config/thesis.yaml.

For current coverage, see: tests/unit/test_thesis_configurability.py (13 tests).

TODO: Rewrite these tests to:
  1. Load thesis.example.yaml (or construct a ThesisConfig in fixtures)
  2. Assert against thesis.pillar_names and thesis.moat_weights dynamically
  3. Test cert scoring, platform detection, sovereignty, tier assignment,
     deal screening separation, negative signals, combined moats, and edge cases
"""
import pytest


@pytest.mark.skip(reason="Needs rewrite for thesis-driven scoring — see docstring")
class TestMoatScoring:
    def test_placeholder(self):
        pass

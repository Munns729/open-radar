"""
LLM Moat Analyzer Tests — NEEDS REWRITE.

Previously asserted Picard-specific pillar names in LLM responses (geographic,
liability, physical). The analyzer now returns whatever pillars are defined in
the active thesis config.

For current coverage, see: tests/unit/test_thesis_configurability.py

TODO: Rewrite to assert response keys match thesis.pillar_names dynamically.
"""
import pytest


@pytest.mark.skip(reason="Needs rewrite for thesis-driven pillars — see docstring")
class TestLLMMoatAnalyzer:
    def test_placeholder(self):
        pass

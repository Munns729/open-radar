import pytest
import json
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from src.universe.llm_moat_analyzer import LLMMoatAnalyzer

@pytest.mark.asyncio
class TestLLMMoatAnalyzerSimple:
    @patch("src.universe.llm_moat_analyzer.client.chat.completions.create")
    async def test_parsing_minimal(self, mock_create):
        analyzer = LLMMoatAnalyzer()
        
        # Create a real-looking response object using SimpleNamespace
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"regulatory": {"score": 85}, "network": {"score": 0}, "geographic": {"score": 0}, "liability": {"score": 0}, "physical": {"score": 0}, "overall_moat_score": 85, "recommended_tier": "Tier 2", "reasoning": "test"}'
                    )
                )
            ],
            usage=None
        )
        mock_create.return_value = response
        
        result = await analyzer.analyze("Test Co")
        assert result["regulatory"]["score"] == 85

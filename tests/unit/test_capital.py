"""
Unit tests for Capital Flows Module (Module 10).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date

from src.capital.scrapers.base_agent import BaseBrowsingAgent, AgentAction
from src.capital.analyzers.exit_matcher import ExitMatcher
from src.capital.database import PEFirmModel, PEInvestmentModel, StrategicAcquirerModel, ConsolidatorModel
from src.core.data_types import Company

# --- Fixtures ---

@pytest.fixture
def mock_session():
    return MagicMock()

# --- Test Analysis Engines ---

def test_exit_matcher(mock_session):
    # Setup mocks for different models
    def query_side_effect(model):
        qry = MagicMock()
        if model == StrategicAcquirerModel:
            qry.filter.return_value.all.return_value = [
                StrategicAcquirerModel(
                    name="Defense Corp",
                    category="Defense",
                    acquisition_budget_annual_usd=1000,
                    values_regulatory_moats=True,
                    acquisitions_last_24mo=2,
                    typical_multiple_paid=12.5
                )
            ]
        elif model == ConsolidatorModel:
            qry.filter.return_value.all.return_value = [
                ConsolidatorModel(
                    name="DefRollup",
                    sector_focus="Defense",
                    typical_target_size_min_usd=50,
                    typical_target_size_max_usd=500
                )
            ]
        return qry
        
    mock_session.query.side_effect = query_side_effect
    
    matcher = ExitMatcher(mock_session)
    
    target = Company(
        name="Target Co",
        sector="Defense",
        revenue_gbp=100,
        moat_type="regulatory"
    )
    
    candidates = matcher.find_exit_candidates(target)
    
    # Expect both a strategic and a consolidator
    assert len(candidates) >= 1
    # Check that we found the strategic
    strat_match = next((c for c in candidates if c.buyer_type == "strategic"), None)
    assert strat_match is not None
    assert strat_match.buyer_name == "Defense Corp"
    
    # Check consolidator
    consol_match = next((c for c in candidates if c.buyer_type == "consolidator"), None)
    assert consol_match is not None
    assert consol_match.buyer_name == "DefRollup"

# --- Test Scraper Logic (Mocked) ---

class ConcreteTestAgent(BaseBrowsingAgent):
    """Concrete implementation for testing"""
    async def run(self, input_data):
        return []

@pytest.mark.asyncio
async def test_base_agent_logic():
    # Test that ask_llm parses JSON correctly
    # Use concrete class instead of abstract base
    agent = ConcreteTestAgent(headless=True, api_key="dummy")
    
    # Mock OpenAI client
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"action": "click", "selector": "#btn"}'
    
    agent.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    decision = await agent.ask_llm("goal", "html content")
    
    assert decision["action"] == "click"
    assert decision["selector"] == "#btn"

@pytest.mark.asyncio
async def test_agent_execution_flow():
    # Test the loop in a concrete agent (e.g. SECEdgar)
    # We'll mock the internal steps to avoid real browsing
    pass 

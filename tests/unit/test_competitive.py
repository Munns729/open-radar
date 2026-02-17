"""Unit tests for Competitive Radar module"""
import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import MagicMock, AsyncMock, patch

from src.competitive.database import init_db, create_vc_firm, create_announcement, VCFirmModel, VCAnnouncementModel, ThreatScoreModel
from src.core.database import get_sync_db
from src.competitive.threat_scorer import ThreatScorer
from src.competitive.kimi_analyzer import KimiAnalyzer
from src.core.models import ThreatLevel

# --- Database Tests ---
@pytest.fixture(scope="module")
def db():
    # Initialize in-memory SQLite for testing
    # Note: init_db uses the configured database, for tests we would need to override settings
    # For now, we'll assume init_db() initializes tables on the configured DB
    # In a more robust setup, we'd mock settings.database_url
    init_db()
    return None  # No db object needed anymore

def test_create_vc_firm(db):
    data = {
        "name": "Test Ventures",
        "tier": "A",
        "focus_sectors": ["SaaS", "AI"],
        "typical_check_size_gbp": 1000000
    }
    firm = create_vc_firm(data)
    assert firm.id is not None
    assert firm.name == "Test Ventures"
    # Note: SQLite stores arrays as strings locally if not mapped, but our model logic handles it
    
def test_create_announcement(db):
    ann_data = {
        "company_name": "NewCo",
        "round_type": "Seed",
        "amount_gbp": 2000000,
        "announced_date": date.today(),
        "source_url": "http://test.com"
    }
    threat_data = {
        "category": "fintech",
        "threat_score": 75,
        "threat_level": "high",
        "reasoning": "Test reasoning"
    }
    ann = create_announcement(ann_data, threat_data)
    assert ann.id is not None
    assert ann.company_name == "NewCo"
    
    # Check relationship
    with get_sync_db() as session:
        saved_threat = session.query(ThreatScoreModel).filter_by(announcement_id=ann.id).first()
        assert saved_threat is not None
        assert saved_threat.threat_score == 75

# --- Threat Scorer Tests ---
def test_threat_scoring_critical():
    scorer = ThreatScorer()
    announcement = {
        "company_name": "BaddestAI",
        "vc_firm": "Sequoia Capital", # Tier A (+30)
        "amount_raised_gbp": 25_000_000, # >20M (+25)
        "description": "Building next gen AI for aerospace", # AI(+5), Aerospace(+6)
        "sector": "Aerospace"
    }
    # Expected: 30 + 25 + 5 + 6 = 66 -> High/Critical range
    # Actually logic: Tier A(30) + >20M(25) + Match 'aerospace'(6) + Match 'ai'(5) = 66
    
    score = scorer.score_announcement(announcement)
    assert score.score_date is not None
    assert "Sequoia" in score.details
    assert "66" in score.details
    assert score.threat_level == ThreatLevel.HIGH

def test_threat_scoring_low():
    scorer = ThreatScorer()
    announcement = {
        "company_name": "BoringCo",
        "vc_firm": "UnknownVC", # Tier C (+10)
        "amount_raised_gbp": 100_000, # <5M (+10)
        "description": "Selling cookies", # No match
        "sector": "Food"
    }
    # Expected: 10 + 10 = 20 -> Low
    score = scorer.score_announcement(announcement)
    assert "20" in score.details
    assert score.threat_level == ThreatLevel.LOW

# --- Kimi Analyzer Tests ---
@pytest.mark.asyncio
async def test_kimi_analyzer_mock():
    with patch("src.core.config.Config.MOONSHOT_API_KEY", "fake_key"):
        analyzer = KimiAnalyzer()

    
    # Mock OpenAI client
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"announcements": [{"company_name": "TestCo", "vc_firm": "TestVC", "amount_raised_gbp": 100}]}'
    mock_response.usage.total_tokens = 100
    
    analyzer.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    result = await analyzer.analyze_screenshots(["base64img"])
    
    assert result.result["announcements"][0]["company_name"] == "TestCo"
    assert result.tokens_used == 100

# --- LinkedIn Scraper Tests ---
@pytest.mark.asyncio
async def test_scraper_run_mock():
    # We construct the scraper but mock internal playwright components to avoid browser launch
    with patch("src.competitive.linkedin_scraper.async_playwright") as mock_func:
        # Mock the context manager returned by async_playwright()
        mock_cm = MagicMock()
        mock_func.return_value = mock_cm
        
        # Mock the playwright object returned by await start()
        mock_playwright_obj = MagicMock()
        mock_cm.start = AsyncMock(return_value=mock_playwright_obj)
        
        # Mock browser launch
        mock_browser = MagicMock()
        mock_playwright_obj.chromium.launch = AsyncMock(return_value=mock_browser)
        
        # Mock context and page
        mock_context = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        mock_page = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Since scraper is already instantiated above with 'from ...', 
        # we need to ensure we are testing a fresh instance or the one that uses our patched import?
        # The 'from' import happened inside previous failing block?
        # Actually, if we instantiate LinkedInScraper inside the patch context, it uses the patched version if it imports inside methods? 
        # No, imports are top-level.
        # But 'src.competitive.linkedin_scraper.async_playwright' is what is patched.
        
        # Instantiate scraper here
        from src.competitive.linkedin_scraper import LinkedInScraper
        scraper = LinkedInScraper() 
        
        # Mock page interactions
        mock_page.goto = AsyncMock()
        mock_page.url = "https://www.linkedin.com/feed/"
        # screenshot is async
        mock_page.screenshot = AsyncMock(return_value=b"fake_image_bytes")
        # evaluate and wait_for_load_state are async
        mock_page.evaluate = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        await scraper.setup_session()
        assert scraper.page is not None
        
        output = await scraper.scrape_feed(scrolls=1)
        assert len(output.data) == 1
        assert output.data[0]["image"] is not None

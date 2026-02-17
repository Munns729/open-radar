import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import AsyncMock, patch, MagicMock

from src.market_intelligence.database import NewsSource, IntelligenceItem, RegulatoryChange, MarketTrend
from src.market_intelligence.sources.news_aggregator import NewsAggregator
from src.market_intelligence.sources.regulatory_monitor import RegulatoryMonitor
from src.market_intelligence.analyzers.relevance_scorer import RelevanceScorer
from src.market_intelligence.analyzers.trend_detector import TrendDetector
from src.market_intelligence.synthesizers.weekly_briefing import WeeklyBriefingGenerator

# Mocks
@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mocking commit/add/execute
    session.add = MagicMock()
    session.commit = AsyncMock()
    
    # Mock execute return
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    return session

@pytest.mark.asyncio
async def test_news_aggregator_add_source(mock_session):
    agg = NewsAggregator(mock_session)
    source = await agg.add_source("Test Source", "http://test.com", "test_cat")
    
    assert source.name == "Test Source"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_news_aggregator_fetch_rss(mock_session):
    # Mock feedparser and aiohttp
    with patch("src.market_intelligence.sources.news_aggregator.feedparser.parse") as mock_parse, \
         patch("src.market_intelligence.sources.news_aggregator.aiohttp.ClientSession.get") as mock_get:
         
         # Mock feed content
         # Mock feed content
         mock_entry = MagicMock()
         # Configure .get() to look up attributes or return default
         def get_side_effect(key, default=None):
             if key == 'published_parsed':
                 return (2025, 1, 1, 12, 0, 0, 0, 0, 0)
             if key == 'title':
                 return "Test Article"
             if key == 'link':
                 return "http://test.com/1"
             if key == 'summary':
                 return "Test Content"
             if key == 'description':
                 return "Test Content"
             return default
             
         mock_entry.get.side_effect = get_side_effect
         mock_entry.title = "Test Article"
         mock_entry.link = "http://test.com/1"
         mock_entry.content = [MagicMock(value="Test Content")]
         
         mock_feed = MagicMock()
         mock_feed.entries = [mock_entry]
         mock_parse.return_value = mock_feed

         # Mock Request
         mock_response = AsyncMock()
         mock_response.status = 200
         mock_response.text.return_value = "rss content"
         mock_get.return_value.__aenter__.return_value = mock_response
         
         agg = NewsAggregator(mock_session)
         source = NewsSource(id=1, name="Test", url="http://test.com", category="test", source_type="rss")
         
         items = await agg.fetch_rss_feed(source)
         assert len(items) == 1
         assert items[0]['title'] == "Test Article"

@pytest.mark.asyncio
async def test_relevance_scorer(mock_session):
    scorer = RelevanceScorer(mock_session)
    item = IntelligenceItem(id=1, title="Test", content="Test content")
    
    with patch.object(scorer, 'call_kimi_api', return_value='{"relevance_score": 80, "key_points": []}'):
        await scorer.score_item(item)
        mock_session.execute.assert_called()
        mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_trend_detector(mock_session):
    detector = TrendDetector(mock_session)
    
    # Mock return of items
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        IntelligenceItem(id=1, title="Article 1", relevance_score=80, published_date=datetime.now())
    ]
    mock_session.execute.return_value = mock_result
    
    with patch.object(detector, 'call_simulated_ai', return_value='[{"trend_name": "AI", "sector": "Tech", "trend_type": "tech", "strength": "emerging", "supporting_evidence": [], "implications_for_thesis": "", "confidence": "high"}]'):
        trends = await detector.detect_trends()
        assert len(trends) == 1
        assert trends[0]['trend_name'] == "AI"
        mock_session.add.assert_called()

@pytest.mark.asyncio
async def test_weekly_briefing(mock_session):
    gen = WeeklyBriefingGenerator(mock_session)
    
    # Mock minimal response for all queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    briefing = await gen.generate_briefing(date.today())
    assert briefing is not None
    mock_session.add.assert_called()

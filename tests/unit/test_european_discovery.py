import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.universe.scrapers.european_discovery import EuropeanDiscoveryScraper

@pytest.fixture
def mock_page():
    page = AsyncMock()
    # page.locator() is sync, return value's all() is async
    locator_mock = MagicMock()
    mock_res = AsyncMock()
    mock_res.inner_text.return_value = "Test GmbH\nISO zertifizierter Maschinenbau in Berlin"
    
    locator_mock.all = AsyncMock(return_value=[mock_res])
    page.locator = MagicMock(return_value=locator_mock)
    
    return page

@pytest.mark.asyncio
async def test_european_discovery_de(mock_page):
    """Test discovery in Germany"""
    with patch("src.universe.scrapers.european_discovery.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        # Complete async lifecycle mocking
        mock_pw.return_value.start = AsyncMock(return_value=mock_pw.return_value)
        mock_pw.return_value.stop = AsyncMock()
        mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.close = AsyncMock()
        
        async with EuropeanDiscoveryScraper() as scraper:
            result = await scraper.discover_region("DE", limit=1)
            
            assert result.row_count == 1
            assert result.data[0]['name'] == "Test GmbH"
            assert result.data[0]['hq_country'] == "DE"

@pytest.mark.asyncio
async def test_european_discovery_fr(mock_page):
    """Test discovery in France"""
    mock_page.locator.return_value.all.return_value[0].inner_text.return_value = "Test SAS\nEntreprise certifiée ISO à Paris"
    
    with patch("src.universe.scrapers.european_discovery.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        # Complete async lifecycle mocking
        mock_pw.return_value.start = AsyncMock(return_value=mock_pw.return_value)
        mock_pw.return_value.stop = AsyncMock()
        mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.close = AsyncMock()
        
        async with EuropeanDiscoveryScraper() as scraper:
            result = await scraper.discover_region("FR", limit=1)
            
            assert result.row_count == 1
            assert result.data[0]['name'] == "Test SAS"
            assert result.data[0]['hq_country'] == "FR"

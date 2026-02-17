"""
Tests for Deep Website Scraper enhancements.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.universe.scrapers.website_scraper import WebsiteScraper

@pytest.fixture
def mock_page():
    page = AsyncMock()
    
    # get_by_role is a synchronous method that returns a Locator
    # Locator.all() is an asynchronous method
    locator_mock = MagicMock()
    locator_mock.all = AsyncMock(return_value=[])
    page.get_by_role = MagicMock(return_value=locator_mock)
    
    # Also setup locator() for other tests if needed
    page.locator = MagicMock(return_value=locator_mock)
    locator_mock.inner_text = AsyncMock(return_value="Content")
    
    return page

@pytest.mark.asyncio
async def test_find_nav_links(mock_page):
    """Test identification of relevant navigation links"""
    scraper = WebsiteScraper()
    
    # Mock links
    link_about = AsyncMock()
    link_about.get_attribute.return_value = "/about-us"
    link_about.inner_text.return_value = "About Us"
    
    link_contact = AsyncMock()
    link_contact.get_attribute.return_value = "/contact"
    link_contact.inner_text.return_value = "Contact" # Should be ignored - not in keywords
    
    link_tech = AsyncMock()
    link_tech.get_attribute.return_value = "/technology"
    link_tech.inner_text.return_value = "Our Technology"
    
    # Setup mock to return these links
    mock_page.get_by_role.return_value.all.return_value = [link_about, link_contact, link_tech]
    
    # Run the method
    links = await scraper._find_nav_links(mock_page, "https://example.com")
    
    # Assertions
    assert "https://example.com/about-us" in links
    assert "https://example.com/technology" in links
    assert "https://example.com/contact" not in links
    assert len(links) == 2 # Contact ignored

@pytest.mark.asyncio
async def test_scrape_deep_integration():
    """
    Test the full scrape flow with mocked pages.
    """
    scraper = WebsiteScraper()
    
    # Mock BaseScraper methods
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    
    scraper.create_browser_context = AsyncMock(return_value=(mock_browser, mock_context, mock_page))
    scraper.close_browser_context = AsyncMock()
    
    # 1. Main Page interaction
    mock_page.goto = AsyncMock(return_value=None)
    # Side effect for inner_text to vary by call
    mock_page.inner_text = AsyncMock(side_effect=["Main Content", "About Content", "Tech Content"])
    mock_page.get_attribute = AsyncMock(return_value="Meta Desc") # for description
        
    # 2. Mock finding links - Mock the method on the instance to simplify integration test
    # validation of logic is in test_find_nav_links
    with patch.object(scraper, '_find_nav_links', return_value=["https://example.com/about", "https://example.com/tech"]) as mock_nav:
         
        result = await scraper.scrape("https://example.com")
        
        # Assertions
        assert result["description"] is not None
        assert "--- HOMEPAGE ---" in result["raw_text"]
        assert "--- ABOUT ---" in result["raw_text"]
        assert "--- TECH ---" in result["raw_text"]
        assert len(result["raw_text"]) > 20 # Contains content

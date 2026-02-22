"""
Unit tests for Universe Scanner (Module 1).
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.universe.database import Base, CompanyModel, CertificationModel, CompanyRelationshipModel
from src.universe.scrapers import AS9100Scraper, CompaniesHouseScraper
from src.core.models import CompanyTier
from src.core.data_types import ScraperOutput

# --- Database Fixtures ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    """InMemory SQLite session for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# --- Scraper Tests ---

@pytest.mark.asyncio
async def test_as9100_scraper():
    """Test AS9100 scraper parsing logic"""
    # Mock Playwright
    with patch("src.universe.scrapers.browser.as9100_scraper.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # AS9100Scraper calls many awaitable methods
        mock_pw.return_value.start = AsyncMock(return_value=mock_pw.return_value)
        mock_pw.return_value.stop = AsyncMock()
        mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.close = AsyncMock()



        
        # Mock locator for Google Search results
        mock_res = AsyncMock()
        mock_res.inner_text.return_value = "Test Aerospace Ltd\nAS9100 Certified Supplier in London"
        
        # page.locator is sync, locator().all() is async
        locator_mock = MagicMock()
        locator_mock.all = AsyncMock(return_value=[mock_res])
        mock_page.locator = MagicMock(return_value=locator_mock)

        
        async with AS9100Scraper() as scraper:
            result = await scraper.scrape_by_country("GB")
            
            assert result.row_count == 1
            assert result.data[0]['name'] == "Test Aerospace Ltd" # clean_company_name preserves casing



@pytest.mark.asyncio
async def test_companies_house_scraper_search():
    """Test Companies House search"""
    mock_files = {"items": [{"company_number": "123", "company_name": "Test Co", "company_status": "active"}]}
    
    with patch("src.universe.scrapers.api.companies_house_scraper.CompaniesHouseScraper._get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_files
        
        async with CompaniesHouseScraper(api_key="fake") as scraper:
            results = await scraper.search_companies("Test")
            assert len(results) == 1
            assert results[0]['company_number'] == "123"


def test_revenue_plausible_for_accounts():
    """Sanity-check LLM revenue against CH account type bands."""
    from src.universe.revenue_bands import revenue_plausible_uk
    def rev(accounts, revenue):
        return revenue_plausible_uk(accounts, revenue)
    # Micro-entity: ≤£1.5M
    assert rev({"last_accounts": {"type": "micro-entity"}}, 1_000_000) is True
    assert rev({"last_accounts": {"type": "micro-entity"}}, 2_000_000) is False
    # Small: ≤£20M
    assert rev({"last_accounts": {"type": "small"}}, 15_000_000) is True
    assert rev({"last_accounts": {"type": "small"}}, 25_000_000) is False
    # Medium: ≤£60M
    assert rev({"last_accounts": {"type": "medium"}}, 50_000_000) is True
    assert rev({"last_accounts": {"type": "medium"}}, 70_000_000) is False
    # Full: no cap
    assert rev({"last_accounts": {"type": "full"}}, 500_000_000) is True
    # Dormant: reject any revenue
    assert rev({"last_accounts": {"type": "dormant"}}, 100) is False
    # Unknown/empty: cap at £60M
    assert rev({}, 50_000_000) is True
    assert rev({}, 100_000_000) is False
    assert rev({"last_accounts": {}}, 50_000_000) is True
    assert rev({"last_accounts": {"type": "unknown"}}, 100_000_000) is False


def test_uk_band_midpoint():
    """Band midpoint used when LLM revenue misaligned."""
    from src.universe.revenue_bands import get_uk_band_from_accounts
    r = get_uk_band_from_accounts({"last_accounts": {"type": "micro-entity"}})
    assert r is not None
    cap, mid, src = r
    assert cap == 1_500_000
    assert mid == 750_000
    assert src == "ch_band_midpoint"
    r = get_uk_band_from_accounts({"last_accounts": {"type": "small"}})
    assert r[1] == 10_000_000


def test_eu_band_from_employees():
    """EU SME band inferred from employee count."""
    from src.universe.revenue_bands import infer_eu_band_from_employees
    r = infer_eu_band_from_employees(5)
    assert r is not None
    cap, mid, src = r
    assert src == "eu_band_midpoint"
    assert mid == int(1_000_000 * 0.85)


# --- Moat Scorer Tests ---
# NOTE: Legacy tests removed — called dead method MoatScorer.score_picard_defensibility().
# Moat scoring is now thesis-driven. See tests/unit/test_thesis_configurability.py for coverage.


# --- Workflow Tests ---

@pytest.mark.asyncio
async def test_workflow_integration(db_session):
    """Test full workflow with mocks"""
    from src.universe.workflow import build_universe, SessionLocal
    
    # Mock SessionLocal to return our test session
    with patch("src.universe.workflow.SessionLocal", return_value=db_session), \
         patch("src.universe.workflow.init_db", new_callable=AsyncMock), \
         patch("src.universe.scrapers.browser.as9100_scraper.AS9100Scraper.scrape_by_country", new_callable=AsyncMock) as mock_as9100, \
         patch("src.universe.scrapers.browser.iso_registry_scraper.ISORegistryScraper.scrape_iso9001", new_callable=AsyncMock) as mock_iso, \
         patch("src.universe.scrapers.api.companies_house_scraper.CompaniesHouseScraper._get", new_callable=AsyncMock) as mock_ch_get:
         
        # Setup mock data return
        mock_as9100.return_value = ScraperOutput(
            source="Test", data_type="cert", 
            data=[{"name": "Test Co", "address": "123 Test", "certification_number": "C1", "metadata": {"country": "GB"}}], 
            row_count=1
        )
        mock_iso.return_value = ScraperOutput(source="Test", data_type="cert", data=[], row_count=0)
        
        # Side effect for _get
        async def ch_get_side_effect(endpoint, params=None):
            if "search" in endpoint:
                 return {"items": [{"company_number": "123", "title": "Test Co Limited", "date_of_creation": "2020-01-01"}]}
            if "/company/123" in endpoint:
                 return {"company_name": "Test Co Limited", "status": "active"}
            return None
            
        mock_ch_get.side_effect = ch_get_side_effect
        
        # Run workflow
        await build_universe(mode="full")
        
        # Verify DB state
        company = db_session.query(CompanyModel).filter_by(name="Test Co").first()
        assert company is not None
        assert company.companies_house_number == "123" # Enriched

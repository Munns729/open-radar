import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.universe.scrapers.opencorporates_scraper import OpenCorporatesScraper

@pytest.mark.asyncio
async def test_search_companies_success():
    scraper = OpenCorporatesScraper()
    
    # Mock response data
    mock_response = {
        "results": {
            "companies": [
                {
                    "company": {
                        "name": "Dassault Systemes",
                        "company_number": "322306440",
                        "jurisdiction_code": "fr",
                        "current_status": "Active",
                        "registered_address_in_full": "10 RUE MARCEL DASSAULT, VELIZY-VILLACOUBLAY, 78140"
                    }
                }
            ]
        }
    }
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        results = await scraper.search_companies("Dassault", "FR")
        
        assert len(results) == 1
        assert results[0]["name"] == "Dassault Systemes"
        assert results[0]["company_number"] == "322306440"
        assert results[0]["jurisdiction"] == "fr"

@pytest.mark.asyncio
async def test_get_company_success():
    scraper = OpenCorporatesScraper()
    
    # Mock response data
    mock_response = {
        "results": {
            "company": {
                "name": "Dassault Systemes",
                "company_number": "322306440",
                "jurisdiction_code": "fr",
                "officers": [{}, {}, {}, {}, {}], # 5 officers
                "industry_codes": [
                    {
                        "industry_code": {
                            "code": "6201Z",
                            "description": "Edition de logiciels",
                            "code_scheme_name": "fr_naf_2008"
                        }
                    }
                ]
            }
        }
    }
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        profile = await scraper.get_company("fr", "322306440")
        
        assert profile is not None
        assert profile["name"] == "Dassault Systemes"
        assert profile["officers_count"] == 5
        assert len(profile["industry_codes"]) == 1
        assert profile["industry_codes"][0]["code"] == "6201Z"

def test_estimate_company_size():
    # Test our heuristic
    assert OpenCorporatesScraper.estimate_company_size(0) is None
    assert OpenCorporatesScraper.estimate_company_size(2) == 15
    assert OpenCorporatesScraper.estimate_company_size(7) == 50
    assert OpenCorporatesScraper.estimate_company_size(15) == 200
    assert OpenCorporatesScraper.estimate_company_size(30) == 500

@pytest.mark.asyncio
async def test_search_rate_limit_handling():
    scraper = OpenCorporatesScraper()
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 429
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limit", request=MagicMock(), response=mock_get.return_value
        )
        
        results = await scraper.search_companies("Dassault", "FR")
        assert results == []

"""
Integration tests for FastAPI endpoints.
Validates status codes and basic response structure.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.web.app import app

@pytest.fixture
def api_client():
    return TestClient(app)

class TestApiEndpoints:
    """Tests for various API endpoints in app.py."""

    def test_root_endpoint(self, api_client):
        """Test the root API endpoint."""
        # Root redirects to /dashboard which requires auth, so expect 401 without creds
        response = api_client.get("/", follow_redirects=True)
        assert response.status_code == 401

    @patch("src.web.app.async_session_factory")
    def test_get_companies(self, mock_factory, api_client):
        """Test the /api/universe/companies endpoint."""
        # Mock the session and result
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        response = api_client.get("/api/universe/companies")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("src.web.app.async_session_factory")
    def test_global_search(self, mock_factory, api_client):
        """Test the /api/search endpoint."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock multiple searches inside the endpoint
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        response = api_client.get("/api/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "companies" in data
        assert "contacts" in data
        assert "deals" in data

    @patch("src.web.app.async_session_factory")
    def test_get_dashboard_stats(self, mock_factory, api_client):
        """Test the /api/dashboard/stats endpoint."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result
        
        response = api_client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_companies"] == 10

    @patch("src.web.app.async_session_factory")
    def test_get_competitive_feed(self, mock_factory, api_client):
        """Test the /api/competitive/feed endpoint."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Test without filter
        response = api_client.get("/api/competitive/feed")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # Test with filter
        response = api_client.get("/api/competitive/feed?firm_id=1")
        assert response.status_code == 200

    @patch("src.web.app.async_session_factory")
    def test_get_competitive_firms(self, mock_factory, api_client):
        """Test the /api/competitive/firms endpoint."""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        response = api_client.get("/api/competitive/firms")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_report_history(self, api_client):
        """Test the /api/reports/history endpoint."""
        # This endpoint reads from 'outputs' directory
        response = api_client.get("/api/reports/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

from unittest.mock import MagicMock

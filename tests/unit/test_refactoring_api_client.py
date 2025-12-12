"""Tests for API client refactoring - verify existing behavior before refactoring."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams, APIResponse
from crawler.config import CrawlerConfig


class TestHogangnonoAPIClientBehavior:
    """Test existing behavior of HogangnonoAPIClient before refactoring."""

    @pytest.fixture
    def mock_config(self):
        """Mock CrawlerConfig."""
        config = Mock(spec=CrawlerConfig)
        config.user_agent = "Mozilla/5.0 Test Agent"
        config.timeout = 30
        config.max_retries = 3
        return config

    @pytest.fixture
    def api_client(self, mock_config):
        """Create HogangnonoAPIClient instance."""
        with patch("crawler.api.hogangnono_client.Session"):
            client = HogangnonoAPIClient(mock_config)
            # Mock the session to avoid actual network calls
            client.session = Mock()
            client._session_initialized = True
            return client

    def test_initialization(self, mock_config):
        """Test API client initialization."""
        with patch("crawler.api.hogangnono_client.Session"):
            client = HogangnonoAPIClient(mock_config)

            assert client.config == mock_config
            assert client.base_url == "https://hogangnono.com"
            assert hasattr(client, "rate_limiter")
            assert hasattr(client, "cache")
            assert hasattr(client, "error_handler")
            assert hasattr(client, "circuit_breaker")

    def test_build_url(self, api_client):
        """Test URL building."""
        # Test with leading slash
        url = api_client._build_url("/api/test")
        assert url == "https://hogangnono.com/api/test"

        # Test without leading slash
        url = api_client._build_url("api/test")
        assert url == "https://hogangnono.com/api/test"

    def test_get_api_headers(self, api_client):
        """Test API header generation."""
        headers = api_client._get_api_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "X-Requested-With" in headers
        assert "Referer" in headers
        assert "Origin" in headers

    def test_get_headers_method(self, api_client):
        """Test _get_headers method (simplified for tests)."""
        headers = api_client._get_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "x-hogangnono-app-name" in headers

    def test_get_pois_bounding_vs_get_apartments_bounding(self, api_client):
        """Test that get_pois_bounding and get_apartments_bounding are equivalent."""
        search_params = SearchParams(startX=127.0, endX=127.1, startY=37.0, endY=37.1)

        # Mock _make_request to track calls
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True, data=[])

            # Call both methods
            api_client.get_pois_bounding(search_params)
            api_client.get_apartments_bounding(search_params)

            # Both should call _make_request with same parameters
            assert mock_request.call_count == 2
            first_call = mock_request.call_args_list[0]
            second_call = mock_request.call_args_list[1]

            # They should be identical
            assert first_call[1] == second_call[1]  # keyword arguments should match

    def test_search_params_initialization(self):
        """Test SearchParams initialization and validation."""
        # Valid params
        params = SearchParams(
            startX=127.0, endX=127.1, startY=37.0, endY=37.1, level=15, tradeType=1
        )

        assert params.startX == 127.0
        assert params.endX == 127.1
        assert params.startY == 37.0
        assert params.endY == 37.1
        assert params.level == 15
        assert params.tradeType == 1

        # Test bbox conversion
        bbox_params = SearchParams(bbox=(127.0, 37.0, 127.1, 37.1))

        assert bbox_params.startX == 127.0
        assert bbox_params.endX == 127.1
        assert bbox_params.startY == 37.0
        assert bbox_params.endY == 37.1

        # Test invalid level
        with pytest.raises(ValueError, match="level must be between"):
            SearchParams(level=19)  # Invalid level

        # Test invalid tradeType
        with pytest.raises(ValueError, match="tradeType must be one of"):
            SearchParams(tradeType=5)  # Invalid trade type

    def test_search_params_to_dict(self):
        """Test SearchParams.to_dict method."""
        params = SearchParams(
            startX=127.0,
            endX=127.1,
            startY=37.0,
            endY=37.1,
            level=15,
            tradeType=1,
            aptType=0,
            priceType=1,
            rentType=0,
        )

        params_dict = params.to_dict()

        assert isinstance(params_dict, dict)
        assert params_dict["startX"] == 127.0
        assert params_dict["endX"] == 127.1
        assert params_dict["startY"] == 37.0
        assert params_dict["endY"] == 37.1
        assert params_dict["level"] == "15"  # Should be string
        assert params_dict["tradeType"] == 1
        assert params_dict["aptType"] == 0
        assert params_dict["priceType"] == 1
        assert params_dict["rentType"] == 0
        assert "map" in params_dict
        assert "screenWidth" in params_dict
        assert "screenHeight" in params_dict

    def test_api_response_from_response(self):
        """Test APIResponse.from_response with various scenarios."""
        # Mock successful JSON response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"data": [{"id": 1}]}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success
        assert api_response.data == [{"id": 1}]
        assert api_response.status_code == 200
        assert api_response.error is None

        # Mock error response
        mock_error_response = Mock()
        mock_error_response.status_code = 404
        mock_error_response.reason = "Not Found"
        mock_error_response.headers = {"content-type": "application/json"}
        mock_error_response.json.return_value = {"error": "Not found"}

        api_error_response = APIResponse.from_response(mock_error_response)

        assert not api_error_response.success
        assert api_error_response.status_code == 404
        assert "Not found" in api_error_response.error

    def test_extract_apartment_id(self, api_client):
        """Test _extract_apartment_id method."""
        # Test extraction from endpoint
        apt_id = api_client._extract_apartment_id("/api/v2/apts/APT123/monthly-reports", None)
        assert apt_id == "APT123"

        # Test extraction from parameters
        apt_id = api_client._extract_apartment_id("/api/v2/monthly-reports", {"complexNo": "456"})
        assert apt_id == "456"

        # Test no apartment ID found
        apt_id = api_client._extract_apartment_id("/api/v2/regions", None)
        assert apt_id is None

    def test_get_apartment_detail_deprecation(self, api_client):
        """Test that get_apartment_detail redirects to transactions."""
        with patch.object(api_client, "get_apartment_transactions") as mock_transactions:
            mock_transactions.return_value = APIResponse(success=True, data={})

            # Call deprecated method
            api_client.get_apartment_detail("APT123")

            # Should redirect to transactions with default parameters
            mock_transactions.assert_called_once_with(apt_id="APT123", trade_type=0, area_no=201)

    def test_error_handler_integration(self, api_client):
        """Test that error handler is properly integrated."""
        # Should have error handler instance
        assert hasattr(api_client, "error_handler")

        # Test error summary
        summary = api_client.get_error_summary()
        assert isinstance(summary, dict)

    def test_circuit_breaker_status(self, api_client):
        """Test circuit breaker status methods."""
        # Should have circuit breaker instance
        assert hasattr(api_client, "circuit_breaker")

        # Test status
        status = api_client.get_circuit_breaker_status()
        assert isinstance(status, dict)
        assert "state" in status
        assert "failure_count" in status
        assert "is_open" in status

        # Test manual reset
        api_client.reset_circuit_breaker()
        # Should not raise any errors

    def test_api_stats(self, api_client):
        """Test API statistics collection."""
        stats = api_client.get_api_stats()

        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "success_count" in stats
        assert "error_count" in stats
        assert "success_rate" in stats
        assert "cache_hit_rate" in stats
        assert "rate_limiter" in stats

    def test_context_manager(self, mock_config):
        """Test API client as context manager."""
        with patch("crawler.api.hogangnono_client.Session"):
            with HogangnonoAPIClient(mock_config) as client:
                assert client is not None
                # Should initialize session on enter
                # Session should be properly closed on exit

    def test_duplicate_methods_implementation(self, api_client):
        """Test that duplicate methods have identical implementations."""
        # Both fetch_ranks_rolling and get_ranking should exist
        assert hasattr(api_client, "fetch_ranks_rolling")
        assert hasattr(api_client, "get_ranking")

        # Both fetch_pois_bounding and get_pois_bounding should exist
        assert hasattr(api_client, "fetch_pois_bounding")
        assert hasattr(api_client, "get_pois_bounding")

        # Methods that are essentially aliases
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True, data={})

            # Test that both methods delegate to _make_request similarly
            api_client.fetch_ranks_rolling()
            first_call = mock_request.call_args

            mock_request.reset_mock()
            api_client.get_ranking()
            second_call = mock_request.call_args

            # Should call similar endpoints
            assert "/ranks/rolling" in str(first_call)
            assert "/ranks/rolling" in str(second_call)

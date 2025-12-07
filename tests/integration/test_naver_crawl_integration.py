"""Simplified integration tests for NaverRealEstateCrawler transaction functionality."""

import json
from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


class TestNaverCrawlerIntegration:
    """Simplified integration tests focusing on core functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CrawlerConfig(headless=True, timeout=30)

    def test_validate_transaction_method(self, config):
        """Test transaction validation logic directly."""
        crawler = NaverRealEstateCrawler(config)

        # Valid transaction
        valid_txn = {
            "tradeDate": "2025-11-14",
            "floor": 21,
            "dealPrice": 1700000000,
            "isDelete": False,
        }
        assert crawler._validate_transaction(valid_txn) is True

        # Invalid transaction (deleted)
        deleted_txn = {
            "tradeDate": "2025-11-14",
            "floor": 21,
            "dealPrice": 1700000000,
            "isDelete": True,
        }
        assert crawler._validate_transaction(deleted_txn) is False

        # Invalid transaction (missing fields)
        incomplete_txn = {"floor": 21, "dealPrice": 1700000000, "isDelete": False}
        assert crawler._validate_transaction(incomplete_txn) is False

        # Invalid transaction (empty trade date)
        empty_date_txn = {"tradeDate": "", "floor": 21, "dealPrice": 1700000000, "isDelete": False}
        assert crawler._validate_transaction(empty_date_txn) is False

    def test_parse_transaction_method(self, config):
        """Test transaction parsing logic directly."""
        crawler = NaverRealEstateCrawler(config)

        raw_txn = {
            "tradeDate": "2025-11-14",
            "tradeYear": "2025",
            "floor": 21,
            "dealPrice": 1700000000,
            "deposit": 0,
            "monthlyRent": 0,
            "isDelete": False,
            "tradeCategory": "중개거래",
            "isRenew": False,
        }

        parsed = crawler._parse_transaction(
            raw_txn,
            complex_id="111515",
            complex_name="테스트단지",
            pyeong_type_number=1,
            pyeong_name="84A",
            trade_type="A1",
        )

        # Verify all fields are properly set
        assert parsed["complex_id"] == "111515"
        assert parsed["complex_name"] == "테스트단지"
        assert parsed["pyeong_type_number"] == 1
        assert parsed["pyeong_name"] == "84A"
        assert parsed["trade_type"] == "A1"
        assert parsed["trade_type_name"] == "매매"
        assert parsed["trade_date"] == "2025-11-14"
        assert parsed["trade_year"] == "2025"
        assert parsed["floor"] == 21
        assert parsed["deal_price"] == 1700000000
        assert parsed["deposit"] == 0
        assert parsed["monthly_rent"] == 0
        assert parsed["trade_category"] == "중개거래"
        assert parsed["is_delete"] is False
        assert parsed["is_renew"] is False

    def test_trade_type_mapping(self, config):
        """Test that trade types are correctly mapped."""
        crawler = NaverRealEstateCrawler(config)

        raw_txn = {
            "tradeDate": "2025-11-14",
            "tradeYear": "2025",
            "floor": 21,
            "dealPrice": 1700000000,
            "deposit": 0,
            "monthlyRent": 0,
            "isDelete": False,
            "tradeCategory": "중개거래",
            "isRenew": False,
        }

        # Test 매매 (A1)
        parsed_a1 = crawler._parse_transaction(
            raw_txn,
            complex_id="111515",
            complex_name="테스트단지",
            pyeong_type_number=1,
            pyeong_name="84A",
            trade_type="A1",
        )
        assert parsed_a1["trade_type_name"] == "매매"

        # Test 전세 (B1)
        parsed_b1 = crawler._parse_transaction(
            raw_txn,
            complex_id="111515",
            complex_name="테스트단지",
            pyeong_type_number=1,
            pyeong_name="84A",
            trade_type="B1",
        )
        assert parsed_b1["trade_type_name"] == "전세"

        # Test 월세 (B2)
        parsed_b2 = crawler._parse_transaction(
            raw_txn,
            complex_id="111515",
            complex_name="테스트단지",
            pyeong_type_number=1,
            pyeong_name="84A",
            trade_type="B2",
        )
        assert parsed_b2["trade_type_name"] == "월세"

    @patch("crawler.crawlers.naver.sync_playwright")
    def test_fetch_transaction_history_with_mock_browser(self, mock_playwright, config):
        """Test fetch_transaction_history with properly mocked browser."""
        # Mock response data
        mock_response = {
            "isSuccess": True,
            "result": {
                "list": [
                    {
                        "tradeDate": "2025-11-14",
                        "tradeYear": "2025",
                        "floor": 21,
                        "dealPrice": 1700000000,
                        "deposit": 0,
                        "monthlyRent": 0,
                        "isDelete": False,
                        "tradeCategory": "중개거래",
                        "propertyType": "NORMAL",
                        "isRenew": False,
                    }
                ],
                "hasNextPage": False,
            },
        }

        # Setup proper browser mock
        mock_page = Mock()
        mock_page.evaluate.return_value = json.dumps(mock_response)
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.chromium.launch.return_value = mock_browser

        # Create context manager mock
        mock_pm = Mock()
        mock_cm = Mock()
        mock_cm.__enter__ = Mock(return_value=mock_browser)
        mock_cm.__exit__ = Mock(return_value=None)
        mock_pm.start.return_value = mock_cm
        mock_playwright.return_value = mock_cm

        # Mock Path for data file
        with patch("crawler.crawlers.naver.Path") as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance

            # Mock file reading
            mock_file = Mock()
            mock_path_instance.open.return_value.__enter__ = Mock(return_value=mock_file)
            mock_path_instance.open.return_value.__exit__ = Mock(return_value=None)
            mock_file.read.return_value = json.dumps({"districts": []})

            # Create crawler and test
            crawler = NaverRealEstateCrawler(config)
            crawler.rate_limiter = Mock()
            crawler.rate_limiter.wait = Mock()
            crawler.rate_limiter.on_success = Mock()

            # Test the method
            transactions = crawler.fetch_transaction_history(
                complex_id="111515",
                pyeong_type_number=1,
                trade_type="A1",
                complex_name="테스트단지",
                pyeong_name="84A",
            )

            # Verify results
            assert len(transactions) == 1
            assert transactions[0]["complex_id"] == "111515"
            assert transactions[0]["complex_name"] == "테스트단지"
            assert transactions[0]["pyeong_name"] == "84A"
            assert transactions[0]["trade_type"] == "A1"
            assert transactions[0]["deal_price"] == 1700000000

    def test_crawl_method_structure(self, config):
        """Test that crawl method has correct structure and imports."""
        # Check that all required components are imported
        from crawler.crawlers.naver import NaverRealEstateCrawler

        # Verify the method exists and has correct signature
        assert hasattr(NaverRealEstateCrawler, "crawl")
        import inspect

        sig = inspect.signature(NaverRealEstateCrawler.crawl)
        assert "self" in sig.parameters
        assert len(sig.parameters) == 1  # Only self parameter

        # Verify helper method exists
        assert hasattr(NaverRealEstateCrawler, "_fetch_transaction_history_with_details")
        helper_sig = inspect.signature(
            NaverRealEstateCrawler._fetch_transaction_history_with_details
        )
        expected_params = ["self", "complex_id", "pyeong_type_number", "trade_type"]
        actual_params = list(helper_sig.parameters.keys())
        assert actual_params == expected_params

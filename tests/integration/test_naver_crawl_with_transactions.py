"""Integration tests for NaverRealEstateCrawler with transaction data collection."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


class TestNaverRealEstateCrawlerWithTransactions:
    """Integration tests for extended crawl functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CrawlerConfig(headless=True, timeout=30)

    @pytest.fixture
    def mock_districts_data(self):
        """Mock districts data for testing."""
        return {
            "districts": [
                {
                    "district_name": "금천구",
                    "dongs": [
                        {
                            "dong_name": "가산동",
                            "cortarNo": "1154510100",
                            "bounds": {
                                "leftLon": 126.880,
                                "rightLon": 126.890,
                                "topLat": 37.480,
                                "bottomLat": 37.470,
                            },
                        }
                    ],
                }
            ]
        }

    @pytest.fixture
    def mock_complexes_response(self):
        """Mock API response for complexes list."""
        return {
            "result": [
                {
                    "hscpNo": "111515",
                    "hscpNm": "테스트단지",
                    "hscpTypeNm": "아파트",
                    "useAprvYmd": "202001",
                    "totDongCnt": 3,
                    "totHsehCnt": 500,
                    "minSpc": "84",
                    "maxSpc": "84",
                    "dealCnt": 5,
                    "leaseCnt": 3,
                    "rentCnt": 2,
                    "totalAtclCnt": 10,
                }
            ]
        }

    @pytest.fixture
    def mock_complex_detail_response(self):
        """Mock API response for complex detail."""
        return {
            "isSuccess": True,
            "result": [
                {
                    "pyeongTypeNumber": 1,
                    "pyeongName": "84A",
                    "supplyArea": "84.94",
                    "exclusiveArea": "71.97",
                    "roomCount": 3,
                    "bathroomCount": 2,
                    "householdCount": 150,
                }
            ],
        }

    @pytest.fixture
    def mock_transaction_response(self):
        """Mock API response for transaction history."""
        return {
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
                    },
                    {
                        "tradeDate": "2025-10-20",
                        "tradeYear": "2025",
                        "floor": 15,
                        "dealPrice": 0,
                        "deposit": 800000000,
                        "monthlyRent": 0,
                        "isDelete": False,
                        "tradeCategory": "중개거래",
                        "propertyType": "NORMAL",
                        "isRenew": False,
                    },
                    {
                        "tradeDate": "2025-09-10",
                        "tradeYear": "2025",
                        "floor": 8,
                        "dealPrice": 0,
                        "deposit": 100000000,
                        "monthlyRent": 2000000,
                        "isDelete": False,
                        "tradeCategory": "중개거래",
                        "propertyType": "NORMAL",
                        "isRenew": False,
                    },
                ],
                "hasNextPage": False,
            },
        }

    @patch("crawler.crawlers.naver.sync_playwright")
    @patch("crawler.crawlers.naver.Path")
    def test_crawl_with_transactions(
        self,
        mock_path,
        mock_playwright,
        config,
        mock_districts_data,
        mock_complexes_response,
        mock_complex_detail_response,
        mock_transaction_response,
    ):
        """Test full crawling pipeline with transaction data collection."""
        # Setup mocks
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file
        mock_path.return_value.parent = Path("/tmp")
        mock_path.return_value.__truediv__ = lambda self, other: Path(f"/tmp/{other}")

        # Mock playwright page
        mock_page = Mock()
        mock_page.evaluate.side_effect = [
            mock_complexes_response,  # complexes list API
            json.dumps(mock_complex_detail_response),  # pyeongList API
            json.dumps({"isSuccess": True, "result": {}}),  # holdingTax API
            json.dumps({"isSuccess": True, "result": {}}),  # declaredValue API
            json.dumps({"isSuccess": True, "result": {}}),  # askingPrice API
            json.dumps({"isSuccess": True, "result": {}}),  # marketPrice API
            json.dumps(mock_transaction_response),  # transaction history API (A1)
            json.dumps(mock_transaction_response),  # transaction history API (B1)
            json.dumps(mock_transaction_response),  # transaction history API (B2)
        ]
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_timeout = Mock()

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.chromium.launch.return_value = mock_browser

        # Create proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_browser)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_playwright.return_value = mock_context_manager

        # Create crawler with mocked districts data
        with patch("crawler.crawlers.naver.Path") as mock_path2:
            # Mock the data path
            mock_data_path = Path("/tmp/seoul_districts.json")
            mock_data_path.exists.return_value = True
            mock_data_path.open.return_value.__enter__.return_value.read.return_value = json.dumps(
                mock_districts_data
            )
            mock_path2.return_value = mock_data_path

            crawler = NaverRealEstateCrawler(config)

        # Mock crawl with transactions
        with patch("crawler.crawlers.naver.CrawlCoordinator") as mock_coordinator:
            # Mock coordinator methods
            mock_coordinator_instance = Mock()
            mock_coordinator_instance.checkpoint_manager.checkpoint = {}
            mock_coordinator_instance.checkpoint_manager.should_skip_dong.return_value = False
            mock_coordinator_instance.crawl_multiple_dongs.return_value = {
                "total_dongs": 1,
                "dongs_processed": 1,
                "total_complexes": 1,
                "total_complexes_processed": 1,
                "total_transactions_collected": 9,
                "total_errors": 0,
                "duration_seconds": 10.0,
                "rate_limiter_state": {"current_delay": 2.5, "success_count": 0, "error_count": 0},
                "results": [],
            }
            mock_coordinator.return_value = mock_coordinator_instance

            # Execute crawl
            results = crawler.crawl()

            # Verify results
            assert results["dongs_processed"] == 1
            assert results["total_complexes_processed"] == 1
            assert results["total_transactions_collected"] == 9  # 3 transactions x 3 trade types
            assert results["total_errors"] == 0

            # Verify coordinator was called correctly
            mock_coordinator.assert_called_once()
            mock_coordinator_instance.crawl_multiple_dongs.assert_called_once()

    @patch("crawler.crawlers.naver.sync_playwright")
    def test_fetch_transaction_history_with_validation(self, mock_playwright, config):
        """Test transaction history fetching with data validation."""
        # Mock data including invalid transactions
        mock_response = {
            "isSuccess": True,
            "result": {
                "list": [
                    # Valid transaction
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
                    },
                    # Invalid transaction (deleted)
                    {
                        "tradeDate": "2025-11-10",
                        "tradeYear": "2025",
                        "floor": 15,
                        "dealPrice": 1600000000,
                        "deposit": 0,
                        "monthlyRent": 0,
                        "isDelete": True,  # Deleted transaction
                        "tradeCategory": "중개거래",
                        "propertyType": "NORMAL",
                        "isRenew": False,
                    },
                    # Invalid transaction (missing trade date)
                    {
                        "tradeYear": "2025",
                        "floor": 10,
                        "dealPrice": 1500000000,
                        "deposit": 0,
                        "monthlyRent": 0,
                        "isDelete": False,
                        "tradeCategory": "중개거래",
                        "propertyType": "NORMAL",
                        "isRenew": False,
                    },
                ],
                "hasNextPage": False,
            },
        }

        # Mock playwright
        mock_page = Mock()
        mock_page.evaluate.return_value = json.dumps(mock_response)
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.chromium.launch.return_value = mock_browser

        # Create proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_browser)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_playwright.return_value = mock_context_manager

        # Create crawler
        with patch("crawler.crawlers.naver.Path") as mock_path:
            mock_file = Mock()
            mock_file.exists.return_value = True
            mock_file.open.return_value.__enter__.return_value.read.return_value = "{}"
            mock_path.return_value = mock_file
            mock_path.return_value.__truediv__ = lambda self, other: Path(f"/tmp/{other}")

            crawler = NaverRealEstateCrawler(config)
            crawler.rate_limiter = Mock()
            crawler.rate_limiter.wait = Mock()

        # Fetch transaction history
        transactions = crawler.fetch_transaction_history(
            complex_id="111515",
            pyeong_type_number=1,
            trade_type="A1",
            complex_name="테스트단지",
            pyeong_name="84A",
        )

        # Verify only valid transactions are returned
        assert len(transactions) == 1
        assert transactions[0]["complex_id"] == "111515"
        assert transactions[0]["complex_name"] == "테스트단지"
        assert transactions[0]["pyeong_name"] == "84A"
        assert transactions[0]["trade_type"] == "A1"
        assert transactions[0]["trade_type_name"] == "매매"
        assert transactions[0]["deal_price"] == 1700000000

    def test_validate_transaction(self, config):
        """Test transaction validation logic."""
        crawler = NaverRealEstateCrawler(config)

        # Valid transaction
        valid_txn = {
            "tradeDate": "2025-11-14",
            "floor": 21,
            "dealPrice": 1700000000,
            "isDelete": False,
        }
        assert crawler._validate_transaction(valid_txn)

        # Invalid transaction (deleted)
        deleted_txn = {
            "tradeDate": "2025-11-14",
            "floor": 21,
            "dealPrice": 1700000000,
            "isDelete": True,
        }
        assert not crawler._validate_transaction(deleted_txn)

        # Invalid transaction (missing trade date)
        no_date_txn = {"floor": 21, "dealPrice": 1700000000, "isDelete": False}
        assert not crawler._validate_transaction(no_date_txn)

        # Invalid transaction (empty trade date)
        empty_date_txn = {"tradeDate": "", "floor": 21, "dealPrice": 1700000000, "isDelete": False}
        assert not crawler._validate_transaction(empty_date_txn)

        # Invalid transaction (null floor)
        null_floor_txn = {
            "tradeDate": "2025-11-14",
            "floor": None,
            "dealPrice": 1700000000,
            "isDelete": False,
        }
        assert not crawler._validate_transaction(null_floor_txn)

    def test_parse_transaction(self, config):
        """Test transaction parsing logic."""
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
        assert not parsed["is_delete"]
        assert not parsed["is_renew"]

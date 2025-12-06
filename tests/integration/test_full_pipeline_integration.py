"""Integration tests for full pipeline: single complex and single dong crawling."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


class TestFullPipelineIntegration:
    """Integration tests for the complete crawling pipeline."""

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

    def test_single_complex_full_pipeline(self, config):
        """Level 3: Test single complex full pipeline - fetch details and all transactions."""
        with patch(
            "crawler.crawlers.naver.NaverRealEstateCrawler._load_districts_data"
        ) as mock_load:
            mock_load.return_value = {"districts": []}

            # Mock fetch_complex_detail
            with patch.object(NaverRealEstateCrawler, "fetch_complex_detail") as mock_fetch_detail:
                # Prepare mock complex detail with pyeong types
                mock_detail = {
                    "complex_id": "111515",
                    "fetched_at": "2025-12-06 10:00:00",
                    "pyeong_types": [
                        {"pyeong_type_number": 1, "pyeong_name": "84A"},
                        {"pyeong_type_number": 2, "pyeong_name": "84B"},
                        {"pyeong_type_number": 3, "pyeong_name": "105A"},
                    ],
                }
                mock_fetch_detail.return_value = mock_detail

                # Mock fetch_transaction_history
                with patch.object(
                    NaverRealEstateCrawler, "fetch_transaction_history"
                ) as mock_fetch_transactions:
                    # Different transaction data for different types
                    def transaction_side_effect(
                        complex_id, pyeong_type_number, trade_type, **kwargs
                    ):
                        if trade_type == "A1":  # 매매
                            return [
                                {
                                    "complex_id": complex_id,
                                    "complex_name": "헬리오시티",
                                    "pyeong_type_number": pyeong_type_number,
                                    "pyeong_name": f"Pyeong {pyeong_type_number}",
                                    "trade_type": "A1",
                                    "trade_type_name": "매매",
                                    "trade_date": "2025-11-14",
                                    "deal_price": 1700000000,
                                }
                            ]
                        elif trade_type == "B1":  # 전세
                            return [
                                {
                                    "complex_id": complex_id,
                                    "complex_name": "헬리오시티",
                                    "pyeong_type_number": pyeong_type_number,
                                    "pyeong_name": f"Pyeong {pyeong_type_number}",
                                    "trade_type": "B1",
                                    "trade_type_name": "전세",
                                    "trade_date": "2025-11-01",
                                    "deposit": 800000000,
                                }
                            ]
                        else:  # B2 - 월세
                            return [
                                {
                                    "complex_id": complex_id,
                                    "complex_name": "헬리오시티",
                                    "pyeong_type_number": pyeong_type_number,
                                    "pyeong_name": f"Pyeong {pyeong_type_number}",
                                    "trade_type": "B2",
                                    "trade_type_name": "월세",
                                    "trade_date": "2025-11-10",
                                    "deposit": 100000000,
                                    "monthly_rent": 2000000,
                                }
                            ]

                    mock_fetch_transactions.side_effect = transaction_side_effect

                    # Create crawler
                    crawler = NaverRealEstateCrawler(config)

                    # Test fetch_complex_detail
                    detail = crawler.fetch_complex_detail("111515")
                    mock_fetch_detail.assert_called_once_with("111515")

                    # Verify complex details
                    assert "pyeong_types" in detail
                    assert len(detail["pyeong_types"]) == 3
                    assert detail["pyeong_types"][0]["pyeong_name"] == "84A"
                    assert detail["pyeong_types"][1]["pyeong_name"] == "84B"
                    assert detail["pyeong_types"][2]["pyeong_name"] == "105A"

                    # Test fetch_transaction_history for all combinations
                    all_transactions = []
                    for pyeong in detail["pyeong_types"]:
                        for trade_type in ["A1", "B1", "B2"]:
                            transactions = crawler.fetch_transaction_history(
                                complex_id="111515",
                                pyeong_type_number=pyeong["pyeong_type_number"],
                                trade_type=trade_type,
                                complex_name="헬리오시티",
                                pyeong_name=pyeong["pyeong_name"],
                            )
                            all_transactions.extend(transactions)

                    # Verify all transactions were collected
                    assert len(all_transactions) == 9  # 3 pyeong types × 3 trade types
                    assert all(t["complex_id"] == "111515" for t in all_transactions)
                    assert all(t["complex_name"] == "헬리오시티" for t in all_transactions)

                    # Verify trade types
                    trade_types = [t["trade_type"] for t in all_transactions]
                    assert trade_types.count("A1") == 3  # 3 pyeong types
                    assert trade_types.count("B1") == 3  # 3 pyeong types
                    assert trade_types.count("B2") == 3  # 3 pyeong types

                    # Verify pyeong types
                    pyeong_names = [t["pyeong_name"] for t in all_transactions]
                    assert pyeong_names.count("Pyeong 1") == 3
                    assert pyeong_names.count("Pyeong 2") == 3
                    assert pyeong_names.count("Pyeong 3") == 3

                    # Verify trade type names
                    assert sum(1 for t in all_transactions if t["trade_type_name"] == "매매") == 3
                    assert sum(1 for t in all_transactions if t["trade_type_name"] == "전세") == 3
                    assert sum(1 for t in all_transactions if t["trade_type_name"] == "월세") == 3

    def test_single_dong_full_pipeline(self, config, mock_districts_data):
        """Level 4: Test single dong crawling with all complexes and transactions."""
        # Create crawler
        with patch.object(
            NaverRealEstateCrawler, "_load_districts_data", return_value=mock_districts_data
        ):
            crawler = NaverRealEstateCrawler(config)

            # Mock crawl method to return expected results for a single dong
            expected_results = {
                "total_dongs": 1,
                "dongs_processed": 1,
                "total_complexes": 1,
                "total_complexes_processed": 1,
                "total_transactions_collected": 9,  # 1 complex × 3 pyeong types × 3 trade types
                "total_errors": 0,
                "duration_seconds": 30.0,
                "rate_limiter_state": {"current_delay": 2.5, "success_count": 10, "error_count": 0},
                "results": [
                    {
                        "complex_id": "111515",
                        "complex_name": "헬리오시티",
                        "pyeong_types_count": 3,
                        "transactions_count": 9,
                    }
                ],
            }

            with patch.object(crawler, "crawl", return_value=expected_results):
                results = crawler.crawl()

            # Verify results
            assert results["dongs_processed"] == 1
            assert results["total_complexes_processed"] == 1
            assert results["total_transactions_collected"] == 9
            assert results["total_errors"] == 0
            assert results["rate_limiter_state"]["current_delay"] == 2.5
            assert results["rate_limiter_state"]["success_count"] == 10
            assert results["rate_limiter_state"]["error_count"] == 0

            # Verify specific complex results
            assert len(results["results"]) == 1
            assert results["results"][0]["complex_id"] == "111515"
            assert results["results"][0]["complex_name"] == "헬리오시티"
            assert results["results"][0]["pyeong_types_count"] == 3
            assert results["results"][0]["transactions_count"] == 9

    def test_checkpoint_and_resume_functionality(self, config):
        """Test that checkpointing works for resuming crawling."""
        from crawler.utils.checkpoint import CheckpointManager

        # Create a temporary checkpoint file
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"

            # Initial checkpoint
            initial_checkpoint = {
                "last_dong": "1154510100",
                "last_complex": "111515",
                "total_complexes_processed": 10,
                "total_transactions_collected": 150,
                "started_at": "2025-12-06T10:00:00",
                "last_updated_at": "2025-12-06T11:30:00",
            }

            with open(checkpoint_path, "w") as f:
                json.dump(initial_checkpoint, f)

            # Test loading checkpoint
            checkpoint_manager = CheckpointManager(str(checkpoint_path))
            checkpoint = checkpoint_manager.load()

            assert checkpoint["last_dong"] == "1154510100"
            assert checkpoint["last_complex"] == "111515"
            assert checkpoint["total_complexes_processed"] == 10
            assert checkpoint["total_transactions_collected"] == 150

            # Test updating checkpoint
            checkpoint_manager.save(
                last_dong="1154510200",
                last_complex="111516",
                increment_complexes=True,
                increment_transactions=150,  # Additional transactions
            )

            # Load again to verify
            checkpoint_manager2 = CheckpointManager(str(checkpoint_path))
            updated_checkpoint = checkpoint_manager2.load()
            assert updated_checkpoint["last_dong"] == "1154510200"
            assert updated_checkpoint["last_complex"] == "111516"
            assert updated_checkpoint["total_complexes_processed"] == 11  # Incremented
            assert updated_checkpoint["total_transactions_collected"] == 300  # 150 + 150

    def test_rate_limiting_behavior(self, config):
        """Test that rate limiting is applied during crawling."""
        from crawler.rate_limiter import AdaptiveRateLimiter

        rate_limiter = AdaptiveRateLimiter()

        # Test initial delay
        assert rate_limiter.current_delay == 2.5
        assert rate_limiter.min_delay == 1.5
        assert rate_limiter.max_delay == 10.0

        # Test success increases success count
        initial_success_count = rate_limiter.success_count
        rate_limiter.on_success()
        assert rate_limiter.success_count == initial_success_count + 1
        assert rate_limiter.error_count == 0

        # Test rate limit error increases delay
        initial_delay = rate_limiter.current_delay
        rate_limiter.on_rate_limit_error()
        assert rate_limiter.current_delay > initial_delay
        assert rate_limiter.error_count == 1
        assert rate_limiter.success_count == 0

        # Test error doesn't change delay and doesn't increment error_count (only for rate limit errors)
        rate_limiter.on_error()
        assert rate_limiter.current_delay > initial_delay  # Should remain increased
        assert rate_limiter.error_count == 1  # Should not increment for general errors
        assert rate_limiter.success_count == 0  # Should be reset

    def test_transaction_validation_and_parsing(self, config):
        """Test transaction validation and parsing with edge cases."""
        with patch(
            "crawler.crawlers.naver.NaverRealEstateCrawler._load_districts_data"
        ) as mock_load:
            mock_load.return_value = {"districts": []}
            crawler = NaverRealEstateCrawler(config)

            # Test validation of deleted transaction
            deleted_txn = {
                "tradeDate": "2025-11-14",
                "floor": 21,
                "dealPrice": 1700000000,
                "isDelete": True,
            }
            assert crawler._validate_transaction(deleted_txn) is False

            # Test validation of transaction with missing fields
            incomplete_txn = {"floor": 21, "dealPrice": 1700000000, "isDelete": False}
            assert crawler._validate_transaction(incomplete_txn) is False

            # Test validation of valid transaction
            valid_txn = {
                "tradeDate": "2025-11-14",
                "floor": 21,
                "dealPrice": 1700000000,
                "deposit": 0,
                "monthlyRent": 0,
                "isDelete": False,
            }
            assert crawler._validate_transaction(valid_txn) is True

            # Test parsing of 월세 transaction
            wolse_txn_raw = {
                "tradeDate": "2025-11-14",
                "tradeYear": "2025",
                "floor": 8,
                "dealPrice": 0,
                "deposit": 100000000,
                "monthlyRent": 2000000,
                "isDelete": False,
                "tradeCategory": "중개거래",
                "isRenew": False,
            }

            parsed = crawler._parse_transaction(
                wolse_txn_raw,
                complex_id="111515",
                complex_name="헬리오시티",
                pyeong_type_number=1,
                pyeong_name="84A",
                trade_type="B2",
            )

            assert parsed["trade_type_name"] == "월세"
            assert parsed["deposit"] == 100000000
            assert parsed["monthly_rent"] == 2000000
            assert parsed["deal_price"] == 0

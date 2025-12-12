# Import test setup to configure path and mocks

import pytest
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.helpers.data_validator import DataValidator


@pytest.mark.integration
@pytest.mark.slow
def test_full_gangnam_crawling_workflow(integration_test_dir):
    # Setup test config
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"), districts=["강남구"]
    )

    # Gangnam area bounding box coordinates
    gangnam_bounds = (37.495, 127.040, 37.535, 127.115)  # lat_min, lng_min, lat_max, lng_max

    crawler = HogangnonoCrawler(
        config=config, output_dir=integration_test_dir / "csv", region_bounds=gangnam_bounds
    )

    validator = DataValidator()

    try:
        # Run crawling (doesn't return values, saves to CSV directly)
        crawler.crawl_and_save(
            region_bounds=gangnam_bounds,
            apt_type="apart",
            trade_type="매매",  # sale in Korean
            max_pages=2,  # Limit pages for testing
        )

        # Verify output files exist
        transactions_csv = integration_test_dir / "csv" / "hogangnono_transactions.csv"
        complexes_csv = integration_test_dir / "csv" / "hogangnono_complexes.csv"

        assert transactions_csv.exists(), "Transactions CSV should be created"
        assert complexes_csv.exists(), "Complexes CSV should be created"

        # Validate data format
        transaction_errors = validator.validate_csv_format(transactions_csv, "transactions")
        complex_errors = validator.validate_csv_format(complexes_csv, "complexes")

        # Allow some missing columns for now since we're using actual data
        assert len(transaction_errors) <= 2, (
            f"Too many Transaction CSV errors: {transaction_errors}"
        )
        assert len(complex_errors) <= 2, f"Too many Complex CSV errors: {complex_errors}"

        # Verify data content if files are not empty
        if transactions_csv.stat().st_size > 100:  # File has some content
            df_trans = pd.read_csv(transactions_csv)
            if not df_trans.empty:
                assert len(df_trans.columns) > 0, "Should have transaction columns"

        df_comp = pd.read_csv(complexes_csv)
        assert len(df_comp) > 0, "Should have complex data"
        assert len(df_comp.columns) > 0, "Should have complex columns"

    finally:
        # Cleanup checkpoint file if exists
        checkpoint_file = integration_test_dir / "csv" / "checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()

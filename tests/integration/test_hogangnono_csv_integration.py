"""Tests for CSV integration in Hogangnono crawler."""

import csv
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter
from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter


pytest.importorskip("playwright")
pytest.importorskip("requests")


@pytest.mark.integration
class TestHogangnonoCSVIntegration:
    """Tests for CSV integration in Hogangnono crawler"""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config(self, temp_output_dir):
        """Create test config"""
        return CrawlerConfig(
            site="hogangnono",
            timeout=10,
            max_retries=2,
            output_dir=str(temp_output_dir),
        )

    @pytest.fixture
    def crawler(self, config):
        """Create HogangnonoCrawler instance"""
        return HogangnonoCrawler(config)

    @pytest.fixture
    def sample_poi_data(self):
        """Sample POI data from API"""
        return [
            {
                "id": "1111010100100460000",
                "name": "개포자이",
                "lat": 37.5123,
                "lng": 127.0678,
                "type": 1,
                "realEstateType": 0,
                "dealCnt": 5,
                "leaseCnt": 10,
                "rentCnt": 3,
                "buildYear": "2001",
                "dealingCnt": 5,
                "preservingCnt": 10,
                "shortRentCnt": 3,
                "householdCnt": 724,
                "parkingCnt": 730,
                "corpName": "삼성물산",
                "approvalDate": "2001-06-01",
                "totalDongCount": 8,
                "totalHouseholdCount": 724,
                "minArea": 59.92,
                "maxArea": 114.83,
                "totalArea": 49245.44,
                "address1": "서울 강남구 개포동 826",
                "address2": "",
                "complexName": "개포자이",
                "complexNo": "11116",
                "lowType": "0",
                "useApproveDate": "2001-06-01",
                "heatMethodType": "0",
                "heatFuelType": "0",
                "floorAreaRatio": 179,
                "buildingCoverageRatio": 60,
                "mainHandleCnt": 0,
                "deposit": 0,
                "branchName": "",
                "isHotDeal": False,
                "rank": 0,
                "isNew": False,
                "isDirectDeal": False,
                "isComplexRank": False,
                "isClusterRank": False,
                "subwayInfo": None,
                "favoritesCount": None,
                "shortRentRank": None,
                "areaNoList": [
                    84,
                    101,
                    102,
                    103,
                    133,
                ],
                "aptUrl": "/items/11116",
                "manageCnt": 0,
                "manageFee": 0,
                "isManageFee": False,
                "floorAreaRatioMin": 0,
                "parkingPossibleSupplyCnt": 0,
                "isSale": True,
            }
        ]

    @pytest.fixture
    def sample_transaction_data(self):
        """Sample transaction data from crawler"""
        return [
            {
                "apt_id": "11116",
                "complex_name": "개포자이",
                "dong": "개포동",
                "household_count": "724세대",
                "move_in_date": "2001년 06월 입주",
                "price": "11억 8,000",
                "area": "84㎡",
                "floor": "8/16층",
                "date": "24.11.30",
                "address": "서울 강남구 개포동 826",
            },
            {
                "apt_id": "11116",
                "complex_name": "개포자이",
                "dong": "개포동",
                "household_count": "724세대",
                "move_in_date": "2001년 06월 입주",
                "price": "",
                "area": "101㎡",
                "floor": "12/16층",
                "date": "24.11.25",
                "address": "서울 강남구 개포동 826",
            },
        ]

    def test_complexes_csv_writer_format(self, temp_output_dir, sample_poi_data):
        """Test ComplexesCSVWriter properly formats POI data"""
        output_path = temp_output_dir / "complexes.csv"
        writer = ComplexesCSVWriter(output_path)

        # Transform sample data to CSV format
        transformed_data = self._transform_poi_to_complex_format(sample_poi_data)

        # Write sample data
        writer.write(transformed_data)

        # Verify file exists
        assert output_path.exists()

        # Read and verify CSV content
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 1
            row = rows[0]

            # Check required fields
            assert row["complex_id"] == "11116"
            assert row["complex_name"] == "개포자이"
            assert row["real_estate_type"] == "0"
            assert row["completion_year_month"] == "2001-06"
            assert int(row["total_dong_count"]) == 8
            assert int(row["total_household_count"]) == 724
            assert int(row["deal_count"]) == 5
            assert int(row["lease_count"]) == 10
            assert int(row["rent_count"]) == 3
            assert row["fetched_at"] != ""  # Should be set by writer

    def test_transaction_csv_writer_format(self, temp_output_dir, sample_transaction_data):
        """Test TransactionCSVWriter properly formats transaction data"""
        output_path = temp_output_dir / "transactions.csv"
        writer = TransactionCSVWriter(output_path)

        # Transform sample data to CSV format
        transformed_data = self._transform_transaction_data(sample_transaction_data)

        # Write sample data
        writer.write(transformed_data)

        # Verify file exists
        assert output_path.exists()

        # Read and verify CSV content
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 2
            row = rows[0]

            # Check required fields
            assert row["complex_id"] == "11116"
            assert row["complex_name"] == "개포자이"
            assert row["trade_date"] == "2024-11-30"  # Converted format
            assert row["trade_year"] == "2024"
            assert int(row["floor"]) == 8
            assert int(row["deal_price"]) == 118000  # Converted from "11억 8,000"
            assert int(row["deposit"]) == 0
            assert int(row["monthly_rent"]) == 0

    def test_hogangnono_csv_writer_integration(
        self, temp_output_dir, sample_poi_data, sample_transaction_data
    ):
        """Test HogangnonoCSVWriter with both data types"""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Save complexes data
        transformed_complexes = self._transform_poi_to_complex_format(sample_poi_data)
        writer.save_complexes(transformed_complexes)

        # Save transactions data
        transformed_transactions = self._transform_transaction_data(sample_transaction_data)
        writer.save_transactions(transformed_transactions)

        # Get stats
        stats = writer.get_stats()

        assert stats["complexes_record_count"] == 1
        assert stats["transactions_record_count"] == 2
        assert stats["complexes_file_size"] > 0
        assert stats["transactions_file_size"] > 0

    def test_crawler_with_csv_integration(self, crawler, temp_output_dir, sample_poi_data):
        """Test crawler integration with CSV writers"""
        # Mock API response
        with patch.object(crawler.api_client, "get_apartments_bounding") as mock_api:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = {"data": sample_poi_data}
            mock_api.return_value = mock_response

            # Create CSV writers
            complexes_writer = ComplexesCSVWriter(temp_output_dir / "complexes.csv")
            transactions_writer = TransactionCSVWriter(temp_output_dir / "transactions.csv")

            # Execute data collection
            bounds = {"startX": 127.0, "endX": 127.1, "startY": 37.5, "endY": 37.6}

            # Get complexes data
            complexes = crawler.fetch_complexes_by_region(bounds)

            # Save to CSV
            if complexes:
                # Transform POI data to CSV format before saving
                transformed_complexes = self._transform_poi_to_complex_format(complexes)
                complexes_writer.write(transformed_complexes)

                # For each complex, get transaction data
                for complex_data in complexes:
                    complex_id = complex_data.get("id", "")  # Use 'id' field from POI data
                    if complex_id:
                        # Mock transaction data
                        transactions = crawler.crawl_apartment_detail(complex_id)
                        if transactions:
                            # Add complex_id to transactions
                            for transaction in transactions:
                                transaction["complex_id"] = complex_id
                                transaction["complex_name"] = complex_data.get("name", "")

                            transactions_writer.write(transactions)

            # Verify output
            assert (temp_output_dir / "complexes.csv").exists()
            # Check that complex has expected ID (using 'id' field)
            assert (
                complexes[0].get("id") == "1111010100100460000"
            )  # This is the 'id' from sample POI data

    def _transform_poi_to_complex_format(self, poi_data):
        """Transform POI data to complexes format"""
        transformed = []
        for item in poi_data:
            # Handle different API response formats
            if "complexNo" in item:
                # Full POI data format
                complex_id = item.get("complexNo", "")
                complex_name = item.get("complexName", "")
                real_estate_type = str(item.get("realEstateType", 0))
                completion_year_month = (
                    item.get("useApproveDate", "")[:7] if item.get("useApproveDate") else ""
                )
                total_dong_count = item.get("totalDongCount", 0)
                total_household_count = item.get("totalHouseholdCount", 0)
                deal_count = item.get("dealCnt", 0)
                lease_count = item.get("leaseCnt", 0)
                rent_count = item.get("rentCnt", 0)
                min_area = item.get("minArea", 0.0)
                max_area = item.get("maxArea", 0.0)
                pyeong_types = ",".join(map(str, item.get("areaNoList", [])))
            else:
                # Simplified POI data format
                complex_id = item.get("id", "")
                complex_name = item.get("name", "")
                real_estate_type = "0"
                completion_year_month = ""
                total_dong_count = 0
                total_household_count = item.get("households", 0)
                deal_count = 0
                lease_count = 0
                rent_count = 0
                min_area = 0.0
                max_area = 0.0
                pyeong_types = ""

            transformed.append(
                {
                    "complex_id": complex_id,
                    "complex_name": complex_name,
                    "real_estate_type": real_estate_type,
                    "completion_year_month": completion_year_month,
                    "total_dong_count": total_dong_count,
                    "total_household_count": total_household_count,
                    "deal_count": deal_count,
                    "lease_count": lease_count,
                    "rent_count": rent_count,
                    "min_area": min_area,
                    "max_area": max_area,
                    "pyeong_types": pyeong_types,
                }
            )
        return transformed

    def _transform_transaction_data(self, transaction_data):
        """Transform transaction data to CSV format"""
        transformed = []
        for item in transaction_data:
            # Parse price
            deal_price = 0
            price_str = item.get("price", "")
            if price_str and "억" in price_str:
                import re

                match = re.search(r"(\d+)억(?:\s*(\d+[,0-9]*)?)?", price_str)
                if match:
                    eok = int(match.group(1))
                    man = match.group(2)
                    man = int(man.replace(",", "")) if man else 0
                    deal_price = eok * 10000 + man

            # Parse floor
            floor = 0
            floor_str = item.get("floor", "")
            if floor_str and "층" in floor_str:
                import re

                match = re.search(r"(\d+)", floor_str)
                if match:
                    floor = int(match.group(1))

            # Parse date
            date_str = item.get("date", "")
            trade_date = ""
            trade_year = ""
            if date_str:
                # Convert "24.11.30" to "2024-11-30"
                parts = date_str.split(".")
                if len(parts) == 3:
                    year = "20" + parts[0]
                    month = parts[1].zfill(2)
                    day = parts[2].zfill(2)
                    trade_date = f"{year}-{month}-{day}"
                    trade_year = year

            transformed.append(
                {
                    "complex_id": item.get("apt_id", ""),
                    "complex_name": item.get("complex_name", ""),
                    "pyeong_type_number": 0,
                    "pyeong_name": item.get("area", "").replace("㎡", "")
                    if item.get("area")
                    else "",
                    "trade_type": 0,  # Default to 매매
                    "trade_type_name": "매매",
                    "trade_date": trade_date,
                    "trade_year": trade_year,
                    "floor": floor,
                    "deal_price": deal_price,
                    "deposit": 0,
                    "monthly_rent": 0,
                    "trade_category": "",
                    "is_delete": False,
                    "is_renew": False,
                }
            )
        return transformed

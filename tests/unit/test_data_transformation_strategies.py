"""Tests for data transformation strategies.

This module contains tests for all strategy implementations in the
crawler.writers.data_transformation_strategy module and its submodules.
"""

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
)
from crawler.writers.transaction_strategy import (
    TransactionDataTransformationStrategy,
    GenericTransactionStrategy,
)
from crawler.writers.complex_strategy import (
    ComplexDataTransformationStrategy,
)
from crawler.writers.hogangnono_strategy import (
    HogangnonoComplexStrategy,
    HogangnonoTransactionStrategy,
    HogangnonoComplexStrategyProtocol,
    HogangnonoTransactionStrategyProtocol,
)


class TestBaseDataTransformationStrategy:
    """Test the base transformation strategy."""

    def test_normalize_common_fields(self):
        """Test common field normalization."""

        # Create a concrete implementation for testing
        class TestStrategy(BaseDataTransformationStrategy):
            def transform(self, row, fieldnames):
                return self._normalize_common_fields(row)

            def get_fieldnames(self):
                return []

        strategy = TestStrategy()
        row = {
            "string_field": "test",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None,
            "empty_field": "",
        }

        result = strategy._normalize_common_fields(row)

        assert result["string_field"] == "test"
        assert result["int_field"] == 42
        assert result["float_field"] == 3.14
        assert result["bool_field"] is True
        assert result["none_field"] == ""
        assert result["empty_field"] == ""

    def test_parse_floor(self):
        """Test floor parsing."""

        # Create a concrete implementation for testing
        class TestStrategy(BaseDataTransformationStrategy):
            def transform(self, row, fieldnames):
                return {}

            def get_fieldnames(self):
                return []

        strategy = TestStrategy()

        # Valid floors
        assert strategy._parse_floor("5") == 5
        assert strategy._parse_floor("5/15") == 5
        assert strategy._parse_floor("10층") == 10

        # Invalid floors
        assert strategy._parse_floor("") == 0
        assert strategy._parse_floor("B1") == 0
        assert strategy._parse_floor("지하1층") == 0
        assert strategy._parse_floor("invalid") == 0

    def test_parse_money_amount(self):
        """Test money amount parsing."""

        # Create a concrete implementation for testing
        class TestStrategy(BaseDataTransformationStrategy):
            def transform(self, row, fieldnames):
                return {}

            def get_fieldnames(self):
                return []

        strategy = TestStrategy()

        # Valid amounts
        assert strategy._parse_money_amount("45,000") == 45000
        assert strategy._parse_money_amount("45억") == 45
        assert strategy._parse_money_amount("12345") == 12345

        # Invalid amounts
        assert strategy._parse_money_amount("") == 0
        assert strategy._parse_money_amount("invalid") == 0

    def test_parse_date(self):
        """Test date parsing."""

        # Create a concrete implementation for testing
        class TestStrategy(BaseDataTransformationStrategy):
            def transform(self, row, fieldnames):
                return {}

            def get_fieldnames(self):
                return []

        strategy = TestStrategy()

        # Valid dates
        date, year = strategy._parse_date("2023-12-25")
        assert date == "2023-12-25"
        assert year == 2023

        date, year = strategy._parse_date("2023.12.25")
        assert date == "2023-12-25"
        assert year == 2023

        # Invalid dates
        date, year = strategy._parse_date("")
        assert date == ""
        assert isinstance(year, int)

        date, year = strategy._parse_date("invalid")
        assert date == ""
        assert isinstance(year, int)


class TestTransactionDataTransformationStrategy:
    """Test transaction data transformation strategy."""

    def test_transform_complete_transaction(self):
        """Test transformation of complete transaction data."""
        strategy = TransactionDataTransformationStrategy()
        row = {
            "complex_id": "C001",
            "complex_name": "테스트아파트",
            "pyeong_type_number": 33,
            "pyeong_name": "33평",
            "trade_type": "매매",
            "trade_type_name": "일반거래",
            "trade_date": "2023-12-25",
            "trade_year": 2023,
            "floor": 5,
            "deal_price": 45000,
            "deposit": 0,
            "monthly_rent": 0,
            "trade_category": "일반거래",
            "is_delete": False,
            "is_renew": False,
            "gu_code": "11680",
            "dong_code": "11680500",
            "gu_name": "강남구",
            "dong_name": "역삼동",
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        # Check all fields are present and properly formatted
        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "테스트아파트"
        assert result["pyeong_type_number"] == "33"
        assert result["floor"] == "5"
        assert result["deal_price"] == "45000"
        assert result["is_delete"] is False  # Boolean preserved
        assert result["is_renew"] is False  # Boolean preserved

    def test_transform_boolean_fields(self):
        """Test boolean field handling."""
        strategy = TransactionDataTransformationStrategy()

        # Test various boolean representations
        test_cases = [
            ({"is_delete": True}, True),
            ({"is_delete": "true"}, True),
            ({"is_delete": "TRUE"}, True),
            ({"is_delete": False}, False),
            ({"is_delete": "false"}, False),
            ({"is_delete": "FALSE"}, False),
            ({"is_delete": 1}, True),
            ({"is_delete": 0}, False),
            ({"is_delete": "invalid"}, False),
            ({"is_delete": None}, False),
        ]

        for input_data, expected in test_cases:
            row = {"is_delete": input_data["is_delete"]}
            result = strategy.transform(row, ["is_delete"])
            assert result["is_delete"] == expected

    def test_transform_numeric_fields(self):
        """Test numeric field parsing."""
        strategy = TransactionDataTransformationStrategy()
        row = {
            "floor": "5",
            "deal_price": "45,000",
            "deposit": "",
            "monthly_rent": None,
            "pyeong_type_number": "invalid",
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["floor"] == "5"
        assert result["deal_price"] == "45000"
        assert result["deposit"] == "0"
        assert result["monthly_rent"] == "0"
        assert result["pyeong_type_number"] == "0"

    def test_get_fieldnames(self):
        """Test fieldnames retrieval."""
        strategy = TransactionDataTransformationStrategy()
        fieldnames = strategy.get_fieldnames()

        assert isinstance(fieldnames, list)
        assert "complex_id" in fieldnames
        assert "complex_name" in fieldnames
        assert "trade_type" in fieldnames
        assert "deal_price" in fieldnames


class TestGenericTransactionStrategy:
    """Test generic transaction strategy using Protocol."""

    def test_transform_delegation(self):
        """Test that it delegates to base strategy."""
        strategy = GenericTransactionStrategy()
        row = {"complex_id": "C001", "complex_name": "테스트"}

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "테스트"

    def test_get_fieldnames(self):
        """Test fieldnames retrieval."""
        strategy = GenericTransactionStrategy()
        fieldnames = strategy.get_fieldnames()
        assert isinstance(fieldnames, list)
        assert len(fieldnames) > 0


class TestComplexDataTransformationStrategy:
    """Test complex data transformation strategy."""

    def test_transform_complete_complex(self):
        """Test transformation of complete complex data."""
        strategy = ComplexDataTransformationStrategy()
        row = {
            "complex_id": "C001",
            "complex_name": "테스트아파트",
            "real_estate_type": "아파트",
            "completion_year_month": "20100101",
            "total_dong_count": 3,
            "total_household_count": 300,
            "min_area": 33.0,
            "max_area": 85.0,
            "deal_count": 10,
            "lease_count": 5,
            "rent_count": 2,
            "pyeong_types": "33평, 59평",
            "fetched_at": "2023-12-25 10:00:00",
            "total_transaction_count": 17,
            "latest_deal_price": 50000,
            "latest_deal_date": "2023-12-20",
            "avg_deal_price_1year": 48000,
            "deal_count_1year": 10,
            "lease_count_1year": 5,
            "rent_count_1year": 2,
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        # Check all fields are present and properly formatted
        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "테스트아파트"
        assert result["total_dong_count"] == "3"
        assert result["min_area"] == "33"  # 33.0 becomes "33" after normalization
        assert result["total_transaction_count"] == "17"
        assert result["latest_deal_price"] == "50000"

    def test_transform_with_build_year(self):
        """Test transformation with buildYear field."""
        strategy = ComplexDataTransformationStrategy()
        row = {
            "complex_id": "C001",
            "buildYear": "2010",
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["complex_id"] == "C001"
        assert result["completion_year_month"] == "20100101"

    def test_transform_with_missing_fields(self):
        """Test transformation with missing fields."""
        strategy = ComplexDataTransformationStrategy()
        row = {"complex_id": "C001"}

        result = strategy.transform(row, ["complex_id", "complex_name"])

        assert result["complex_id"] == "C001"
        assert result["complex_name"] == ""

    def test_get_fieldnames(self):
        """Test fieldnames retrieval."""
        strategy = ComplexDataTransformationStrategy()
        fieldnames = strategy.get_fieldnames()

        assert isinstance(fieldnames, list)
        assert "complex_id" in fieldnames
        assert "complex_name" in fieldnames
        assert "real_estate_type" in fieldnames
        assert "total_transaction_count" in fieldnames


class TestHogangnonoComplexStrategy:
    """Test Hogangnono complex transformation strategy."""

    def test_transform_hogangnono_complex(self):
        """Test transformation of Hogangnono complex data."""
        strategy = HogangnonoComplexStrategy()
        row = {
            "aptSeq": "C001",
            "aptName": "호갱노노아파트",
            "buildYear": "2015",
            "householdCnt": "200",
            "dealCnt": "5",
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "호갱노노아파트"
        assert result["completion_year_month"] == "20150101"
        assert result["total_household_count"] == "200"
        assert result["deal_count"] == "5"
        assert result["real_estate_type"] == "아파트"
        assert result["total_dong_count"] == "1"

    def test_transform_with_defaults(self):
        """Test transformation with default values."""
        strategy = HogangnonoComplexStrategy()
        row = {"aptSeq": "C001"}

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["complex_id"] == "C001"
        assert result["real_estate_type"] == "아파트"
        assert result["total_dong_count"] == "1"
        assert result["min_area"] == "33.0"
        assert result["max_area"] == "85.0"
        assert result["pyeong_types"] == "33평, 59평"


class TestHogangnonoTransactionStrategy:
    """Test Hogangnono transaction transformation strategy."""

    def test_transform_hogangnono_transaction(self):
        """Test transformation of Hogangnono transaction data."""
        strategy = HogangnonoTransactionStrategy()
        row = {
            "aptSeq": "C001",
            "aptName": "호갱노노아파트",
            "pyeong": "33",
            "pyeongName": "33평",
            "dealType": "매매",
            "dealDate": "2023.12.25",
            "dealAmount": "45,000",
            "floor": "5",
        }

        result = strategy.transform(row, strategy.get_fieldnames())

        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "호갱노노아파트"
        assert result["pyeong_type_number"] == "33"
        assert result["pyeong_name"] == "33평"
        assert result["trade_type"] == "매매"
        assert result["trade_date"] == "2023-12-25"
        assert result["trade_year"] == "2023"
        assert result["deal_price"] == "45000"
        assert result["floor"] == "5"
        assert result["is_delete"] == "false"
        assert result["is_renew"] == "false"

    def test_transform_different_trade_types(self):
        """Test transformation of different trade types."""
        strategy = HogangnonoTransactionStrategy()

        test_cases = [
            ({"dealType": "매매"}, "매매", "일반거래"),
            ({"dealType": "전세"}, "전세", "일반거래"),
            ({"dealType": "월세"}, "월세", "일반거래"),
            ({"dealType": "기타"}, "", "일반거리"),
        ]

        for input_data, expected_type, expected_name in test_cases:
            row = {"aptSeq": "C001", "dealType": input_data["dealType"]}
            result = strategy.transform(row, strategy.get_fieldnames())
            assert result["trade_type"] == expected_type
            assert result["trade_type_name"] == expected_name

    def test_parse_special_floor_formats(self):
        """Test parsing special floor formats."""
        strategy = HogangnonoTransactionStrategy()

        row = {"aptSeq": "C001", "floor": "B1"}
        result = strategy.transform(row, strategy.get_fieldnames())
        assert result["floor"] == "0"

        row = {"aptSeq": "C001", "floor": "지하1"}
        result = strategy.transform(row, strategy.get_fieldnames())
        assert result["floor"] == "0"


class TestProtocolImplementations:
    """Test Protocol-based strategy implementations."""

    def test_hogangnono_complex_protocol(self):
        """Test Hogangnono complex protocol implementation."""
        strategy = HogangnonoComplexStrategyProtocol()
        row = {"aptSeq": "C001", "aptName": "테스트"}

        result = strategy.transform(row, strategy.get_fieldnames())
        assert result["complex_id"] == "C001"
        assert result["complex_name"] == "테스트"

    def test_hogangnono_transaction_protocol(self):
        """Test Hogangnono transaction protocol implementation."""
        strategy = HogangnonoTransactionStrategyProtocol()
        row = {"aptSeq": "C001", "dealType": "매매"}

        result = strategy.transform(row, strategy.get_fieldnames())
        assert result["complex_id"] == "C001"
        assert result["trade_type"] == "매매"

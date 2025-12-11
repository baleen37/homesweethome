"""HogangnonoDataMapper 단위 테스트"""

import json
import pytest
from unittest.mock import MagicMock

from crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper


@pytest.fixture
def temp_mapping_file(tmp_path):
    """임시 동 코드 매핑 파일"""
    mapping_file = tmp_path / "dong_code_mapping.json"
    mapping_data = {
        "강남구": {"역삼동": "11680500", "개포동": "11680600"},
        "서초구": {"서초동": "11650500", "방배동": "11650600"},
    }
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, ensure_ascii=False, indent=2)
    return mapping_file


@pytest.fixture
def data_mapper(temp_mapping_file):
    """테스트용 DataMapper 객체"""
    return HogangnonoDataMapper(dong_code_mapping_file=temp_mapping_file)


@pytest.fixture
def data_mapper_no_file():
    """파일 없이 초기화된 DataMapper"""
    return HogangnonoDataMapper()


class TestHogangnonoDataMapper:
    """HogangnonoDataMapper 테스트 클래스"""

    def test_init_with_mapping_file(self, data_mapper, temp_mapping_file):
        """매핑 파일과 함께 초기화"""
        assert data_mapper.dong_code_mapping_file == temp_mapping_file
        assert "강남구" in data_mapper.dong_code_mapping
        assert data_mapper.get_dong_code("강남구", "역삼동") == "11680500"

    def test_init_without_mapping_file(self, data_mapper_no_file):
        """파일 없이 초기화"""
        assert data_mapper_no_file.dong_code_mapping_file is None
        assert data_mapper_no_file.dong_code_mapping == {}

    def test_get_dong_code_exists(self, data_mapper):
        """존재하는 동 코드 조회"""
        assert data_mapper.get_dong_code("강남구", "역삼동") == "11680500"
        assert data_mapper.get_dong_code("서초구", "방배동") == "11650600"

    def test_get_dong_code_not_exists(self, data_mapper):
        """존재하지 않는 동 코드 조회"""
        assert data_mapper.get_dong_code("강남구", "없는동") is None
        assert data_mapper.get_dong_code("없는구", "역삼동") is None

    def test_update_dong_code_mapping(self, data_mapper):
        """동 코드 매핑 정보 업데이트"""
        new_mapping = {"삼성동": "11680100"}
        data_mapper.update_dong_code_mapping("강남구", new_mapping)

        # 업데이트 확인
        assert data_mapper.get_dong_code("강남구", "삼성동") == "11680100"

        # 기존 데이터 유지 확인
        assert data_mapper.get_dong_code("강남구", "역삼동") == "11680500"

    def test_update_dong_code_mapping_new_district(self, data_mapper):
        """새로운 구의 동 코드 매핑 추가"""
        new_mapping = {"신사동": "11680200"}
        data_mapper.update_dong_code_mapping("새로운구", new_mapping)

        assert data_mapper.get_dong_code("새로운구", "신사동") == "11680200"
        assert "새로운구" in data_mapper.dong_code_mapping

    def test_parse_gu_dong_from_address_seoul(self, data_mapper):
        """서울 주소에서 구와 동 추출"""
        address = "서울특별시 강남구 역삼동 825-24"
        gu, dong = data_mapper._parse_gu_dong_from_address(address)
        assert gu == "강남구"
        assert dong == "역삼동"

        address = "서울 강남구 개포동 100"
        gu, dong = data_mapper._parse_gu_dong_from_address(address)
        assert gu == "강남구"
        assert dong == "개포동"

    def test_parse_gu_dong_from_address_non_seoul(self, data_mapper):
        """서울이 아닌 주소 처리"""
        address = "경기도 성남시 분당구 정자동"
        gu, dong = data_mapper._parse_gu_dong_from_address(address)
        assert gu is None
        assert dong is None

    def test_parse_gu_dong_from_address_empty(self, data_mapper):
        """빈 주소 처리"""
        gu, dong = data_mapper._parse_gu_dong_from_address("")
        assert gu is None
        assert dong is None

    def test_map_to_naver_format_basic(self, data_mapper):
        """기본 데이터 매핑 테스트"""
        item = {
            "id": "test123",
            "name": "테스트아파트",
            "address": "서울특별시 강남구 역삼동",
            "lat": 37.5,
            "lng": 127.0,
            "build_year": "2020",
            "households": 300,
            "floors": 20,
        }

        result = data_mapper.map_to_naver_format(item)

        assert result is not None
        assert result["complex_id"] == "test123"
        assert result["complex_name"] == "테스트아파트"
        assert result["build_year"] == 2020
        assert result["households"] == 300
        assert result["gu_name"] == "강남구"
        assert result["dong_name"] == "역삼동"
        assert result["gu_code"] == "11680"
        assert result["dong_code"] == "11680500"

    def test_map_to_naver_format_with_trade_info(self, data_mapper):
        """거래 정보 포함 매핑 테스트"""
        item = {
            "id": "apt123",
            "name": "매매아파트",
            "address": "서울특별시 강남구 개포동",
            "trade": {
                "type": "sale",
                "area": "84.95",
                "floor": "5",
                "price": "1,000,000,000",
                "date": "20241201",
            },
        }

        result = data_mapper.map_to_naver_format(item)

        assert result is not None
        assert result["trade_type"] == "A1"
        assert result["trade_type_name"] == "매매"
        assert result["pyeong_type_number"] == 26  # 84.95 / 3.305785
        assert result["pyeong_name"] == "26평형"
        assert result["floor"] == "5"
        assert result["deal_price"] == 1000000000
        assert result["trade_date"] == "20241201"
        assert result["trade_year"] == 2024

    def test_map_to_naver_format_jeonse(self, data_mapper):
        """전세 매물 매핑 테스트"""
        item = {
            "id": "jeonse123",
            "name": "전세아파트",
            "recent_trade": {
                "type": "jeonse",
                "jeonse_price": "500,000,000",
                "date": "2024-11-01",
            },
        }

        result = data_mapper.map_to_naver_format(item)

        assert result is not None
        assert result["trade_type"] == "B1"
        assert result["trade_type_name"] == "전세"
        assert result["deposit"] == 500000000
        assert result["deal_price"] == 0

    def test_map_to_naver_format_monthly(self, data_mapper):
        """월세 매물 매핑 테스트"""
        item = {
            "id": "monthly123",
            "name": "월세아파트",
            "trade": {
                "type": "monthly",
                "deposit": "100,000,000",
                "monthly": "500,000",
            },
        }

        result = data_mapper.map_to_naver_format(item)

        assert result is not None
        assert result["trade_type"] == "B2"
        assert result["trade_type_name"] == "월세"
        assert result["deposit"] == 100000000
        assert result["monthly_rent"] == 500000

    def test_map_to_naver_format_missing_id(self, data_mapper):
        """ID 없는 데이터 처리"""
        item = {
            "name": "ID없는아파트",
            "address": "서울특별시 강남구",
        }

        result = data_mapper.map_to_naver_format(item)
        assert result is None

    def test_map_to_naver_format_with_fetch_function(self, data_mapper_no_file):
        """fetch 함수를 통한 동 코드 조회"""
        item = {
            "id": "fetch123",
            "name": "조회테스트",
            "address": "서울특별시 강남구 신사동",
        }

        # Mock fetch 함수
        mock_fetch = MagicMock(return_value="11680200")

        result = data_mapper_no_file.map_to_naver_format(item, fetch_dong_code_func=mock_fetch)

        assert result is not None
        assert result["dong_code"] == "11680200"
        assert result["gu_code"] == "11680"

        # fetch 함수가 호출되었는지 확인
        mock_fetch.assert_called_once_with("강남구", "신사동")

        # 매핑 정보가 저장되었는지 확인
        assert data_mapper_no_file.get_dong_code("강남구", "신사동") == "11680200"

    def test_extract_complex_info(self, data_mapper):
        """단지 정보 추출 테스트"""
        mapped_data = {
            "complex_id": "123",
            "complex_name": "아파트",
            "address": "주소",
            "latitude": 37.5,
            "longitude": 127.0,
            "build_year": 2020,
            "households": 300,
            "floors": 20,
            "gu_code": "11680",
            "dong_code": "11680500",
            "gu_name": "강남구",
            "dong_name": "역삼동",
            # 거래 정보
            "trade_type": "A1",
            "deal_price": 100000,
            "pyeong_type_number": 33,
        }

        complex_info = data_mapper.extract_complex_info(mapped_data)

        # 단지 정보만 포함해야 함
        assert complex_info["complex_id"] == "123"
        assert complex_info["complex_name"] == "아파트"
        assert complex_info["address"] == "주소"
        assert "gu_code" in complex_info
        assert "trade_type" not in complex_info
        assert "deal_price" not in complex_info

    def test_extract_transaction_info(self, data_mapper):
        """거래 정보 추출 테스트"""
        mapped_data = {
            "complex_id": "123",
            "complex_name": "아파트",
            "build_year": 2020,
            # 거래 정보
            "trade_type": "A1",
            "trade_type_name": "매매",
            "trade_date": "20241201",
            "trade_year": 2024,
            "floor": "5",
            "deal_price": 1000000000,
            "deposit": 0,
            "monthly_rent": 0,
            "trade_category": "sale",
            "is_delete": "N",
            "is_renew": "N",
            "pyeong_type_number": 33,
            "pyeong_name": "33평형",
        }

        transaction_info = data_mapper.extract_transaction_info(mapped_data)

        # 거래 정보만 포함해야 함
        assert transaction_info["complex_id"] == "123"
        assert transaction_info["trade_type"] == "A1"
        assert transaction_info["deal_price"] == 1000000000
        assert "build_year" not in transaction_info

    def test_map_to_naver_format_with_area_conversion(self, data_mapper):
        """면적 변환 테스트"""
        item = {
            "id": "area123",
            "name": "면적테스트",
            "trade": {
                "area": "33.0",  # 10평
                "exclusive_area": "59.34",  # 18평
            },
        }

        result = data_mapper.map_to_naver_format(item)

        # exclusive_area가 우선순위가 높음
        assert result["pyeong_type_number"] == 18  # 59.34 / 3.305785
        assert result["pyeong_name"] == "18평형"

    def test_map_to_naver_format_trade_date_parsing(self, data_mapper):
        """거래일 파싱 테스트"""
        test_cases = [
            ("20241201", 2024),
            ("2024-12-01", 2024),
            ("2024.12.01", 2024),
            ("202412", 2024),
            ("", 0),
        ]

        for trade_date, expected_year in test_cases:
            item = {
                "id": "date123",
                "name": "날짜테스트",
                "trade": {
                    "date": trade_date,
                },
            }

            result = data_mapper.map_to_naver_format(item)
            assert result["trade_year"] == expected_year

    def test_map_to_naver_format_price_parsing(self, data_mapper):
        """가격 파싱 테스트"""
        item = {
            "id": "price123",
            "name": "가격테스트",
            "trade": {
                "price": "1,234,567,890",  # 쉼표 포함
                "deposit": "500,000,000",
                "monthly": "100,000",
            },
        }

        result = data_mapper.map_to_naver_format(item)

        assert result["deal_price"] == 1234567890
        assert result["deposit"] == 500000000
        assert result["monthly_rent"] == 100000

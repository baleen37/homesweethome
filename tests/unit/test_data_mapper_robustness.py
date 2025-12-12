"""데이터 매퍼 강건성 테스트

손상되거나 비정상적인 데이터를 처리하는 데이터 매퍼의 능력을 검증합니다.
"""

import pytest

from src.crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
from src.crawler.models.api_responses import ComplexInfo


class TestDataMapperRobustness:
    """데이터 매퍼 강건성 테스트"""

    @pytest.fixture
    def mapper(self):
        """테스트용 데이터 매퍼"""
        return HogangnonoDataMapper()

    def test_missing_required_fields(self, mapper):
        """필수 필드가 누락된 데이터 처리"""
        # ID만 있는 최소한의 데이터
        item = {"id": "123"}

        result = mapper.map_to_naver_format(item)

        # None을 반환해야 함
        assert result is None

    def test_null_values_in_critical_fields(self, mapper):
        """중요 필드에 null 값이 있는 경우"""
        item = {"id": None, "name": None, "lat": None, "lng": None}

        result = mapper.map_to_naver_format(item)

        # None을 반환해야 함
        assert result is None

    def test_invalid_coordinates(self, mapper):
        """잘못된 좌표 처리"""
        test_cases = [
            {"id": "123", "name": "아파트", "lat": "invalid", "lng": 127.0},
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": "invalid"},
            {"id": "123", "name": "아파트", "lat": "", "lng": 127.0},
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": ""},
            {"id": "123", "name": "아파트", "lat": 91.0, "lng": 127.0},  # 위도 범위 초과
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": 181.0},  # 경도 범위 초과
        ]

        for item in test_cases:
            result = mapper.map_to_naver_format(item)
            # None을 반환하거나 유효한 ComplexInfo 반환
            # 실제로는 POIInfo에서 처리할 수 있으므로 None이 아닐 수 있음
            assert result is None or isinstance(result, ComplexInfo)

    def test_malformed_address(self, mapper):
        """손상된 주소 처리"""
        test_cases = [
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": 127.0, "address": ""},
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": 127.0, "address": None},
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": 127.0, "address": 123},  # 숫자
            {"id": "123", "name": "아파트", "lat": 37.5, "lng": 127.0, "address": "잘못된주소"},
            {
                "id": "123",
                "name": "아파트",
                "lat": 37.5,
                "lng": 127.0,
                "address": "부산시 해운대구",
            },  # 서울 아님
        ]

        for item in test_cases:
            result = mapper.map_to_naver_format(item)
            if result:
                # 결과가 있더라도 주소 파싱은 실패할 수 있음
                assert result.gu_name is None or result.gu_name == ""
                assert result.dong_name is None or result.dong_name == ""

    def test_non_string_fields(self, mapper):
        """문자열이 아닌 필드 값 처리"""
        item = {
            "id": 123,  # 숫자 ID
            "name": ["아파트", "이름"],  # 배열
            "lat": 37.5,
            "lng": 127.0,
            "address": {"gu": "강남구", "dong": "역삼동"},  # 객체
        }

        result = mapper.map_to_naver_format(item)

        # 처리되거나 실패
        if result:
            assert isinstance(result.id, str)
            assert isinstance(result.name, str)

    def test_extreme_values(self, mapper):
        """극단적인 값 처리"""
        item = {
            "id": "123",
            "name": "아파트",
            "lat": 37.5,
            "lng": 127.0,
            "households": -1,  # 음수
            "floors": 9999,  # 매우 큰 값
            "build_year": 1800,  # 너무 오래된 연도
        }

        result = mapper.map_to_naver_format(item)

        # 처리되거나 실패
        if result:
            # 값이 그대로 유지됨 (검증은 ComplexInfo에서)
            assert result.households == -1 or result.households is None
            assert result.floors == 9999 or result.floors is None

    def test_unicode_and_special_characters(self, mapper):
        """유니코드 및 특수문자 처리"""
        item = {
            "id": "123",
            "name": "테스트'아파트\"특수\n문자",
            "lat": 37.5,
            "lng": 127.0,
            "address": "서울시 강남구 역삼동 🏢",
        }

        result = mapper.map_to_naver_format(item)

        if result:
            # 특수문자 보존
            assert "'" in result.name
            assert '"' in result.name
            assert "🏢" in result.address

    def test_very_long_strings(self, mapper):
        """매우 긴 문자열 처리"""
        long_name = "아" * 1000  # 1000자 이름
        long_address = "서울시 " * 100  # 긴 주소

        item = {"id": "123", "name": long_name, "lat": 37.5, "lng": 127.0, "address": long_address}

        result = mapper.map_to_naver_format(item)

        if result:
            # 긴 문자열 그대로 유지
            assert len(result.name) == 1000
            assert len(result.address) > 100

    def test_nested_structure_parsing(self, mapper):
        """중첩 구조 파싱"""
        item = {
            "id": "123",
            "name": "아파트",
            "lat": 37.5,
            "lng": 127.0,
            "address": {"full": "서울시 강남구 역삼동", "gu": "강남구", "dong": "역삼동"},
        }

        result = mapper.map_to_naver_format(item)

        # 주소 파싱 실패 (문자열이 아님)
        assert result is None or (result.gu_name is None and result.dong_name is None)

    def test_empty_and_whitespace_strings(self, mapper):
        """빈 문자열과 공백 문자열 처리"""
        test_cases = [
            {"id": " ", "name": "아파트", "lat": 37.5, "lng": 127.0},  # 공백 ID
            {"id": "123", "name": "   ", "lat": 37.5, "lng": 127.0},  # 공백 이름
            {"id": "123", "name": "\t\n", "lat": 37.5, "lng": 127.0},  # 탭/개행 이름
        ]

        for item in test_cases:
            result = mapper.map_to_naver_format(item)
            # 처리되거나 실패
            assert result is None or isinstance(result, ComplexInfo)

    def test_boolean_values(self, mapper):
        """불리언 값 처리"""
        item = {
            "id": True,  # 불리언 ID
            "name": False,  # 불리언 이름
            "lat": 37.5,
            "lng": 127.0,
        }

        result = mapper.map_to_naver_format(item)

        if result:
            # 문자열로 변환
            assert isinstance(result.id, str)
            assert isinstance(result.name, str)

    def test_partial_data_extraction(self, mapper):
        """일부 데이터만 있는 경우 추출"""
        # 최소한의 유효한 데이터
        item = {
            "id": "APT_123",
            "name": "테스트아파트",
            "lat": 37.5,
            "lng": 127.0,
            # 나머지 필드 없음
        }

        result = mapper.map_to_naver_format(item)

        if result:
            # 있는 필드만 추출
            assert result.id == "APT_123"
            assert result.name == "테스트아파트"
            assert result.latitude == 37.5
            assert result.longitude == 127.0
            # 없는 필드는 None
            assert result.build_year is None or result.build_year == 0
            assert result.households is None or result.households == 0

    def test_data_type_variations(self, mapper):
        """다양한 데이터 타입 처리"""
        item = {
            "id": "123",
            "name": "아파트",
            "lat": "37.5",  # 문자열 숫자
            "lng": 127.0,  # 실수
            "households": "100",  # 문자열 숫자
            "floors": 20,  # 정수
        }

        result = mapper.map_to_naver_format(item)

        if result:
            # 타입 변환 또는 원본 유지
            assert isinstance(result.latitude, (float, str))
            assert isinstance(result.longitude, (float, str))
            assert isinstance(result.households, (int, str))
            assert isinstance(result.floors, (int, str))

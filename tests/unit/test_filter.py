"""데이터 필터링 유틸리티 단위 테스트"""

from crawler.utils.filter import (
    FilterOptions,
    filter_records,
    get_filter_stats,
    is_valid_address,
    is_valid_coordinate,
    is_valid_household,
    is_valid_name,
    should_filter_record,
)


class TestIsValidHousehold:
    """is_valid_household 함수 테스트"""

    def test_valid_household(self):
        """유효한 세대수"""
        assert is_valid_household("100", 1) is True
        assert is_valid_household("1", 1) is True
        assert is_valid_household("500", 10) is True

    def test_household_below_minimum(self):
        """최소 세대수 미만"""
        assert is_valid_household("0", 1) is False
        assert is_valid_household("5", 10) is False

    def test_household_empty_or_none(self):
        """빈 값 또는 None"""
        assert is_valid_household("", 1) is False
        assert is_valid_household(None, 1) is False

    def test_min_household_zero_means_no_filter(self):
        """min_household=0이면 필터링하지 않음"""
        assert is_valid_household("0", 0) is True
        assert is_valid_household("", 0) is True
        assert is_valid_household(None, 0) is True

    def test_household_negative_min_means_no_filter(self):
        """min_household가 음수면 필터링하지 않음"""
        assert is_valid_household("0", -1) is True
        assert is_valid_household("", -1) is True


class TestIsValidCoordinate:
    """is_valid_coordinate 함수 테스트"""

    def test_valid_seoul_coordinates(self):
        """유효한 서울 좌표"""
        # 강남구 역삼동
        assert is_valid_coordinate("37.5", "127.0") is True
        # 종로구
        assert is_valid_coordinate("37.57", "126.98") is True
        # 마포구
        assert is_valid_coordinate("37.56", "126.9") is True

    def test_zero_coordinates(self):
        """(0, 0) 좌표는 유효하지 않음"""
        assert is_valid_coordinate("0", "0") is False
        assert is_valid_coordinate("0.0", "0.0") is False
        assert is_valid_coordinate("0", "127.0") is False
        assert is_valid_coordinate("37.5", "0") is False

    def test_outside_seoul_coordinates(self):
        """서울 외 좌표"""
        # 부산
        assert is_valid_coordinate("35.1", "129.0") is False
        # 제주
        assert is_valid_coordinate("33.5", "126.5") is False
        # 대전
        assert is_valid_coordinate("36.3", "127.4") is False

    def test_empty_or_none_coordinates(self):
        """빈 값 또는 None 좌표"""
        assert is_valid_coordinate("", "") is False
        assert is_valid_coordinate(None, None) is False
        assert is_valid_coordinate("37.5", None) is False
        assert is_valid_coordinate(None, "127.0") is False

    def test_string_to_float_conversion(self):
        """문자열을 float로 변환"""
        assert is_valid_coordinate("37.5000", "127.0000") is True
        assert is_valid_coordinate("37.5", "127") is True


class TestIsValidName:
    """is_valid_name 함수 테스트"""

    def test_valid_names(self):
        """유효한 이름"""
        assert is_valid_name("역삼자이") is True
        assert is_valid_name("힐스테이트") is True
        assert is_valid_name("ABC") is True

    def test_empty_or_none_names(self):
        """빈 값 또는 None 이름"""
        assert is_valid_name("") is False
        assert is_valid_name(None) is False
        assert is_valid_name("   ") is False

    def test_whitespace_only_names(self):
        """공백만 있는 이름"""
        assert is_valid_name("  ") is False
        assert is_valid_name("\t") is False
        assert is_valid_name("\n") is False


class TestIsValidAddress:
    """is_valid_address 함수 테스트"""

    def test_valid_addresses(self):
        """유효한 주소"""
        assert is_valid_address("서울시 강남구 역삼동") is True
        assert is_valid_address("서울특별시 강남구 역삼동 123-45") is True

    def test_empty_or_none_addresses(self):
        """빈 값 또는 None 주소"""
        assert is_valid_address("") is False
        assert is_valid_address(None) is False
        assert is_valid_address("   ") is False


class TestShouldFilterRecord:
    """should_filter_record 함수 테스트"""

    def test_valid_record_not_filtered(self):
        """유효한 레코드는 필터링하지 않음"""
        record = {
            "seq": "123",
            "name": "테스트아파트",
            "household": "100",
            "lat": "37.5",
            "lng": "127.0",
            "address": "서울시 강남구",
        }
        options = FilterOptions.strict()
        assert should_filter_record(record, options) is False

    def test_household_zero_filtered_with_strict_options(self):
        """household=0은 strict 옵션에서 필터링"""
        record = {
            "seq": "123",
            "name": "테스트",
            "household": "0",
            "lat": "37.5",
            "lng": "127.0",
        }
        options = FilterOptions.strict()
        assert should_filter_record(record, options) is True

    def test_household_zero_not_filtered_with_permissive_options(self):
        """household=0은 permissive 옵션에서 필터링하지 않음"""
        record = {
            "seq": "123",
            "name": "테스트",
            "household": "0",
            "lat": "37.5",
            "lng": "127.0",
        }
        options = FilterOptions.permissive()
        assert should_filter_record(record, options) is False

    def test_zero_coordinates_filtered_with_strict_options(self):
        """(0, 0) 좌표는 strict 옵션에서 필터링"""
        record = {
            "seq": "123",
            "name": "테스트",
            "household": "100",
            "lat": "0.0",
            "lng": "0.0",
        }
        options = FilterOptions.strict()
        assert should_filter_record(record, options) is True

    def test_zero_coordinates_not_filtered_with_moderate_options(self):
        """(0, 0) 좌표는 moderate 옵션에서 필터링하지 않음"""
        record = {
            "seq": "123",
            "name": "테스트",
            "household": "100",
            "lat": "0.0",
            "lng": "0.0",
        }
        options = FilterOptions.moderate()
        assert should_filter_record(record, options) is False

    def test_missing_name_filtered(self):
        """이름이 없으면 필터링"""
        record = {
            "seq": "123",
            "name": "",
            "household": "100",
            "lat": "37.5",
            "lng": "127.0",
        }
        options = FilterOptions(require_name=True)
        assert should_filter_record(record, options) is True

    def test_dict_and_dto_compatibility(self):
        """dict와 DTO 모두 지원"""
        dict_record = {
            "seq": "123",
            "name": "테스트",
            "household": "100",
            "lat": "37.5",
            "lng": "127.0",
        }

        # Mock DTO
        class MockDTO:
            def model_dump(self):
                return dict_record

        dto_record = MockDTO()

        options = FilterOptions.strict()
        assert should_filter_record(dict_record, options) is False
        assert should_filter_record(dto_record, options) is False


class TestFilterRecords:
    """filter_records 함수 테스트"""

    def test_filters_invalid_records(self):
        """유효하지 않은 레코드 필터링"""
        records = [
            {"seq": "1", "name": "A1", "household": "100", "lat": "37.5", "lng": "127.0"},
            {"seq": "2", "name": "A2", "household": "0", "lat": "37.5", "lng": "127.0"},
            {"seq": "3", "name": "A3", "household": "200", "lat": "37.5", "lng": "127.0"},
        ]
        options = FilterOptions(min_household=1)

        filtered = filter_records(records, options)
        assert len(filtered) == 2
        assert filtered[0]["seq"] == "1"
        assert filtered[1]["seq"] == "3"

    def test_permissive_options_keep_all(self):
        """permissive 옵션은 모든 레코드 유지"""
        records = [
            {"seq": "1", "name": "A1", "household": "0", "lat": "0.0", "lng": "0.0"},
            {"seq": "2", "name": "A2", "household": "100", "lat": "37.5", "lng": "127.0"},
        ]
        options = FilterOptions.permissive()

        filtered = filter_records(records, options)
        assert len(filtered) == 2


class TestGetFilterStats:
    """get_filter_stats 함수 테스트"""

    def test_calculates_removal_rate(self):
        """제거율 계산"""
        stats = get_filter_stats(100, 80)
        assert stats["original_count"] == 100
        assert stats["filtered_count"] == 80
        assert stats["removed_count"] == 20
        assert stats["removal_rate"] == 20.0

    def test_zero_original_count(self):
        """원본이 0개일 때"""
        stats = get_filter_stats(0, 0)
        assert stats["removal_rate"] == 0

    def test_no_records_filtered(self):
        """필터링 없음"""
        stats = get_filter_stats(50, 50)
        assert stats["removed_count"] == 0
        assert stats["removal_rate"] == 0

    def test_all_records_filtered(self):
        """모든 레코드 필터링"""
        stats = get_filter_stats(100, 0)
        assert stats["removed_count"] == 100
        assert stats["removal_rate"] == 100


class TestFilterOptions:
    """FilterOptions 클래스 테스트"""

    def test_strict_options(self):
        """strict 옵션 생성"""
        options = FilterOptions.strict()
        assert options.min_household == 1
        assert options.require_valid_coords is True
        assert options.require_name is True

    def test_moderate_options(self):
        """moderate 옵션 생성"""
        options = FilterOptions.moderate()
        assert options.min_household == 1
        assert options.require_valid_coords is False
        assert options.require_name is True

    def test_permissive_options(self):
        """permissive 옵션 생성"""
        options = FilterOptions.permissive()
        assert options.min_household == 0
        assert options.require_valid_coords is False
        assert options.require_name is True

    def test_custom_options(self):
        """사용자 정의 옵션"""
        options = FilterOptions(min_household=50, require_valid_coords=True, require_address=True)
        assert options.min_household == 50
        assert options.require_valid_coords is True
        assert options.require_address is True

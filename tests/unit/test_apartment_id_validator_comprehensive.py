"""아파트 ID 검증기 테스트

TDD 접근법으로 작성된 아파트 ID 검증기 테스트입니다.
"""

from src.crawler.validators.apartment_id_validator import ApartmentIdValidator


class TestApartmentIdValidator:
    """아파트 ID 검증기 테스트 클래스"""

    def test_valid_string_ids(self):
        """유효한 문자열 ID 테스트"""
        valid_ids = ["A1001", "B2022", "APT_001", "home-123", "12345", "single"]

        for apt_id in valid_ids:
            assert ApartmentIdValidator.is_valid_id(apt_id), f"ID {apt_id} should be valid"

    def test_valid_integer_ids(self):
        """유효한 정수 ID 테스트"""
        valid_ids = [12345, 1001, 999999, 1]

        for apt_id in valid_ids:
            assert ApartmentIdValidator.is_valid_id(apt_id), f"ID {apt_id} should be valid"

    def test_none_id(self):
        """None ID 테스트"""
        assert not ApartmentIdValidator.is_valid_id(None), "None ID should be invalid"

    def test_empty_string(self):
        """빈 문자열 테스트"""
        invalid_ids = ["", "   ", "\t", "\n"]

        for apt_id in invalid_ids:
            assert not ApartmentIdValidator.is_valid_id(apt_id), (
                f"Empty ID '{apt_id}' should be invalid"
            )

    def test_invalid_types(self):
        """유효하지 않은 타입 테스트"""
        invalid_types = [123.45, [], {}, set()]

        for apt_id in invalid_types:
            assert not ApartmentIdValidator.is_valid_id(apt_id), (
                f"Type {type(apt_id)} should be invalid"
            )

        # bool은 int의 서브클래스이므로 True는 "1", False는 "0"으로 처리됨
        assert ApartmentIdValidator.is_valid_id(True)  # True는 "1"로 변환
        assert ApartmentIdValidator.is_valid_id(False)  # False는 "0"으로 변환

    def test_invalid_characters(self):
        """유효하지 않은 문자 포함 테스트"""
        invalid_chars = [
            "/",
            " ",
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "+",
            "=",
            "[",
            "]",
            "{",
            "}",
            "|",
            "\\",
            ":",
            ";",
            '"',
            "'",
            "<",
            ">",
            ",",
            ".",
            "?",
            "!",
        ]

        for char in invalid_chars:
            invalid_id = f"A{char}123"
            assert not ApartmentIdValidator.is_valid_id(invalid_id), (
                f"ID with '{char}' should be invalid"
            )

    def test_length_validation(self):
        """길이 검증 테스트"""
        # 최소 길이 미만 (빈 문자열은 위에서 테스트)
        # 최대 길이 초과
        too_long_id = "A" * 51
        assert not ApartmentIdValidator.is_valid_id(too_long_id), (
            f"ID with length {len(too_long_id)} should be invalid"
        )

        # 경계값 테스트
        min_length_id = "A" * 1
        max_length_id = "A" * 50
        assert ApartmentIdValidator.is_valid_id(min_length_id), "Minimum length ID should be valid"
        assert ApartmentIdValidator.is_valid_id(max_length_id), "Maximum length ID should be valid"

    def test_validate_and_normalize_success(self):
        """검증 및 정규화 성공 테스트"""
        # 문자열 ID
        assert ApartmentIdValidator.validate_and_normalize("A1001") == "A1001"
        # 공백이 있는 경우 - 유효하지 않으므로 None 반환
        assert ApartmentIdValidator.validate_and_normalize("  A1001  ") is None

        # 정수 ID
        assert ApartmentIdValidator.validate_and_normalize(12345) == "12345"

    def test_validate_and_normalize_failure(self):
        """검증 및 정규화 실패 테스트"""
        invalid_inputs = [None, "", "A/123", "A B", 123.45, []]

        for invalid_input in invalid_inputs:
            assert ApartmentIdValidator.validate_and_normalize(invalid_input) is None, (
                f"Invalid input {invalid_input} should return None"
            )

    def test_filter_valid_ids(self):
        """유효한 ID 필터링 테스트"""
        mixed_ids = ["A1001", None, "", "B/2022", "C-303", 12345, {}, "D_404"]
        valid_ids, invalid_ids = ApartmentIdValidator.filter_valid_ids(mixed_ids)

        # 유효한 ID 목록 확인
        expected_valid = ["A1001", "C-303", "12345", "D_404"]
        assert valid_ids == expected_valid, f"Valid IDs should be {expected_valid}"

        # 유효하지 않은 ID 목록 확인 (이유 포함)
        assert len(invalid_ids) == 4, "Should have 4 invalid IDs"

        # 각 invalid ID에 이유가 있는지 확인
        for invalid_id, reason in invalid_ids:
            assert isinstance(invalid_id, (type(None), str, int, dict)), (
                "Invalid ID should preserve original type"
            )
            assert isinstance(reason, str), "Reason should be a string"
            assert reason, "Reason should not be empty"

    def test_get_invalid_reason(self):
        """유효하지 않은 이유 반환 테스트"""
        # None 값
        assert ApartmentIdValidator._get_invalid_reason(None) == "None value"

        # 빈 문자열
        assert ApartmentIdValidator._get_invalid_reason("") == "Empty or whitespace only"
        assert ApartmentIdValidator._get_invalid_reason("   ") == "Empty or whitespace only"

        # 유효하지 않은 타입
        assert "Invalid type" in ApartmentIdValidator._get_invalid_reason(123.45)
        assert "Invalid type" in ApartmentIdValidator._get_invalid_reason([])

        # 길이 제한
        too_long = "A" * 51
        assert "Invalid length" in ApartmentIdValidator._get_invalid_reason(too_long)

        # 유효하지 않은 문자
        assert "Contains invalid characters" in ApartmentIdValidator._get_invalid_reason("A/123")

        # 패턴 불일치 - 점은 유효하지 않은 문자 목록에 있음
        assert "invalid characters" in ApartmentIdValidator._get_invalid_reason("A.123")

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # 언더스코어와 하이픈만 포함된 ID
        assert ApartmentIdValidator.is_valid_id("_-_-")

        # 숫자만으로 구성된 ID
        assert ApartmentIdValidator.is_valid_id("1234567890")

        # 영문 소문자
        assert ApartmentIdValidator.is_valid_id("lowercase")

        # 혼합된 대소문자
        assert ApartmentIdValidator.is_valid_id("MixedCase123")

        # 특수문자 조합
        assert ApartmentIdValidator.is_valid_id("A_B-C_D")

    def test_regex_pattern(self):
        """정규식 패턴 테스트"""
        # 패턴에 맞는 경우
        valid_patterns = ["ABC123", "test_case", "test-case", "a1b2c3", "_underscore", "-hyphen"]

        for pattern in valid_patterns:
            assert ApartmentIdValidator.VALID_ID_PATTERN.match(pattern), (
                f"Pattern '{pattern}' should match VALID_ID_PATTERN"
            )

        # 패턴에 맞지 않는 경우
        invalid_patterns = ["A B", "A/B", "A.B", "A@B", "A#B", "A$B"]

        for pattern in invalid_patterns:
            assert not ApartmentIdValidator.VALID_ID_PATTERN.match(pattern), (
                f"Pattern '{pattern}' should not match VALID_ID_PATTERN"
            )

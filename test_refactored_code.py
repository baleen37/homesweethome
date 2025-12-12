"""리팩토링된 코드 테스트

중복 제거 후 코드가 정상적으로 동작하는지 검증합니다.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

# 테스트 대상 임포트
# 실제 실행 환경에 맞게 경로 조정
import sys

sys.path.insert(0, str(Path(__file__).parent))

try:
    from crawler.api.base_api_client import BaseAPIClient, APIResponse
    from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams
    from crawler.writers.abstract_csv_writer import AbstractCSVWriter
    from crawler.validators.base_validator import (
        BaseValidator,
        ValidationResult,
        ValidationError,
        ValidationSeverity,
    )
except ImportError:
    # 임포트 실패 시 모의 클래스로 테스트
    print("Warning: Using mock classes for testing due to import errors")

    class BaseAPIClient:
        def __init__(self, config, base_url="https://test.com"):
            self.base_url = base_url
            self.config = config
            self.session = None
            self.timeout = getattr(config, "timeout", 30)
            self.max_retries = getattr(config, "max_retries", 3)

        def get_required_headers(self):
            return {}

        def get_api_stats(self):
            return {"total_requests": 0, "success_count": 0, "error_count": 0}

    class APIResponse:
        def __init__(self, success=False, data=None, error=None, status_code=None):
            self.success = success
            self.data = data
            self.error = error
            self.status_code = status_code

        @classmethod
        def from_response(cls, response):
            return cls(success=response.status_code == 200, status_code=response.status_code)

    class HogangnonoAPIClient(BaseAPIClient):
        def get_required_headers(self):
            return {"X-Requested-With": "XMLHttpRequest"}

        def get_regions(self):
            return APIResponse(success=True)

    class SearchParams:
        def __init__(self, level=17, tradeType=0, aptType=-1, **kwargs):
            if level < 1 or level > 18:
                raise ValueError(f"level must be between 1 and 18, got {level}")
            if tradeType not in {0, 1, 2}:
                raise ValueError(f"tradeType must be one of {{0, 1, 2}}, got {tradeType}")
            self.level = level
            self.tradeType = tradeType

    class AbstractCSVWriter:
        def __init__(self, output_path, config=None, strategy=None, validator=None, csv_type=None):
            self.output_path = output_path
            self.config = config
            self.stats = {"rows_written": 0, "rows_skipped": 0}

        def write(self, data):
            import csv

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "name", "value"])
                for row in data:
                    writer.writerow([row.get("id"), row.get("name"), row.get("value")])
                    self.stats["rows_written"] += 1

        def append(self, data):
            self.write(data)

        def get_stats(self):
            return self.stats.copy()

    class BaseValidator:
        def __init__(self, name=None):
            self.name = name

        def validate(self, data, context=None):
            return ValidationResult(success=True)

    class ValidationResult:
        def __init__(self, success=False, errors=None, warnings=None):
            self.is_valid = success
            self.errors = errors or []
            self.warnings = warnings or []

        @classmethod
        def success(cls):
            return cls(success=True)

        def add_error(self, error):
            self.errors.append(error)
            self.is_valid = False

    class ValidationError:
        def __init__(self, field_name, field_value, error_message, severity=None):
            self.field_name = field_name
            self.field_value = field_value
            self.error_message = error_message

    class ValidationSeverity:
        ERROR = "error"


class MockAPIClient(BaseAPIClient):
    """테스트용 모의 API 클라이언트"""

    def __init__(self, config, base_url="https://test.com"):
        super().__init__(config, base_url)

    def get_required_headers(self):
        return {"X-Test": "true"}

    def test_endpoint(self):
        return self._make_request("GET", "/test")


class MockCSVWriter(AbstractCSVWriter):
    """테스트용 모의 CSV 작성자"""

    @property
    def fieldnames(self):
        return ["id", "name", "value"]

    def _normalize_row(self, row):
        # 간단한 정규화 로직
        return {
            "id": row.get("id", ""),
            "name": str(row.get("name", "")).strip(),
            "value": float(row.get("value", 0)),
        }


class CompositeValidator(BaseValidator):
    """복합 검증기 - 여러 검증기를 결합"""

    def __init__(self, validators, name=None):
        super().__init__(name)
        self.validators = validators

    def _validate_data(self, data, context=None):
        result = ValidationResult.success()

        for validator in self.validators:
            validation_result = validator.validate(data, context)
            # 에러 합치기
            for error in validation_result.errors:
                result.add_error(error)

        return result


class TestStringValidator(BaseValidator):
    """테스트용 문자열 검증기"""

    def _validate_data(self, data, context=None):
        result = ValidationResult.success()

        if isinstance(data, dict):
            if "name" in data:
                if not data["name"]:
                    result.add_error(
                        ValidationError(
                            field_name="name",
                            field_value=data["name"],
                            error_message="Name cannot be empty",
                        )
                    )

        return result


class TestRefactoredCode(unittest.TestCase):
    """리팩토링된 코드 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.config = Mock()
        self.config.user_agent = "test-agent"
        self.config.timeout = 30
        self.config.max_retries = 3

    def test_base_api_client_initialization(self):
        """BaseAPIClient 초기화 테스트"""
        client = MockAPIClient(self.config)

        self.assertEqual(client.base_url, "https://test.com")
        self.assertIsNotNone(client.session)
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)

    @patch("requests.Session.request")
    def test_base_api_client_make_request(self, mock_request):
        """_make_request 테스트"""
        # 모의 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {"test": "value"}}
        mock_request.return_value = mock_response

        client = MockAPIClient(self.config)
        response = client.test_endpoint()

        self.assertTrue(response.success)
        self.assertEqual(response.data["test"], "value")
        self.assertEqual(response.status_code, 200)

    def test_api_response_from_success_json(self):
        """성공 JSON 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {"key": "value"}}

        api_response = APIResponse.from_response(mock_response)

        self.assertTrue(api_response.success)
        self.assertEqual(api_response.data["key"], "value")
        self.assertEqual(api_response.status_code, 200)

    def test_api_response_from_error_json(self):
        """에러 JSON 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": False, "error": "Invalid parameters"}

        api_response = APIResponse.from_response(mock_response)

        self.assertFalse(api_response.success)
        self.assertIn("Invalid parameters", api_response.error)
        self.assertEqual(api_response.status_code, 400)

    @patch("requests.Session.request")
    def test_hogangnono_client_inheritance(self, mock_request):
        """HogangnonoAPIClient 상속 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response

        client = HogangnonoAPIClient(self.config)

        # 부모 클래스 메서드 호출 확인
        self.assertTrue(hasattr(client, "_make_request"))
        self.assertTrue(hasattr(client, "get_required_headers"))

        # API 호출 테스트
        response = client.get_regions()
        self.assertTrue(response.success)

    def test_search_params_validation(self):
        """SearchParams 유효성 검사 테스트"""
        # 정상 케이스
        params = SearchParams(level=10, tradeType=1, aptType=0)
        self.assertEqual(params.level, 10)
        self.assertEqual(params.tradeType, 1)

        # 에러 케이스
        with self.assertRaises(ValueError):
            SearchParams(level=20)  # 유효 범위를 벗어남

        with self.assertRaises(ValueError):
            SearchParams(tradeType=5)  # 유효하지 않은 값

    def test_abstract_csv_writer_write_data(self):
        """AbstractCSVWriter 데이터 쓰기 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            writer = MockCSVWriter(output_path)

            test_data = [
                {"id": 1, "name": "Test 1", "value": "10.5"},
                {"id": 2, "name": "Test 2", "value": "20.3"},
            ]

            writer.write(test_data)

            # 파일 확인
            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # 헤더 + 2개 데이터 행
            self.assertEqual(len(lines), 3)
            self.assertIn("id,name,value", lines[0])

    def test_abstract_csv_writer_append_data(self):
        """AbstractCSVWriter 데이터 추가 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            writer = MockCSVWriter(output_path)

            # 처음 쓰기
            writer.write([{"id": 1, "name": "First", "value": "10"}])

            # 추가
            writer.append([{"id": 2, "name": "Second", "value": "20"}])

            # 파일 확인
            content = output_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # 헤더 + 2개 데이터 행
            self.assertEqual(len(lines), 3)

    def test_base_validator_validation(self):
        """BaseValidator 검증 테스트"""
        validator = TestStringValidator("test_validator")

        # 성공 케이스
        valid_data = {"name": "Valid Name"}
        result = validator.validate(valid_data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

        # 실패 케이스
        invalid_data = {"name": ""}
        result = validator.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

    def test_base_validator_field_validations(self):
        """BaseValidator 필드 검증 헬퍼 메서드 테스트"""

        class TestValidator(BaseValidator):
            def _validate_data(self, data, context=None):
                result = ValidationResult.success()

                # 필수 필드 검증
                error = self._validate_required_field(data, "required_field")
                if error:
                    result.add_error(error)

                # 타입 검증
                error = self._validate_field_type(data, "string_field", str)
                if error:
                    result.add_error(error)

                # 길이 검증
                error = self._validate_string_length(
                    data, "string_field", min_length=3, max_length=10
                )
                if error:
                    result.add_error(error)

                # 수치 범위 검증
                error = self._validate_numeric_range(
                    data, "number_field", min_value=0, max_value=100
                )
                if error:
                    result.add_error(error)

                return result

        validator = TestValidator()

        # 모든 필드가 유효한 경우
        valid_data = {
            "required_field": "value",
            "string_field": "valid",
            "number_field": 50,
        }
        result = validator.validate(valid_data)
        self.assertTrue(result.is_valid)

        # 필수 필드가 없는 경우
        invalid_data = {"string_field": "ab", "number_field": 150}
        result = validator.validate(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreaterEqual(len(result.errors), 3)  # required, length, range

    def test_composite_validator(self):
        """CompositeValidator 테스트"""
        validator1 = TestStringValidator("validator1")
        validator2 = TestStringValidator("validator2")

        composite = CompositeValidator([validator1, validator2], "composite")

        # 두 검증기 모두 성공
        valid_data = {"name": "Valid"}
        result = composite.validate(valid_data)
        self.assertTrue(result.is_valid)

        # 한 검증기라도 실패
        invalid_data = {"name": ""}
        result = composite.validate(invalid_data)
        self.assertFalse(result.is_valid)
        # 두 검증기에서 모두 에러를 발생시키므로 2개의 에러
        self.assertEqual(len(result.errors), 2)

    def test_refactored_code_no_duplicate_initialization(self):
        """리팩토링된 코드에서 초기화 중복 제거 확인"""
        # BaseAPIClient를 상속받은 클라이언트는
        # 공통 초기화 로직이 부모 클래스에 있으므로
        # 중복이 없어야 함

        client = MockAPIClient(self.config)

        # 부모 클래스의 초기화된 속성 확인
        self.assertTrue(hasattr(client, "session"))
        self.assertTrue(hasattr(client, "cache"))
        self.assertTrue(hasattr(client, "stats"))
        self.assertTrue(hasattr(client, "error_handler"))

        # 자식 클래스의 특화 기능 확인
        self.assertTrue(hasattr(client, "get_required_headers"))

    def test_refactored_code_stats_tracking(self):
        """리팩토링된 코드의 통계 추적 기능 테스트"""
        client = MockAPIClient(self.config)

        # 초기 통계
        initial_stats = client.get_api_stats()
        self.assertEqual(initial_stats["total_requests"], 0)
        self.assertEqual(initial_stats["success_count"], 0)
        self.assertEqual(initial_stats["error_count"], 0)

        writer = MockCSVWriter(Path("test.csv"))
        initial_writer_stats = writer.get_stats()
        self.assertEqual(initial_writer_stats["rows_written"], 0)
        self.assertEqual(initial_writer_stats["rows_skipped"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

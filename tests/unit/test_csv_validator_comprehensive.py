"""CSV 검증器 테스트

TDD 접근법으로 작성된 CSV 데이터 검증기 테스트입니다.
"""

import pytest
from datetime import datetime

from src.crawler.validators.csv_validator import (
    ValidationStatus,
    DataType,
    FieldDefinition,
    ValidationError,
    ValidationResult,
    CSVFieldValidator,
)


class TestValidationStatus:
    """ValidationStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestDataType:
    """DataType Enum 테스트"""

    def test_data_type_values(self):
        """데이터 타입 값 확인"""
        assert DataType.STRING.value == "string"
        assert DataType.INTEGER.value == "integer"
        assert DataType.FLOAT.value == "float"
        assert DataType.BOOLEAN.value == "boolean"
        assert DataType.DATE.value == "date"
        assert DataType.EMAIL.value == "email"
        assert DataType.PHONE.value == "phone"
        assert DataType.POSTAL_CODE.value == "postal_code"


class TestFieldDefinition:
    """FieldDefinition 데이터클래스 테스트"""

    def test_minimal_field_definition(self):
        """최소 필드 정의 생성 테스트"""
        field = FieldDefinition(name="id", data_type=DataType.INTEGER)
        assert field.name == "id"
        assert field.data_type == DataType.INTEGER
        assert field.required is True  # 기본값
        assert field.min_length is None
        assert field.max_length is None
        assert field.min_value is None
        assert field.max_value is None
        assert field.allowed_values is None
        assert field.pattern is None
        assert field.description is None

    def test_complete_field_definition(self):
        """완전한 필드 정의 생성 테스트"""
        field = FieldDefinition(
            name="email",
            data_type=DataType.EMAIL,
            required=False,
            min_length=5,
            max_length=100,
            pattern=r"[^@]+@[^@]+\.[^@]+",
            description="User email address",
        )
        assert field.name == "email"
        assert field.data_type == DataType.EMAIL
        assert field.required is False
        assert field.min_length == 5
        assert field.max_length == 100
        assert field.pattern == r"[^@]+@[^@]+\.[^@]+"
        assert field.description == "User email address"

    def test_field_definition_immutability(self):
        """필드 정의 불변성 테스트"""
        field = FieldDefinition(name="test", data_type=DataType.STRING)

        # frozen=True 이므로 속성 변경 시도 시 에러 발생
        with pytest.raises(Exception):
            field.name = "new_name"


class TestValidationError:
    """ValidationError 데이터클래스 테스트"""

    def test_validation_error_creation(self):
        """검증 오류 생성 테스트"""
        error = ValidationError(
            row_number=10,
            field_name="email",
            field_value="invalid-email",
            error_message="Invalid email format",
            severity=ValidationStatus.FAILED,
        )
        assert error.row_number == 10
        assert error.field_name == "email"
        assert error.field_value == "invalid-email"
        assert error.error_message == "Invalid email format"
        assert error.severity == ValidationStatus.FAILED

    def test_validation_error_default_severity(self):
        """기본 심각도 테스트"""
        error = ValidationError(
            row_number=5, field_name="name", field_value="", error_message="Required field"
        )
        assert error.severity == ValidationStatus.FAILED


class TestValidationResult:
    """ValidationResult 데이터클래스 테스트"""

    def test_validation_result_creation(self):
        """검증 결과 생성 테스트"""
        result = ValidationResult(file_path="/test/file.csv", status=ValidationStatus.PASSED)
        assert result.file_path == "/test/file.csv"
        assert result.status == ValidationStatus.PASSED
        assert result.total_rows == 0
        assert result.valid_rows == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_headers == set()
        assert result.extra_headers == set()
        assert isinstance(result.start_time, datetime)
        assert result.end_time is None

    def test_error_count_property(self):
        """오류 수 속성 테스트"""
        result = ValidationResult(file_path="/test/file.csv", status=ValidationStatus.FAILED)

        assert result.error_count == 0

        result.add_error(
            ValidationError(row_number=1, field_name="test", field_value="", error_message="Error")
        )

        assert result.error_count == 1

    def test_warning_count_property(self):
        """경고 수 속성 테스트"""
        result = ValidationResult(file_path="/test/file.csv", status=ValidationStatus.WARNING)

        assert result.warning_count == 0

        result.add_warning(
            ValidationError(
                row_number=1,
                field_name="test",
                field_value="",
                error_message="Warning",
                severity=ValidationStatus.WARNING,
            )
        )

        assert result.warning_count == 1

    def test_validation_rate_property(self):
        """검증율 속성 테스트"""
        # 빈 파일의 경우
        result = ValidationResult(file_path="/test/file.csv", status=ValidationStatus.PASSED)
        assert result.validation_rate == 1.0

        # 데이터가 있는 경우
        result.total_rows = 100
        result.valid_rows = 90
        assert result.validation_rate == 0.9

    def test_add_error_and_warning(self):
        """오류 및 경고 추가 테스트"""
        result = ValidationResult(file_path="/test/file.csv", status=ValidationStatus.FAILED)

        error = ValidationError(
            row_number=1, field_name="test", field_value="", error_message="Error"
        )

        warning = ValidationError(
            row_number=2,
            field_name="test2",
            field_value="",
            error_message="Warning",
            severity=ValidationStatus.WARNING,
        )

        result.add_error(error)
        result.add_warning(warning)

        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.errors[0] == error
        assert result.warnings[0] == warning


class TestCSVFieldValidator:
    """CSVFieldValidator 클래스 테스트"""

    def test_field_validator_initialization(self):
        """필드 검증기 초기화 테스트"""
        field_def = FieldDefinition("email", DataType.EMAIL, required=True)
        validator = CSVFieldValidator(field_def)
        assert validator.field_def == field_def

    def test_validate_required_field_missing(self):
        """필수 필드 누락 검증 테스트"""
        field_def = FieldDefinition("email", DataType.EMAIL, required=True)
        validator = CSVFieldValidator(field_def)

        errors = validator.validate("", 1)
        assert len(errors) == 1
        assert errors[0].field_name == "email"
        assert "missing or empty" in errors[0].error_message

        errors = validator.validate(None, 1)
        assert len(errors) == 1
        assert errors[0].field_name == "email"

    def test_validate_optional_field_empty(self):
        """선택적 필드 빈 값 검증 테스트"""
        field_def = FieldDefinition("phone", DataType.PHONE, required=False)
        validator = CSVFieldValidator(field_def)

        errors = validator.validate("", 1)
        assert len(errors) == 0

        errors = validator.validate(None, 1)
        assert len(errors) == 0

    def test_validate_min_length(self):
        """최소 길이 검증 테스트"""
        field_def = FieldDefinition("name", DataType.STRING, min_length=3)
        validator = CSVFieldValidator(field_def)

        # 너무 짧은 값
        errors = validator.validate("Jo", 1)
        assert len(errors) == 1
        assert "too short" in errors[0].error_message

        # 적절한 길이
        errors = validator.validate("John", 1)
        assert len(errors) == 0

    def test_validate_max_length(self):
        """최대 길이 검증 테스트"""
        field_def = FieldDefinition("name", DataType.STRING, max_length=10)
        validator = CSVFieldValidator(field_def)

        # 너무 긴 값
        errors = validator.validate("This name is too long", 1)
        assert len(errors) == 1
        assert "too long" in errors[0].error_message

        # 적절한 길이
        errors = validator.validate("John", 1)
        assert len(errors) == 0

    def test_validate_pattern(self):
        """패턴 검증 테스트"""
        field_def = FieldDefinition("email", DataType.STRING, pattern=r"[^@]+@[^@]+\.[^@]+")
        validator = CSVFieldValidator(field_def)

        # 유효한 이메일
        errors = validator.validate("test@example.com", 1)
        assert len(errors) == 0

        # 유효하지 않은 이메일
        errors = validator.validate("invalid-email", 1)
        assert len(errors) == 1
        assert "does not match required pattern" in errors[0].error_message

    def test_validate_allowed_values(self):
        """허용된 값 검증 테스트"""
        field_def = FieldDefinition(
            "status", DataType.STRING, allowed_values={"active", "inactive", "pending"}
        )
        validator = CSVFieldValidator(field_def)

        # 허용된 값
        errors = validator.validate("active", 1)
        assert len(errors) == 0

        # 허용되지 않은 값
        errors = validator.validate("unknown", 1)
        assert len(errors) == 1
        assert "not in allowed values" in errors[0].error_message

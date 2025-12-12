"""기본 검증기

모든 검증기의 공통 기능을 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class ValidationSeverity(Enum):
    """검증 심각도 수준"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationError:
    """검증 에러"""

    field_name: str
    field_value: Any
    error_message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    row_number: Optional[int] = None


@dataclass
class ValidationResult:
    """검증 결과"""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

    @classmethod
    def success(cls) -> "ValidationResult":
        """성공 결과 생성"""
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, errors: List[ValidationError]) -> "ValidationResult":
        """실패 결과 생성"""
        return cls(is_valid=False, errors=errors, warnings=[])

    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """경고 존재 여부"""
        return len(self.warnings) > 0

    def add_error(self, error: ValidationError) -> None:
        """에러 추가"""
        self.errors.append(error)
        if error.severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def add_warning(self, warning: ValidationError) -> None:
        """경고 추가"""
        warning.severity = ValidationSeverity.WARNING
        self.warnings.append(warning)


class BaseValidator(ABC):
    """기본 검증기

    공통 검증 패턴을 제공합니다.
    """

    def __init__(self, name: Optional[str] = None):
        """초기화

        Args:
            name: 검증기 이름
        """
        self.name = name or self.__class__.__name__
        self.logger = logger.bind(validator=self.name)

    def validate(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """데이터 검증

        Args:
            data: 검증할 데이터
            context: 추가 컨텍스트 정보

        Returns:
            ValidationResult 객체
        """
        result = ValidationResult.success()

        try:
            # 사전 검증
            pre_result = self._pre_validate(data, context)
            result.errors.extend(pre_result.errors)
            result.warnings.extend(pre_result.warnings)

            # 주요 검증 로직
            main_result = self._validate_data(data, context)
            result.errors.extend(main_result.errors)
            result.warnings.extend(main_result.warnings)

            # 사후 검증
            post_result = self._post_validate(data, context)
            result.errors.extend(post_result.errors)
            result.warnings.extend(post_result.warnings)

            # 결과 종합
            if result.has_errors():
                result.is_valid = False

            self._log_validation_result(result, context)

        except Exception as e:
            error = ValidationError(
                field_name="validation_error",
                field_value=None,
                error_message=f"Validation failed: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
            )
            result.add_error(error)
            self.logger.error("validation_exception", error=str(e))

        return result

    def _pre_validate(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """사전 검증 (필요시 오버라이드)"""
        return ValidationResult.success()

    @abstractmethod
    def _validate_data(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """주요 검증 로직 (서브클래스에서 구현)"""
        pass

    def _post_validate(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """사후 검증 (필요시 오버라이드)"""
        return ValidationResult.success()

    def _log_validation_result(
        self, result: ValidationResult, context: Optional[Dict] = None
    ) -> None:
        """검증 결과 로깅"""
        if result.has_errors():
            error_count = len(result.errors)
            critical_count = len(
                [e for e in result.errors if e.severity == ValidationSeverity.CRITICAL]
            )

            self.logger.error(
                "validation_failed",
                error_count=error_count,
                critical_count=critical_count,
                context=context,
            )

            if critical_count > 0:
                critical_errors = [
                    e.error_message
                    for e in result.errors
                    if e.severity == ValidationSeverity.CRITICAL
                ]
                self.logger.error(
                    "critical_validation_errors",
                    errors=critical_errors[:5],  # 처음 5개만
                )

        if result.has_warnings():
            self.logger.warning(
                "validation_warnings",
                warning_count=len(result.warnings),
                context=context,
            )

    def _validate_required_field(
        self, data: Dict[str, Any], field_name: str, row_number: Optional[int] = None
    ) -> Optional[ValidationError]:
        """필수 필드 검증"""
        if field_name not in data or data[field_name] is None:
            return ValidationError(
                field_name=field_name,
                field_value=data.get(field_name),
                error_message=f"Required field '{field_name}' is missing or null",
                severity=ValidationSeverity.ERROR,
                row_number=row_number,
            )
        return None

    def _validate_field_type(
        self,
        data: Dict[str, Any],
        field_name: str,
        expected_type: Type,
        row_number: Optional[int] = None,
    ) -> Optional[ValidationError]:
        """필드 타입 검증"""
        if field_name in data:
            value = data[field_name]
            if value is not None and not isinstance(value, expected_type):
                return ValidationError(
                    field_name=field_name,
                    field_value=value,
                    error_message=(
                        f"Field '{field_name}' should be {expected_type.__name__}, "
                        f"but got {type(value).__name__}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    row_number=row_number,
                )
        return None

    def _validate_string_length(
        self,
        data: Dict[str, Any],
        field_name: str,
        min_length: int = 0,
        max_length: Optional[int] = None,
        row_number: Optional[int] = None,
    ) -> Optional[ValidationError]:
        """문자열 길이 검증"""
        if field_name in data:
            value = data[field_name]
            if value is not None:
                str_value = str(value)
                length = len(str_value)

                if length < min_length:
                    return ValidationError(
                        field_name=field_name,
                        field_value=value,
                        error_message=(
                            f"Field '{field_name}' length {length} is less than "
                            f"minimum {min_length}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        row_number=row_number,
                    )

                if max_length and length > max_length:
                    return ValidationError(
                        field_name=field_name,
                        field_value=value,
                        error_message=(
                            f"Field '{field_name}' length {length} exceeds maximum {max_length}"
                        ),
                        severity=ValidationSeverity.WARNING,
                        row_number=row_number,
                    )
        return None

    def _validate_numeric_range(
        self,
        data: Dict[str, Any],
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        row_number: Optional[int] = None,
    ) -> Optional[ValidationError]:
        """수치 범위 검증"""
        if field_name in data:
            value = data[field_name]
            if value is not None:
                try:
                    num_value = float(value)

                    if min_value is not None and num_value < min_value:
                        return ValidationError(
                            field_name=field_name,
                            field_value=value,
                            error_message=(
                                f"Field '{field_name}' value {num_value} is less than "
                                f"minimum {min_value}"
                            ),
                            severity=ValidationSeverity.ERROR,
                            row_number=row_number,
                        )

                    if max_value is not None and num_value > max_value:
                        return ValidationError(
                            field_name=field_name,
                            field_value=value,
                            error_message=(
                                f"Field '{field_name}' value {num_value} exceeds "
                                f"maximum {max_value}"
                            ),
                            severity=ValidationSeverity.ERROR,
                            row_number=row_number,
                        )
                except (ValueError, TypeError):
                    return ValidationError(
                        field_name=field_name,
                        field_value=value,
                        error_message=(
                            f"Field '{field_name}' must be a number, got {type(value).__name__}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        row_number=row_number,
                    )
        return None


class CompositeValidator(BaseValidator):
    """복합 검증기

    여러 검증기를 결합하여 사용합니다.
    """

    def __init__(self, validators: List[BaseValidator], name: Optional[str] = None):
        """초기화

        Args:
            validators: 결합할 검증기 목록
            name: 검증기 이름
        """
        super().__init__(name)
        self.validators = validators

    def _validate_data(self, data: Any, context: Optional[Dict] = None) -> ValidationResult:
        """모든 검증기 실행"""
        result = ValidationResult.success()

        for validator in self.validators:
            validator_result = validator.validate(data, context)
            result.errors.extend(validator_result.errors)
            result.warnings.extend(validator_result.warnings)

            # 실패 시 즉시 중단 옵션
            if result.has_errors() and context and context.get("fail_fast", False):
                break

        return result

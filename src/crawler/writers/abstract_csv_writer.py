"""추상 CSV 작성자

CSV 작성의 공통 패턴을 추상화하여 중복을 줄입니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
import csv
import structlog
from dataclasses import dataclass

from crawler.writers.data_transformation_strategy import DataTransformationStrategy
from crawler.validators.csv_validator import CSVValidator
from crawler.writers.csv_header_standard import CSVType

logger = structlog.get_logger().bind(component="AbstractCSVWriter")


@dataclass
class WriteConfig:
    """CSV 쓰기 설정"""

    encoding: str = "utf-8"
    newline: str = ""
    delimiter: str = ","
    quotechar: str = '"'
    quoting: int = csv.QUOTE_MINIMAL
    skip_invalid_rows: bool = True
    enable_validation: bool = True


class AbstractCSVWriter(ABC):
    """추상 CSV 작성자

    모든 CSV 작성자의 공통 동작을 정의합니다.
    """

    def __init__(
        self,
        output_path: Path,
        config: Optional[WriteConfig] = None,
        strategy: Optional[DataTransformationStrategy] = None,
        validator: Optional[CSVValidator] = None,
        csv_type: Optional[CSVType] = None,
    ):
        """초기화

        Args:
            output_path: 출력 CSV 파일 경로
            config: 쓰기 설정
            strategy: 데이터 변환 전략
            validator: 데이터 검증기
            csv_type: CSV 타입 (헤더 표준화용)
        """
        self.output_path = output_path
        self.config = config or WriteConfig()
        self.strategy = strategy
        self.validator = validator
        self.csv_type = csv_type

        # 파일 존재 여부 확인
        self._file_exists = output_path.exists()

        # 통계
        self.stats = {
            "rows_written": 0,
            "rows_skipped": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
        }

    @property
    @abstractmethod
    def fieldnames(self) -> List[str]:
        """CSV 필드명 목록 (서브클래스에서 구현)"""
        pass

    @abstractmethod
    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """행 데이터 정규화 (서브클래스에서 구현)"""
        pass

    def _validate_row(self, row: Dict[str, Any], row_number: int) -> bool:
        """행 데이터 검증"""
        if not self.config.enable_validation or not self.validator:
            return True

        result = self.validator.validate_row(row, row_number)
        self.stats["validation_errors"] += len(result.errors)
        self.stats["validation_warnings"] += len(result.warnings)

        # 로깅
        if result.errors:
            logger.error(
                "row_validation_failed",
                row_number=row_number,
                error_count=len(result.errors),
            )
        if result.warnings:
            logger.warning(
                "row_validation_warnings",
                row_number=row_number,
                warning_count=len(result.warnings),
            )

        return result.is_valid()

    def write_header(self) -> None:
        """CSV 헤더 쓰기"""
        self._ensure_directory()

        with open(
            self.output_path,
            mode="w",
            encoding=self.config.encoding,
            newline=self.config.newline,
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )
            writer.writeheader()

        self._file_exists = True
        logger.info("header_written", file_path=str(self.output_path))

    def write(
        self,
        data: List[Dict[str, Any]],
        mode: str = "w",
        write_header: bool = None,
    ) -> None:
        """데이터 쓰기

        Args:
            data: 쓸 데이터 목록
            mode: 쓰기 모드 ('w' 또는 'a')
            write_header: 헤더 쓰기 여부 (None은 자동 결정)
        """
        if not data:
            logger.info("write_skipped", reason="empty_data")
            return

        self._ensure_directory()

        # 헤더 쓰기 결정
        if write_header is None:
            write_header = mode == "w" or not self._file_exists

        # 데이터 처리
        processed_data = self._process_data(data)

        # 파일 쓰기
        with open(
            self.output_path,
            mode=mode,
            encoding=self.config.encoding,
            newline=self.config.newline,
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            if write_header:
                writer.writeheader()

            if processed_data:
                writer.writerows(processed_data)
                self.stats["rows_written"] += len(processed_data)

        self._file_exists = True
        logger.info(
            "write_completed",
            file_path=str(self.output_path),
            rows_written=len(processed_data),
            total_input=len(data),
        )

    def append(self, data: List[Dict[str, Any]]) -> None:
        """데이터 추가"""
        if not self._file_exists:
            # 파일이 없으면 새로 생성
            self.write(data, mode="w")
        else:
            # 기존 파일에 추가
            self.write(data, mode="a", write_header=False)

    def _process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """데이터 처리 (검증 및 정규화)"""
        processed = []

        for i, row in enumerate(data, start=1):
            # 검증
            if not self._validate_row(row, i):
                if self.config.skip_invalid_rows:
                    self.stats["rows_skipped"] += 1
                    continue
                else:
                    raise ValueError(f"Row {i} failed validation")

            # 정규화
            try:
                normalized = self._normalize_row(row)
                processed.append(normalized)
            except Exception as e:
                logger.error(
                    "normalization_failed",
                    row_number=i,
                    error=str(e),
                    skipping=True,
                )
                if self.config.skip_invalid_rows:
                    self.stats["rows_skipped"] += 1
                    continue
                else:
                    raise

        return processed

    def _ensure_directory(self) -> None:
        """디렉토리 생성"""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        stats = self.stats.copy()
        stats["file_exists"] = self._file_exists
        stats["file_path"] = str(self.output_path)
        if self._file_exists:
            stats["file_size"] = self.output_path.stat().st_size
        return stats

    def reset_stats(self) -> None:
        """통계 초기화"""
        self.stats = {
            "rows_written": 0,
            "rows_skipped": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
        }

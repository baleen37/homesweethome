"""File logging handler for ProgressTracker.

This module provides FileLogHandler class that handles all file I/O operations
for the ProgressTracker, including checkpoint file management and JSON serialization.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, TextIO, cast

import structlog


class FileLogHandler:
    """File logging handler for ProgressTracker.

    Handles all file I/O operations including:
    - Checkpoint file writing and loading
    - JSON serialization/deserialization
    - File path management
    - Structured log file writing
    """

    def __init__(self, output_dir: Path, log_file: Optional[str] = None) -> None:
        """FileLogHandler 초기화

        Args:
            output_dir: 로그 파일 저장 디렉토리
            log_file: 추가 로그 파일 경로 (선택적)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 로거 설정
        self.logger = structlog.get_logger()

        # 진행 상황 저장 파일 경로
        self.progress_file = self.output_dir / "progress.json"

        # 로그 파일 핸들
        self.log_file: Optional[TextIO] = None
        if log_file:
            try:
                self.log_file = open(self.output_dir / log_file, "w", encoding="utf-8")
                self._write_initial_log()
            except Exception as e:
                self.logger.warning(
                    "failed_to_open_log_file",
                    log_file=log_file,
                    error=str(e),
                )
                self.log_file = None

    def _write_initial_log(self) -> None:
        """초기 로그 메시지 작성"""
        if self.log_file:
            self._write_log_entry(
                level="INFO",
                event="progress_tracking_started",
                output_dir=str(self.output_dir),
            )

    def _write_log_entry(self, level: str, event: str, **kwargs: Any) -> None:
        """로그 엔트리를 JSON 형식으로 작성

        Args:
            level: 로그 레벨 (INFO, ERROR, etc.)
            event: 이벤트 이름
            **kwargs: 추가 이벤트 데이터
        """
        if self.log_file:
            log_entry = {
                "timestamp": time.time(),
                "level": level,
                "event": event,
                **kwargs,
            }
            self.log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            self.log_file.flush()

    def save_progress(self, progress_data: Dict[str, Any]) -> None:
        """진행 상황을 파일에 저장

        Args:
            progress_data: 저장할 진행 상황 데이터
        """
        try:
            # 현재 시간 추가
            data_to_save = {
                **progress_data,
                "current_time": time.time(),
            }

            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(
                "failed_to_save_progress",
                error=str(e),
                progress_file=str(self.progress_file),
            )

    def load_progress(self) -> Optional[Dict[str, Any]]:
        """저장된 진행 상황을 로드

        Returns:
            저장된 진행 상황 데이터 또는 None
        """
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return cast(Dict[str, Any], json.load(f))
            except Exception as e:
                self.logger.warning(
                    "failed_to_load_progress",
                    error=str(e),
                    progress_file=str(self.progress_file),
                )
        return None

    def log_dong_started(
        self,
        dong_code: str,
        dong_name: str,
        complex_count: int,
    ) -> None:
        """동 처리 시작 로그 작성

        Args:
            dong_code: 동 코드
            dong_name: 동 이름
            complex_count: 해당 동의 단지 수
        """
        self._write_log_entry(
            level="INFO",
            event="dong_started",
            dong_code=dong_code,
            dong_name=dong_name,
            complex_count=complex_count,
        )

    def log_error(self, error: str) -> None:
        """에러 로그 작성

        Args:
            error: 에러 메시지
        """
        self._write_log_entry(
            level="ERROR",
            event="error_occurred",
            error=error,
        )

    def log_progress_report(self, summary: Dict[str, Any]) -> None:
        """진행 상황 리포트 로그 작성

        Args:
            summary: 진행 상황 요약 데이터
        """
        self._write_log_entry(
            level="INFO",
            event="progress_report",
            summary=summary,
        )

    def log_crawling_finished(self, final_summary: Dict[str, Any]) -> None:
        """크롤링 완료 로그 작성

        Args:
            final_summary: 최종 진행 상황 요약 데이터
        """
        self._write_log_entry(
            level="INFO",
            event="crawling_finished",
            final_summary=final_summary,
        )

    def close(self) -> None:
        """로그 파일 핸들을 닫기"""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception as e:
                self.logger.warning(
                    "failed_to_close_log_file",
                    error=str(e),
                )
            finally:
                self.log_file = None

    def __enter__(self) -> "FileLogHandler":
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager 종료"""
        self.close()

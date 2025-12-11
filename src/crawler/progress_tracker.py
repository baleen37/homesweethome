"""Progress tracker for monitoring crawling operations.

This module provides ProgressTracker class that monitors and reports
the progress of long-running crawling operations with real-time statistics,
performance metrics, and ETA calculations.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from crawler.file_log_handler import FileLogHandler
from crawler.statistics_calculator import StatisticsCalculator


class ProgressTracker:
    """크롤링 진행 상황 추적기

    실시간 진행 상황 보고, 성능 측정, 오류율 모니터링을 제공합니다.
    """

    def __init__(
        self,
        output_dir: Path,
        report_interval: int = 60,
        log_file: Optional[str] = None,
    ) -> None:
        """ProgressTracker 초기화

        Args:
            output_dir: 진행 상황 리포트 저장 디렉토리
            report_interval: 리포트 출력 간격 (초)
            log_file: 추가 로그 파일 경로 (선택적)
        """
        # 리포트 간격 설정
        self.report_interval = report_interval
        self.last_report_time: float = 0.0

        # 로그 설정
        self.logger = structlog.get_logger()

        # 파일 로그 핸들러
        self.file_handler = FileLogHandler(output_dir, log_file)

        # 통계 데이터
        self.stats: Dict[str, Any] = {
            "start_time": 0,
            "current_time": 0,
            "total_dongs": 0,
            "completed_dongs": 0,
            "total_complexes": 0,
            "completed_complexes": 0,
            "total_transactions": 0,
            "collected_transactions": 0,
            "errors": [],
            "error_count": 0,
            "rate_limiter_delay": 2.5,
            "avg_complex_time": 0,
            "avg_dong_time": 0,
        }

        # 속도 측정을 위한 타이밍 데이터
        self.timings: List[Dict[str, Any]] = []
        self.current_dong_start: float = 0.0
        self.current_complex_start: float = 0.0

    def start_crawling(
        self,
        total_dongs: int,
        total_complexes: int,
    ) -> None:
        """크롤링 시작을 기록

        Args:
            total_dongs: 전체 동 수
            total_complexes: 전체 단지 수
        """
        self.stats.update(
            {
                "start_time": time.time(),
                "total_dongs": total_dongs,
                "total_complexes": total_complexes,
            }
        )

        self.logger.info(
            "crawling_started",
            total_dongs=total_dongs,
            total_complexes=total_complexes,
        )

        # 초기 리포트 출력
        self._save_progress()

    def start_dong(self, dong_code: str, dong_name: str, complex_count: int) -> None:
        """동 처리 시작을 기록

        Args:
            dong_code: 동 코드
            dong_name: 동 이름
            complex_count: 해당 동의 단지 수
        """
        self.current_dong_start = time.time()

        self.logger.info(
            "dong_processing_started",
            dong_code=dong_code,
            dong_name=dong_name,
            complex_count=complex_count,
        )

        # 파일 로그에도 기록
        self.file_handler.log_dong_started(dong_code, dong_name, complex_count)

    def complete_dong(
        self,
        dong_code: str,
        dong_name: str,
        complexes_processed: int,
        transactions_collected: int,
        errors: List[str],
    ) -> None:
        """동 처리 완료를 기록

        Args:
            dong_code: 동 코드
            dong_name: 동 이름
            complexes_processed: 처리된 단지 수
            transactions_collected: 수집된 거래내역 수
            errors: 에러 목록
        """
        duration = time.time() - self.current_dong_start

        # 통계 업데이트
        self.stats["completed_dongs"] += 1
        self.stats["collected_transactions"] += transactions_collected
        self.stats["error_count"] += len(errors)
        self.stats["errors"].extend(errors)

        # 타이밍 기록 (평균 속도 계산용)
        self.timings.append(
            {
                "type": "dong",
                "duration": duration,
                "complexes": complexes_processed,
                "transactions": transactions_collected,
                "timestamp": time.time(),
            }
        )

        # 최근 10개의 동 타이밍으로 평균 계산
        self.stats["avg_dong_time"] = StatisticsCalculator.compute_average_timing(
            self.timings, "dong", 10
        )

        self.logger.info(
            "dong_processing_completed",
            dong_code=dong_code,
            dong_name=dong_name,
            duration_seconds=duration,
            complexes_processed=complexes_processed,
            transactions_collected=transactions_collected,
            errors_count=len(errors),
        )

        # 주기적 리포트 확인
        self._check_report_interval()

        # 진행 상황 저장
        self._save_progress()

    def start_complex(self, complex_id: str, complex_name: str) -> None:
        """단지 처리 시작을 기록

        Args:
            complex_id: 단지 ID
            complex_name: 단지명
        """
        self.current_complex_start = time.time()

        # 디버그 레벨로 로그 (너무 많지 않게)
        self.logger.debug(
            "complex_processing_started",
            complex_id=complex_id,
            complex_name=complex_name,
        )

    def complete_complex(
        self,
        complex_id: str,
        complex_name: str,
        transactions_collected: int,
    ) -> None:
        """단지 처리 완료를 기록

        Args:
            complex_id: 단지 ID
            complex_name: 단지명
            transactions_collected: 수집된 거래내역 수
        """
        duration = time.time() - self.current_complex_start

        # 통계 업데이트
        self.stats["completed_complexes"] += 1
        self.stats["collected_transactions"] += transactions_collected

        # 타이밍 기록
        self.timings.append(
            {
                "type": "complex",
                "duration": duration,
                "transactions": transactions_collected,
                "timestamp": time.time(),
            }
        )

        # 최근 50개의 단지 타이밍으로 평균 계산
        self.stats["avg_complex_time"] = StatisticsCalculator.compute_average_timing(
            self.timings, "complex", 50
        )

        # 디버그 레벨로 로그
        self.logger.debug(
            "complex_processing_completed",
            complex_id=complex_id,
            duration_seconds=duration,
            transactions_collected=transactions_collected,
        )

    def update_rate_limiter_delay(self, delay: float) -> None:
        """Rate limiter 지연 시간 업데이트

        Args:
            delay: 현재 지연 시간 (초)
        """
        self.stats["rate_limiter_delay"] = delay

    def add_error(self, error: str) -> None:
        """에러를 기록

        Args:
            error: 에러 메시지
        """
        self.stats["error_count"] += 1
        self.stats["errors"].append(error)

        # 에러 로그
        self.logger.error("crawling_error", error=error)

        # 파일 로그에도 기록
        self.file_handler.log_error(error)

    def get_progress_summary(self) -> Dict[str, Any]:
        """진행 상황 요약을 반환

        Returns:
            진행 상황 요약 딕셔너리
        """
        return StatisticsCalculator.calculate_comprehensive_stats(
            stats=self.stats,
            timings=self.timings,
        )

    def print_progress_report(self, force: bool = False) -> None:
        """진행 상황 리포트를 출력

        Args:
            force: True이면 리포트 간격과 무관하게 즉시 출력
        """
        current_time = time.time()

        # 강제 출력이 아니면 리포트 간격 확인
        if not force and current_time - self.last_report_time < self.report_interval:
            return

        summary = self.get_progress_summary()

        # 콘솔 출력 (깔끔한 형식)
        print("\n" + "=" * 60)
        print(f"[{summary['last_updated']}] 크롤링 진행 상황")
        print("=" * 60)

        # 진행률
        print(
            f"동: {summary['completed_dongs']}/{summary['total_dongs']} ({summary['dong_progress_percent']}%)"
        )
        print(
            f"단지: {summary['completed_complexes']}/{summary['total_complexes']} ({summary['complex_progress_percent']}%)"
        )
        print(f"거래내역: {summary['collected_transactions']:,}건 수집")

        # 시간 정보
        print(f"\n경과 시간: {summary['elapsed_time_formatted']}")
        print(f"예상 남은 시간: {summary['eta_formatted']}")

        # 성능 지표
        print("\n성능:")
        print(f"  - 단지 처리 속도: {summary['complexes_per_hour']:.1f}개/시간")
        print(f"  - 거래내역 수집 속도: {summary['transactions_per_hour']:.1f}건/시간")
        print(f"  - 평균 Rate Limit: {summary['rate_limiter_delay']:.1f}초")

        # 에러 정보
        if summary["error_count"] > 0:
            print(
                f"\n⚠️  에러: {summary['error_count']}건 (에러율: {summary['error_rate_percent']}%)"
            )

        print("=" * 60)
        sys.stdout.flush()

        self.last_report_time = current_time

        # 파일 로그에도 기록
        self.file_handler.log_progress_report(summary)

    def _check_report_interval(self) -> None:
        """리포트 출력 간격을 확인하고 필요 시 출력"""
        self.print_progress_report()

    def _save_progress(self) -> None:
        """진행 상황을 파일에 저장"""
        progress_data = {
            **self.stats,
            "summary": self.get_progress_summary(),
        }

        self.file_handler.save_progress(progress_data)

    def _format_duration(self, seconds: float) -> str:
        """초를 사람이 읽기 쉬운 형식으로 변환

        Args:
            seconds: 초

        Returns:
            형식화된 시간 문자열
        """
        return StatisticsCalculator.format_duration(seconds)

    def finish_crawling(self) -> None:
        """크롤링 완료를 기록"""
        final_summary = self.get_progress_summary()

        self.logger.info(
            "crawling_completed",
            total_duration=final_summary["elapsed_time_formatted"],
            total_complexes=self.stats["completed_complexes"],
            total_transactions=self.stats["collected_transactions"],
            total_errors=self.stats["error_count"],
        )

        # 최종 리포트 출력
        self.print_progress_report(force=True)

        # 파일 로그 마무리
        self.file_handler.log_crawling_finished(final_summary)
        self.file_handler.close()

        # 최종 진행 상황 저장
        self._save_progress()

    def load_progress(self) -> Optional[Dict[str, Any]]:
        """저장된 진행 상황을 로드

        Returns:
            저장된 진행 상황 데이터 또는 None
        """
        return self.file_handler.load_progress()

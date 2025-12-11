"""Statistics calculator for crawling operations.

This module provides StatisticsCalculator class that handles all statistical
computations for crawling operations, including progress percentages,
ETA calculations, processing rates, and time formatting utilities.
"""

import time
from typing import Any, Dict, List


class StatisticsCalculator:
    """통계 계산기

    크롤링 작업의 모든 통계 계산을 처리합니다.
    진행률, 예상 소요시간, 처리 속도 등을 계산합니다.
    """

    @staticmethod
    def compute_progress_percentage(completed: int, total: int) -> float:
        """진행률 백분율 계산

        Args:
            completed: 완료된 수
            total: 전체 수

        Returns:
            진행률 (0-100)
        """
        if total <= 0:
            return 0.0
        return (completed / total) * 100

    @staticmethod
    def compute_eta(avg_time_per_item: float, remaining_items: int) -> float:
        """예상 소요시간(ETA) 계산

        Args:
            avg_time_per_item: 항목당 평균 소요 시간 (초)
            remaining_items: 남은 항목 수

        Returns:
            예상 소요시간 (초)
        """
        if avg_time_per_item <= 0 or remaining_items <= 0:
            return 0.0
        return avg_time_per_item * remaining_items

    @staticmethod
    def compute_processing_rate(items_processed: int, elapsed_seconds: float) -> float:
        """시간당 처리 속도 계산

        Args:
            items_processed: 처리된 항목 수
            elapsed_seconds: 경과 시간 (초)

        Returns:
            시간당 처리 속도 (items/hour)
        """
        if elapsed_seconds <= 0:
            return 0.0
        return (items_processed / elapsed_seconds) * 3600

    @staticmethod
    def compute_average_timing(
        timings: List[Dict[str, Any]], timing_type: str, limit: int = 10
    ) -> float:
        """특정 유형의 평균 타이밍 계산

        Args:
            timings: 타이밍 데이터 리스트
            timing_type: 타이밍 유형 ('dong' 또는 'complex')
            limit: 평균 계산에 사용할 최근 데이터 수

        Returns:
            평균 시간 (초)
        """
        filtered_timings = [t for t in timings if t.get("type") == timing_type][-limit:]
        if not filtered_timings:
            return 0.0
        return sum(t["duration"] for t in filtered_timings) / len(filtered_timings)

    @staticmethod
    def compute_error_rate(error_count: int, total_operations: int) -> float:
        """에러율 계산

        Args:
            error_count: 에러 수
            total_operations: 전체 작업 수

        Returns:
            에러율 (0-100)
        """
        if total_operations <= 0:
            return 0.0
        return (error_count / total_operations) * 100

    @staticmethod
    def format_duration(seconds: float) -> str:
        """초를 사람이 읽기 쉬운 형식으로 변환

        Args:
            seconds: 초

        Returns:
            형식화된 시간 문자열
        """
        if seconds < 60:
            return f"{seconds:.0f}초"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}분"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}시간"
        else:
            days = seconds / 86400
            return f"{days:.1f}일"

    @staticmethod
    def calculate_comprehensive_stats(
        stats: Dict[str, Any],
        timings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """종합 통계 계산

        Args:
            stats: 기본 통계 데이터
            timings: 타이밍 데이터

        Returns:
            계산된 통계 딕셔너리
        """
        current_time = time.time()
        start_time = stats.get("start_time", current_time)
        elapsed = current_time - start_time

        # 진행률 계산
        dong_progress = StatisticsCalculator.compute_progress_percentage(
            stats.get("completed_dongs", 0), stats.get("total_dongs", 0)
        )
        complex_progress = StatisticsCalculator.compute_progress_percentage(
            stats.get("completed_complexes", 0), stats.get("total_complexes", 0)
        )

        # 남은 항목 계산
        remaining_dongs = stats.get("total_dongs", 0) - stats.get("completed_dongs", 0)
        remaining_complexes = stats.get("total_complexes", 0) - stats.get("completed_complexes", 0)

        # ETA 계산
        avg_dong_time = StatisticsCalculator.compute_average_timing(timings, "dong", 10)
        eta_seconds = StatisticsCalculator.compute_eta(avg_dong_time, remaining_dongs)

        # 성능 지표 계산
        avg_complexes_per_hour = StatisticsCalculator.compute_processing_rate(
            stats.get("completed_complexes", 0), elapsed
        )
        avg_transactions_per_hour = StatisticsCalculator.compute_processing_rate(
            stats.get("collected_transactions", 0), elapsed
        )

        # 에러율 계산
        total_operations = stats.get("completed_complexes", 0) + stats.get("completed_dongs", 0)
        error_rate = StatisticsCalculator.compute_error_rate(
            stats.get("error_count", 0), total_operations
        )

        # 평균 처리 시간 계산
        avg_complex_time = StatisticsCalculator.compute_average_timing(timings, "complex", 50)

        return {
            "elapsed_time_seconds": elapsed,
            "elapsed_time_formatted": StatisticsCalculator.format_duration(elapsed),
            "eta_seconds": eta_seconds,
            "eta_formatted": StatisticsCalculator.format_duration(eta_seconds)
            if eta_seconds > 0
            else "계산 중...",
            # 진행률
            "dong_progress_percent": round(dong_progress, 1),
            "completed_dongs": stats.get("completed_dongs", 0),
            "total_dongs": stats.get("total_dongs", 0),
            "remaining_dongs": remaining_dongs,
            "complex_progress_percent": round(complex_progress, 1),
            "completed_complexes": stats.get("completed_complexes", 0),
            "total_complexes": stats.get("total_complexes", 0),
            "remaining_complexes": remaining_complexes,
            # 수집된 데이터
            "collected_transactions": stats.get("collected_transactions", 0),
            # 성능 지표
            "avg_complex_time_seconds": round(avg_complex_time, 1),
            "avg_dong_time_seconds": round(avg_dong_time, 1),
            "complexes_per_hour": round(avg_complexes_per_hour, 1),
            "transactions_per_hour": round(avg_transactions_per_hour, 1),
            # 현재 상태
            "rate_limiter_delay": round(stats.get("rate_limiter_delay", 2.5), 1),
            "error_count": stats.get("error_count", 0),
            "error_rate_percent": round(error_rate, 1),
            # 마지막 업데이트 시간
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

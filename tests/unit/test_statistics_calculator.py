"""Tests for StatisticsCalculator functionality."""

from unittest.mock import patch

from crawler.statistics_calculator import StatisticsCalculator

# Import test setup to configure path and mocks


class TestStatisticsCalculator:
    """StatisticsCalculator 테스트 클래스"""

    def test_compute_progress_percentage(self):
        """진행률 백분율 계산 테스트"""
        # 정상적인 경우
        assert StatisticsCalculator.compute_progress_percentage(5, 10) == 50.0
        assert StatisticsCalculator.compute_progress_percentage(0, 10) == 0.0
        assert StatisticsCalculator.compute_progress_percentage(10, 10) == 100.0

        # 경계 조건
        assert StatisticsCalculator.compute_progress_percentage(5, 0) == 0.0
        assert StatisticsCalculator.compute_progress_percentage(0, 0) == 0.0
        assert StatisticsCalculator.compute_progress_percentage(10, -5) == 0.0

    def test_compute_eta(self):
        """예상 소요시간(ETA) 계산 테스트"""
        # 정상적인 경우
        assert StatisticsCalculator.compute_eta(10.0, 5) == 50.0
        assert StatisticsCalculator.compute_eta(1.5, 10) == 15.0

        # 경계 조건
        assert StatisticsCalculator.compute_eta(0, 10) == 0.0
        assert StatisticsCalculator.compute_eta(10.0, 0) == 0.0
        assert StatisticsCalculator.compute_eta(-5.0, 10) == 0.0
        assert StatisticsCalculator.compute_eta(10.0, -5) == 0.0

    def test_compute_processing_rate(self):
        """시간당 처리 속도 계산 테스트"""
        # 정상적인 경우
        # 100개 항목을 3600초(1시간) 동안 처리 = 100개/시간
        assert StatisticsCalculator.compute_processing_rate(100, 3600) == 100.0
        # 60개 항목을 1800초(30분) 동안 처리 = 120개/시간
        assert StatisticsCalculator.compute_processing_rate(60, 1800) == 120.0

        # 경계 조건
        assert StatisticsCalculator.compute_processing_rate(100, 0) == 0.0
        assert StatisticsCalculator.compute_processing_rate(0, 3600) == 0.0
        assert StatisticsCalculator.compute_processing_rate(100, -10) == 0.0

    def test_compute_average_timing(self):
        """평균 타이밍 계산 테스트"""
        timings = [
            {"type": "dong", "duration": 10.0},
            {"type": "dong", "duration": 20.0},
            {"type": "dong", "duration": 30.0},
            {"type": "complex", "duration": 5.0},
            {"type": "complex", "duration": 15.0},
        ]

        # 동 타이밍 평균
        avg_dong = StatisticsCalculator.compute_average_timing(timings, "dong")
        assert avg_dong == 20.0  # (10 + 20 + 30) / 3

        # 단지 타이밍 평균
        avg_complex = StatisticsCalculator.compute_average_timing(timings, "complex")
        assert avg_complex == 10.0  # (5 + 15) / 2

        # 존재하지 않는 유형
        avg_nonexistent = StatisticsCalculator.compute_average_timing(timings, "nonexistent")
        assert avg_nonexistent == 0.0

        # limit 테스트
        timings_extended = timings * 3  # 15개 데이터
        avg_with_limit = StatisticsCalculator.compute_average_timing(
            timings_extended, "dong", limit=5
        )
        # 마지막 5개 동 타이밍의 평균: (20 + 30 + 10 + 20 + 30) / 5 = 22.0
        assert abs(avg_with_limit - 22.0) < 0.1

    def test_compute_error_rate(self):
        """에러율 계산 테스트"""
        # 정상적인 경우
        # 10개 에러 / 100개 작업 = 10%
        assert StatisticsCalculator.compute_error_rate(10, 100) == 10.0
        # 5개 에러 / 50개 작업 = 10%
        assert StatisticsCalculator.compute_error_rate(5, 50) == 10.0

        # 경계 조건
        assert StatisticsCalculator.compute_error_rate(0, 100) == 0.0
        assert StatisticsCalculator.compute_error_rate(10, 0) == 0.0
        assert StatisticsCalculator.compute_error_rate(0, 0) == 0.0

    def test_format_duration(self):
        """시간 형식화 테스트"""
        # 초
        assert StatisticsCalculator.format_duration(30) == "30초"
        assert StatisticsCalculator.format_duration(59) == "59초"

        # 분
        assert StatisticsCalculator.format_duration(60) == "1분"
        assert StatisticsCalculator.format_duration(90) == "2분"
        assert StatisticsCalculator.format_duration(3599) == "60분"

        # 시간
        assert StatisticsCalculator.format_duration(3600) == "1.0시간"
        assert StatisticsCalculator.format_duration(5400) == "1.5시간"
        assert StatisticsCalculator.format_duration(86399) == "24.0시간"

        # 일
        assert StatisticsCalculator.format_duration(86400) == "1.0일"
        assert StatisticsCalculator.format_duration(172800) == "2.0일"

        # 소수점 처리
        assert StatisticsCalculator.format_duration(90.5) == "2분"
        assert StatisticsCalculator.format_duration(3660) == "1.0시간"

    @patch("time.time")
    def test_calculate_comprehensive_stats(self, mock_time):
        """종합 통계 계산 테스트"""
        # 현재 시간 설정
        mock_time.return_value = 1000.0

        stats = {
            "start_time": 0.0,  # 1000초 경과
            "completed_dongs": 5,
            "total_dongs": 10,
            "completed_complexes": 50,
            "total_complexes": 100,
            "collected_transactions": 500,
            "error_count": 2,
            "rate_limiter_delay": 3.5,
        }

        timings = [
            {"type": "dong", "duration": 10.0, "complexes": 10, "transactions": 100},
            {"type": "dong", "duration": 20.0, "complexes": 10, "transactions": 100},
            {"type": "complex", "duration": 5.0, "transactions": 20},
            {"type": "complex", "duration": 15.0, "transactions": 30},
        ]

        result = StatisticsCalculator.calculate_comprehensive_stats(stats, timings)

        # 기본 정보 확인
        assert result["elapsed_time_seconds"] == 1000.0
        assert (
            result["elapsed_time_formatted"] == "17분"
        )  # 1000초 / 60 = 16.666... -> 반올림하여 17분

        # 진행률 확인
        assert result["dong_progress_percent"] == 50.0
        assert result["completed_dongs"] == 5
        assert result["total_dongs"] == 10
        assert result["remaining_dongs"] == 5

        assert result["complex_progress_percent"] == 50.0
        assert result["completed_complexes"] == 50
        assert result["total_complexes"] == 100
        assert result["remaining_complexes"] == 50

        # 수집된 데이터
        assert result["collected_transactions"] == 500

        # 성능 지표
        # 시간당 처리량: 50개 단지 / 1000초 * 3600 = 180개/시간
        assert abs(result["complexes_per_hour"] - 180.0) < 0.1
        # 시간당 거래: 500개 거래 / 1000초 * 3600 = 1800개/시간
        assert abs(result["transactions_per_hour"] - 1800.0) < 0.1

        # 평균 처리 시간
        assert result["avg_dong_time_seconds"] == 15.0  # (10 + 20) / 2
        assert result["avg_complex_time_seconds"] == 10.0  # (5 + 15) / 2

        # ETA 계산
        # 남은 동: 5개, 평균 동 시간: 15초, ETA = 75초
        assert result["eta_seconds"] == 75.0
        assert result["eta_formatted"] == "1분"  # 75초는 1분으로 표시

        # 현재 상태
        assert result["rate_limiter_delay"] == 3.5
        assert result["error_count"] == 2
        # 에러율: 2개 에러 / (5+50개 작업) * 100 = 3.6%
        assert abs(result["error_rate_percent"] - 3.6) < 0.1

        # 마지막 업데이트 시간
        assert "last_updated" in result

    def test_calculate_comprehensive_stats_empty_data(self):
        """빈 데이터로 종합 통계 계산 테스트"""
        empty_stats = {}
        empty_timings = []

        result = StatisticsCalculator.calculate_comprehensive_stats(empty_stats, empty_timings)

        # 모든 값이 0 또는 기본값인지 확인
        assert result["elapsed_time_seconds"] >= 0
        assert result["dong_progress_percent"] == 0.0
        assert result["completed_dongs"] == 0
        assert result["total_dongs"] == 0
        assert result["remaining_dongs"] == 0
        assert result["complex_progress_percent"] == 0.0
        assert result["completed_complexes"] == 0
        assert result["total_complexes"] == 0
        assert result["remaining_complexes"] == 0
        assert result["collected_transactions"] == 0
        assert result["avg_complex_time_seconds"] == 0.0
        assert result["avg_dong_time_seconds"] == 0.0
        assert result["complexes_per_hour"] == 0.0
        assert result["transactions_per_hour"] == 0.0
        assert result["rate_limiter_delay"] == 2.5  # 기본값
        assert result["error_count"] == 0
        assert result["error_rate_percent"] == 0.0
        assert result["eta_seconds"] == 0.0
        assert result["eta_formatted"] == "계산 중..."

    def test_calculate_comprehensive_stats_with_zero_start_time(self):
        """start_time이 0일 때 종합 통계 계산 테스트"""
        stats = {
            "start_time": 0,  # start_time이 0인 경우
            "completed_dongs": 1,
            "total_dongs": 10,
        }

        with patch("time.time", return_value=1000):
            result = StatisticsCalculator.calculate_comprehensive_stats(stats, [])

        # start_time이 0이면 현재 시간을 사용
        assert result["elapsed_time_seconds"] >= 0

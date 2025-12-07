"""
네이버 부동산 API 성능 테스트

API 응답 시간, 성공률, Rate Limiting 효율성 등을 측정
"""

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.rate_limiter import AdaptiveRateLimiter


@dataclass
class PerformanceMetrics:
    """성능 측정을 위한 데이터 클래스"""

    request_times: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    rate_limit_hits: int = 0
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    data_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def total_requests(self) -> int:
        return self.success_count + self.error_count

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.success_count / self.total_requests) * 100

    @property
    def avg_response_time(self) -> float:
        if not self.request_times:
            return 0.0
        return sum(self.request_times) / len(self.request_times)

    @property
    def max_response_time(self) -> float:
        if not self.request_times:
            return 0.0
        return max(self.request_times)

    @property
    def min_response_time(self) -> float:
        if not self.request_times:
            return 0.0
        return min(self.request_times)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds

    @property
    def avg_memory_usage_mb(self) -> float:
        if not self.memory_usage_mb:
            return 0.0
        return sum(self.memory_usage_mb) / len(self.memory_usage_mb)

    @property
    def max_memory_usage_mb(self) -> float:
        if not self.memory_usage_mb:
            return 0.0
        return max(self.memory_usage_mb)


class PerformanceMonitor:
    """성능 모니터링 클래스"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()

    def start_monitoring(self):
        """모니터링 시작"""
        self.metrics.start_time = datetime.now()
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        self.metrics.end_time = datetime.now()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def _monitor_resources(self):
        """리소스 사용량 모니터링"""
        while self.monitoring:
            try:
                # 메모리 사용량 (MB)
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.metrics.memory_usage_mb.append(memory_mb)

                # CPU 사용량 (%)
                cpu_percent = self.process.cpu_percent()
                self.metrics.cpu_usage_percent.append(cpu_percent)

                time.sleep(0.5)  # 0.5초 간격으로 측정
            except Exception:
                break

    def record_request(self, response_time: float, success: bool, is_rate_limit: bool = False):
        """요청 결과 기록"""
        self.metrics.request_times.append(response_time)
        if success:
            self.metrics.success_count += 1
        else:
            self.metrics.error_count += 1
            if is_rate_limit:
                self.metrics.rate_limit_hits += 1

    def record_data_processed(self, size: int):
        """처리된 데이터 크기 기록"""
        self.metrics.data_processed += size

    def get_report(self) -> Dict[str, Any]:
        """성능 보고서 생성"""
        return {
            "요약": {
                "총 요청 수": self.metrics.total_requests,
                "성공률": f"{self.metrics.success_rate:.2f}%",
                "요청/초": f"{self.metrics.requests_per_second:.2f}",
                "처리된 데이터": f"{self.metrics.data_processed:,} 바이트",
            },
            "응답 시간": {
                "평균": f"{self.metrics.avg_response_time:.3f}초",
                "최소": f"{self.metrics.min_response_time:.3f}초",
                "최대": f"{self.metrics.max_response_time:.3f}초",
            },
            "리소스 사용": {
                "평균 메모리": f"{self.metrics.avg_memory_usage_mb:.2f}MB",
                "최대 메모리": f"{self.metrics.max_memory_usage_mb:.2f}MB",
                "실행 시간": f"{self.metrics.duration_seconds:.2f}초",
            },
            "오류": {
                "실패 요청": self.metrics.error_count,
                "Rate Limit 적중": self.metrics.rate_limit_hits,
            },
        }


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig.from_env()


@pytest.fixture
def crawler(config):
    """테스트용 크롤러"""
    return NaverRealEstateCrawler(config)


@pytest.fixture
def monitor():
    """성능 모니터"""
    return PerformanceMonitor()


class TestNaverAPIPerformance:
    """네이버 API 성능 테스트 클래스"""

    @contextmanager
    def measure_request_time(self, monitor: PerformanceMonitor):
        """요청 시간 측정 컨텍스트 매니저"""
        start_time = time.time()
        try:
            yield
            response_time = time.time() - start_time
            monitor.record_request(response_time, success=True)
        except Exception as e:
            response_time = time.time() - start_time
            is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()
            monitor.record_request(response_time, success=False, is_rate_limit=is_rate_limit)
            raise

    def test_api_response_time_single_request(self, crawler, monitor):
        """단일 API 요청 응답 시간 테스트"""
        monitor.start_monitoring()

        try:
            with self.measure_request_time(monitor):
                # 강남구 단지 목록 조회
                result = crawler.fetch_complex_list(
                    cortar_no="1168010600",  # 강남구
                    bounds={
                        "min_lat": 37.48,
                        "max_lat": 37.52,
                        "min_lng": 127.02,
                        "max_lng": 127.06,
                    },
                )
                monitor.record_data_processed(len(str(result)))

        finally:
            monitor.stop_monitoring()

        # 성능 기준 검증
        assert monitor.metrics.avg_response_time <= 5.0, "API 응답 시간이 5초를 초과했습니다"
        assert monitor.metrics.success_rate == 100.0, "단일 요청이 실패했습니다"

        print("\n[단일 요청 응답 시간 테스트 결과]")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_consecutive_requests_success_rate(self, crawler, monitor):
        """연속 100회 요청 성공률 테스트"""
        monitor.start_monitoring()

        # 테스트용 법정동 코드 목록 (서울시 5개구)
        test_dongs = [
            ("1168010600", "강남구"),  # 강남구
            ("1165010300", "서초구"),  # 서초구
            ("1171010100", "송파구"),  # 송파구
            ("1156010700", "강동구"),  # 강동구
            ("1153010300", "광진구"),  # 광진구
        ]

        try:
            for i in range(100):
                # 라운드 로빈 방식으로 동 선택
                dong_code, dong_name = test_dongs[i % len(test_dongs)]

                try:
                    with self.measure_request_time(monitor):
                        result = crawler.fetch_complex_list(
                            cortar_no=dong_code,
                            bounds={
                                "min_lat": 37.4,
                                "max_lat": 37.7,
                                "min_lng": 126.9,
                                "max_lng": 127.2,
                            },
                        )
                        monitor.record_data_processed(len(str(result)))

                        # Rate limiting 적용
                        time.sleep(1)  # 1초 간격

                except Exception:
                    # 실패 시에도 다음 요청 계속
                    continue

        finally:
            monitor.stop_monitoring()

        # 성능 기준 검증
        assert (
            monitor.metrics.success_rate >= 95.0
        ), f"성공률 {monitor.metrics.success_rate:.2f}%가 95% 미만입니다"
        assert monitor.metrics.avg_response_time <= 5.0, "평균 응답 시간이 5초를 초과했습니다"

        print("\n[연속 100회 요청 성공률 테스트 결과]")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_rate_limiting_efficiency(self, crawler, monitor):
        """Rate Limiting 효율성 측정 테스트"""
        # AdaptiveRateLimiter 테스트
        rate_limiter = AdaptiveRateLimiter()
        # 테스트를 위해 더 짧은 지연 시간으로 설정
        rate_limiter.current_delay = 0.1
        rate_limiter.min_delay = 0.05
        rate_limiter.max_delay = 2.0

        monitor.start_monitoring()

        try:
            # 50개의 빠른 요청 전송
            for i in range(50):
                try:
                    start_time = time.time()
                    result = crawler.fetch_complex_list(
                        cortar_no="1168010600",
                        bounds={
                            "min_lat": 37.5,
                            "max_lat": 37.52,
                            "min_lng": 127.03,
                            "max_lng": 127.05,
                        },
                    )
                    response_time = time.time() - start_time

                    monitor.record_request(response_time, success=True)
                    monitor.record_data_processed(len(str(result)))

                    # Rate limiter 적용
                    rate_limiter.wait()

                except Exception as e:
                    response_time = time.time() - start_time
                    is_rate_limit = "429" in str(e)
                    monitor.record_request(
                        response_time, success=False, is_rate_limit=is_rate_limit
                    )

                    if is_rate_limit:
                        rate_limiter.on_rate_limit_error()

        finally:
            monitor.stop_monitoring()

        # Rate limiting 효율성 검증
        assert (
            monitor.metrics.rate_limit_hits < 10
        ), f"Rate Limit 적중 횟수 {monitor.metrics.rate_limit_hits}가 너무 많습니다"

        print("\n[Rate Limiting 효율성 테스트 결과]")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))
        print(f"\nRate Limiter 최종 지연 시간: {rate_limiter.current_delay:.2f}초")

    def test_large_data_processing_speed(self, crawler, monitor):
        """대용량 데이터 처리 속도 측정 테스트"""
        monitor.start_monitoring()

        try:
            # 여러 구의 데이터 수집 (대용량)
            districts = [
                ("1168010600", "강남구"),
                ("1165010300", "서초구"),
                ("1171010100", "송파구"),
                ("1156010700", "강동구"),
                ("1153010300", "광진구"),
                ("1154510100", "동대문구"),
                ("1159011700", "마포구"),
                ("1144010300", "서대문구"),
                ("1141010100", "종로구"),
                ("1150010100", "성북구"),
            ]

            total_complexes = []

            for dong_code, dong_name in districts:
                with self.measure_request_time(monitor):
                    result = crawler.fetch_complex_list(
                        cortar_no=dong_code,
                        bounds={
                            "min_lat": 37.4,
                            "max_lat": 37.7,
                            "min_lng": 126.8,
                            "max_lng": 127.3,
                        },
                    )

                    if isinstance(result, list) and result:
                        total_complexes.extend(result)
                        monitor.record_data_processed(len(str(result)))
                    elif isinstance(result, dict) and "complexList" in result:
                        complexes = result["complexList"]
                        total_complexes.extend(complexes)
                        monitor.record_data_processed(len(str(complexes)))

                # Rate limiting
                time.sleep(1)

        finally:
            monitor.stop_monitoring()

        # 대용량 처리 성능 검증
        assert len(total_complexes) > 0, "수집된 데이터가 없습니다"
        assert monitor.metrics.avg_response_time <= 5.0, "평균 응답 시간이 5초를 초과했습니다"

        print("\n[대용량 데이터 처리 속도 테스트 결과]")
        print(f"총 수집된 단지 수: {len(total_complexes):,}")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_memory_usage_stability(self, crawler, monitor):
        """메모리 사용량 안정성 테스트"""
        monitor.start_monitoring()

        try:
            # 100번의 요청을 통해 메모리 누수 확인
            for i in range(100):
                try:
                    with self.measure_request_time(monitor):
                        result = crawler.fetch_complex_list(
                            cortar_no="1168010600",
                            bounds={
                                "min_lat": 37.5,
                                "max_lat": 37.52,
                                "min_lng": 127.03,
                                "max_lng": 127.05,
                            },
                        )
                        # 간단한 데이터 처리
                        if result and "complexList" in result:
                            processed_data = len(result["complexList"])
                            monitor.record_data_processed(processed_data * 100)  # 추산

                except Exception:
                    continue

                # 짧은 간격
                time.sleep(0.5)

        finally:
            monitor.stop_monitoring()

        # 메모리 안정성 검증
        if len(monitor.metrics.memory_usage_mb) > 10:
            # 처음 10%와 마지막 10%의 메모리 사용량 비교
            initial_memory = sum(monitor.metrics.memory_usage_mb[:10]) / 10
            final_memory = sum(monitor.metrics.memory_usage_mb[-10:]) / 10
            memory_growth = final_memory - initial_memory

            # 메모리 증가가 50MB 이하면 안정적으로 판단
            assert memory_growth <= 50, f"메모리 증가량 {memory_growth:.2f}MB가 50MB를 초과했습니다"

        print("\n[메모리 사용량 안정성 테스트 결과]")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_single_dong_fast_crawling(self, crawler, monitor):
        """단일 동 빠른 크롤링 시나리오 테스트"""
        monitor.start_monitoring()

        try:
            # 강남구 대치동 (법정동 코드: 1168010800)
            dong_code = "1168010800"
            dong_bounds = {"min_lat": 37.48, "max_lat": 37.52, "min_lng": 127.04, "max_lng": 127.08}

            # 단지 목록 조회
            with self.measure_request_time(monitor):
                complex_result = crawler.fetch_complex_list(dong_code, dong_bounds)

            complexes = []
            if isinstance(complex_result, list) and complex_result:
                complexes = complex_result[:10]  # 처음 10개 단지만
            elif isinstance(complex_result, dict) and "complexList" in complex_result:
                complexes = complex_result["complexList"][:10]  # 처음 10개 단지만

                # 각 단지별 상세 정보 조회
                for complex_info in complexes:
                    try:
                        complex_id = complex_info["hscpNo"]
                        with self.measure_request_time(monitor):
                            detail_result = crawler.fetch_complex_detail(complex_id)
                            monitor.record_data_processed(len(str(detail_result)))
                    except Exception:
                        continue

                    # Rate limiting
                    time.sleep(0.5)

        finally:
            monitor.stop_monitoring()

        # 단일 동 크롤링 성능 검증
        assert monitor.metrics.success_rate >= 80.0, "단일 동 크롤링 성공률이 80% 미만입니다"

        print("\n[단일 동 빠른 크롤링 시나리오 테스트 결과]")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_multi_dong_concurrent_crawling(self, crawler, monitor):
        """다중 동 동시 크롤링 시나리오 테스트"""
        monitor.start_monitoring()

        # 테스트용 동 목록 (3개 동)
        test_dongs = [("1168010800", "대치동"), ("1168010500", "개포동"), ("1168010100", "역삼동")]

        def crawl_single_dong(dong_data):
            """단일 동 크롤링 함수"""
            dong_code, dong_name = dong_data
            local_monitor = PerformanceMonitor()

            try:
                with self.measure_request_time(local_monitor):
                    result = crawler.fetch_complex_list(
                        cortar_no=dong_code,
                        bounds={
                            "min_lat": 37.48,
                            "max_lat": 37.52,
                            "min_lng": 127.03,
                            "max_lng": 127.08,
                        },
                    )

                # 데이터 크기 계산
                data_size = 0
                if isinstance(result, list):
                    data_size = len(str(result))
                elif isinstance(result, dict):
                    data_size = len(str(result))

                return {
                    "dong_name": dong_name,
                    "success": True,
                    "data_size": data_size,
                    "response_time": local_monitor.metrics.request_times[-1]
                    if local_monitor.metrics.request_times
                    else 0,
                }
            except Exception as e:
                return {
                    "dong_name": dong_name,
                    "success": False,
                    "error": str(e),
                    "response_time": 0,
                }

        try:
            # ThreadPoolExecutor를 사용한 동시 크롤링 (max_workers=3)
            with ThreadPoolExecutor(max_workers=3) as executor:
                # 모든 작업 제출
                futures = [executor.submit(crawl_single_dong, dong) for dong in test_dongs]

                # 결과 수집
                results = []
                for future in as_completed(futures):
                    result = future.result(timeout=30)
                    results.append(result)

                    if result["success"]:
                        monitor.record_request(result["response_time"], True)
                        monitor.record_data_processed(result["data_size"])
                    else:
                        monitor.record_request(0, False)

        finally:
            monitor.stop_monitoring()

        # 다중 동 크롤링 성능 검증
        successful_dongs = sum(1 for r in results if r["success"])
        assert successful_dongs >= 2, f"성공한 동 수 {successful_dongs}가 2개 미만입니다"

        print("\n[다중 동 동시 크롤링 시나리오 테스트 결과]")
        print(f"성공한 동: {successful_dongs}/3")
        for result in results:
            status = "성공" if result["success"] else "실패"
            print(f"- {result['dong_name']}: {status} ({result['response_time']:.3f}초)")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    def test_long_running_stability(self, crawler, monitor):
        """장시간 실행 안정성 테스트"""
        monitor.start_monitoring()

        try:
            # 10분간 지속적인 크롤링 (테스트 목적으로 1분으로 단축)
            test_duration = 60  # 60초
            start_time = time.time()

            # 순환할 동 목록
            dongs = [
                ("1168010600", "강남구"),
                ("1165010300", "서초구"),
                ("1171010100", "송파구"),
            ]
            dong_index = 0
            request_count = 0

            while time.time() - start_time < test_duration:
                dong_code, dong_name = dongs[dong_index % len(dongs)]

                try:
                    with self.measure_request_time(monitor):
                        result = crawler.fetch_complex_list(
                            cortar_no=dong_code,
                            bounds={
                                "min_lat": 37.4,
                                "max_lat": 37.7,
                                "min_lng": 126.9,
                                "max_lng": 127.3,
                            },
                        )
                        monitor.record_data_processed(len(str(result)) if result else 0)

                    request_count += 1

                except Exception:
                    pass

                dong_index += 1
                time.sleep(2)  # 2초 간격

        finally:
            monitor.stop_monitoring()

        # 장시간 실행 안정성 검증
        assert request_count >= 20, f"처리된 요청 수 {request_count}가 20개 미만입니다"
        assert monitor.metrics.success_rate >= 90.0, "장시간 실행 성공률이 90% 미만입니다"

        print("\n[장시간 실행 안정성 테스트 결과]")
        print(f"총 처리 요청: {request_count}")
        print(json.dumps(monitor.get_report(), indent=2, ensure_ascii=False))

    @pytest.mark.integration
    def test_full_performance_suite(self, crawler, monitor):
        """전체 성능 테스트 스위트"""
        print("\n" + "=" * 60)
        print("네이버 API 전체 성능 테스트 시작")
        print("=" * 60)

        # 1. 단일 요청 응답 시간
        print("\n1. 단일 요청 응답 시간 테스트...")
        self.test_api_response_time_single_request(crawler, monitor)

        # 2. 연속 요청 성공률
        print("\n2. 연속 요청 성공률 테스트...")
        self.test_consecutive_requests_success_rate(crawler, monitor)

        # 3. Rate Limiting 효율성
        print("\n3. Rate Limiting 효율성 테스트...")
        self.test_rate_limiting_efficiency(crawler, monitor)

        # 4. 대용량 데이터 처리
        print("\n4. 대용량 데이터 처리 테스트...")
        self.test_large_data_processing_speed(crawler, monitor)

        print("\n" + "=" * 60)
        print("네이버 API 전체 성능 테스트 완료")
        print("=" * 60)


if __name__ == "__main__":
    # 직접 실행 시 테스트 수행
    pytest.main([__file__, "-v", "-s"])

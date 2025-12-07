"""RetryManager 클래스 단위 테스트"""

import pytest
from unittest.mock import Mock
import time

from crawler.api.retry_manager import (
    RetryManager,
    RetryConfig,
    RetryStrategy,
    CircuitBreakerState,
    RetryableError,
    NonRetryableError,
    CircuitBreakerOpenError,
)


class TestRetryConfig:
    """RetryConfig 설정 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.backoff_multiplier == 2.0
        assert config.jitter_enabled is True
        assert config.retryable_status_codes == {429, 500, 502, 503, 504}
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60.0

    def test_custom_config(self):
        """사용자 정의 설정 테스트"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            backoff_multiplier=1.5,
            jitter_enabled=False,
            retryable_status_codes={500, 503},
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=120.0,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.backoff_multiplier == 1.5
        assert config.jitter_enabled is False
        assert config.retryable_status_codes == {500, 503}
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 120.0


class TestRetryManager:
    """RetryManager 핵심 기능 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 RetryConfig"""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # 테스트를 위해 짧게 설정
            max_delay=1.0,
            jitter_enabled=False,  # 테스트의 일관성을 위해 비활성화
        )

    @pytest.fixture
    def retry_manager(self, config):
        """테스트용 RetryManager"""
        return RetryManager(config)

    def test_successful_operation_no_retry(self, retry_manager):
        """성공적인 작업은 재시도하지 않음"""
        mock_func = Mock(return_value={"result": "success"})

        result = retry_manager.execute_with_retry("test_endpoint", mock_func)

        assert result == {"result": "success"}
        assert mock_func.call_count == 1

    def test_retry_on_retryable_error(self, retry_manager):
        """재시도 가능한 에러 발생 시 재시도"""
        mock_func = Mock(
            side_effect=[
                RetryableError("First failure", status_code=429),
                RetryableError("Second failure", status_code=429),
                {"result": "success"},
            ]
        )

        result = retry_manager.execute_with_retry("test_endpoint", mock_func)

        assert result == {"result": "success"}
        assert mock_func.call_count == 3

    def test_no_retry_on_non_retryable_error(self, retry_manager):
        """재시도 불가능한 에러 발생 시 즉시 실패"""
        mock_func = Mock(side_effect=NonRetryableError("Bad request", status_code=400))

        with pytest.raises(NonRetryableError):
            retry_manager.execute_with_retry("test_endpoint", mock_func)

        assert mock_func.call_count == 1

    def test_max_attempts_exceeded(self, retry_manager):
        """최대 재시도 횟수 초과 시 실패"""
        mock_func = Mock(side_effect=RetryableError("Always fails", status_code=500))

        with pytest.raises(RetryableError):
            retry_manager.execute_with_retry("test_endpoint", mock_func)

        assert mock_func.call_count == 3  # max_attempts

    def test_exponential_backoff_delays(self, retry_manager):
        """Exponential backoff 지연 시간 테스트"""
        config = RetryConfig(
            max_attempts=4,
            base_delay=0.1,
            max_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter_enabled=False,
        )
        retry_manager = RetryManager(config)

        call_count = []

        def mock_func():
            call_count.append(1)
            if len(call_count) < 4:
                raise RetryableError("Failure", status_code=500)
            return {"result": "success"}

        start_time = time.time()
        retry_manager.execute_with_retry("test_endpoint", mock_func)
        elapsed_time = time.time() - start_time

        # 3번의 재시도 사이에 지연이 있어야 함
        assert elapsed_time > 0.2  # 0.1 + 0.2 (지연 시간)
        assert len(call_count) == 4

    def test_linear_backoff_delays(self):
        """Linear backoff 지연 시간 테스트"""
        config = RetryConfig(
            max_attempts=4,
            base_delay=0.1,
            max_delay=1.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            jitter_enabled=False,
        )
        retry_manager = RetryManager(config)

        call_count = []

        def mock_func():
            call_count.append(1)
            if len(call_count) < 4:
                raise RetryableError("Failure", status_code=500)
            return {"result": "success"}

        start_time = time.time()
        retry_manager.execute_with_retry("test_endpoint", mock_func)
        elapsed_time = time.time() - start_time

        # 3번의 재시도 사이에 지연이 있어야 함
        assert elapsed_time > 0.2  # 0.1 + 0.1 + 0.1 (지연 시간)
        assert len(call_count) == 4


class TestCircuitBreaker:
    """서킷 브레이커 기능 테스트"""

    @pytest.fixture
    def config(self):
        """서킷 브레이커 테스트용 설정"""
        return RetryConfig(
            max_attempts=2,
            base_delay=0.01,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.1,  # 테스트를 위해 짧게 설정
        )

    @pytest.fixture
    def retry_manager(self, config):
        """테스트용 RetryManager"""
        return RetryManager(config)

    def test_circuit_breaker_opens_after_threshold(self, retry_manager):
        """임계치 도달 시 서킷 브레이커 열림"""
        # 첫 번째 엔드포인트
        mock_func = Mock(side_effect=RetryableError("Always fails", status_code=500))

        # 임계치만큼 실패
        for _ in range(3):
            with pytest.raises(RetryableError):
                retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 서킷 브레이커가 열려야 함
        state = retry_manager.get_circuit_state("test_endpoint")
        assert state == CircuitBreakerState.OPEN

        # 서킷 브레이커가 열린 상태에서는 즉시 실패
        with pytest.raises(CircuitBreakerOpenError):
            retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 원래 함수는 호출되지 않아야 함
        assert mock_func.call_count == 6  # 3 failures * 2 attempts each

    def test_circuit_breaker_half_open_after_timeout(self, retry_manager):
        """타임아웃 후 서킷 브레이커 HALF_OPEN 상태로 전환"""
        # 먼저 서킷 브레이커를 염
        mock_func = Mock(side_effect=RetryableError("Always fails", status_code=500))

        for _ in range(3):
            with pytest.raises(RetryableError):
                retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 타임아웃 대기
        time.sleep(0.15)

        # HALF_OPEN 상태에서는 한 번의 시도만 허용
        mock_func.side_effect = [{"result": "success"}]
        result = retry_manager.execute_with_retry("test_endpoint", mock_func)

        assert result == {"result": "success"}

        # 성공했으므로 서킷 브레이커는 닫혀야 함
        state = retry_manager.get_circuit_state("test_endpoint")
        assert state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_reopens_on_half_open_failure(self, retry_manager):
        """HALF_OPEN 상태에서 실패 시 다시 열림"""
        # 먼저 서킷 브레이커를 염
        mock_func = Mock(side_effect=RetryableError("Always fails", status_code=500))

        for _ in range(3):
            with pytest.raises(RetryableError):
                retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 타임아웃 대기
        time.sleep(0.15)

        # HALF_OPEN 상태에서 실패
        with pytest.raises(RetryableError):
            retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 다시 열려야 함
        state = retry_manager.get_circuit_state("test_endpoint")
        assert state == CircuitBreakerState.OPEN


class TestFallback:
    """Fallback 기능 테스트"""

    @pytest.fixture
    def config_with_fallback(self):
        """Fallback 테스트용 설정"""
        return RetryConfig(
            max_attempts=2,
            base_delay=0.01,
            fallback_endpoints={"primary": ["fallback1", "fallback2"], "secondary": ["fallback3"]},
        )

    @pytest.fixture
    def retry_manager(self, config_with_fallback):
        """테스트용 RetryManager"""
        return RetryManager(config_with_fallback)

    def test_fallback_to_secondary_on_primary_failure(self, retry_manager):
        """주 엔드포인트 실패 시 fallback으로 전환"""
        primary_func = Mock(side_effect=RetryableError("Primary fails", status_code=500))
        fallback_func = Mock(return_value={"result": "fallback success"})

        # fallback 함수 등록
        retry_manager.register_fallback_func("fallback1", fallback_func)

        result = retry_manager.execute_with_retry("primary", primary_func)

        assert result == {"result": "fallback success"}
        assert primary_func.call_count == 2  # max_attempts
        assert fallback_func.call_count == 1

    def test_fallback_exhaustion(self, retry_manager):
        """모든 fallback 실패 시 최종 실패"""
        primary_func = Mock(side_effect=RetryableError("Primary fails", status_code=500))
        fallback1_func = Mock(side_effect=RetryableError("Fallback1 fails", status_code=500))
        fallback2_func = Mock(side_effect=RetryableError("Fallback2 fails", status_code=500))

        # fallback 함수 등록
        retry_manager.register_fallback_func("fallback1", fallback1_func)
        retry_manager.register_fallback_func("fallback2", fallback2_func)

        with pytest.raises(RetryableError):
            retry_manager.execute_with_retry("primary", primary_func)

        # 모든 함수가 호출되어야 함
        assert primary_func.call_count == 2
        assert fallback1_func.call_count == 2
        assert fallback2_func.call_count == 2

    def test_no_fallback_for_non_retryable_error(self, retry_manager):
        """재시도 불가능한 에러는 fallback 사용 안 함"""
        primary_func = Mock(side_effect=NonRetryableError("Bad request", status_code=400))
        fallback_func = Mock(return_value={"result": "fallback success"})

        retry_manager.register_fallback_func("fallback1", fallback_func)

        with pytest.raises(NonRetryableError):
            retry_manager.execute_with_retry("primary", primary_func)

        # primary만 호출되어야 함
        assert primary_func.call_count == 1
        assert fallback_func.call_count == 0

    def test_successful_primary_no_fallback(self, retry_manager):
        """주 엔드포인트 성공 시 fallback 사용 안 함"""
        primary_func = Mock(return_value={"result": "primary success"})
        fallback_func = Mock(return_value={"result": "fallback success"})

        retry_manager.register_fallback_func("fallback1", fallback_func)

        result = retry_manager.execute_with_retry("primary", primary_func)

        assert result == {"result": "primary success"}
        assert primary_func.call_count == 1
        assert fallback_func.call_count == 0


class TestStatistics:
    """통계 정보 기능 테스트"""

    @pytest.fixture
    def retry_manager(self):
        """통계 테스트용 RetryManager"""
        config = RetryConfig(max_attempts=3)
        return RetryManager(config)

    def test_statistics_tracking(self, retry_manager):
        """통계 정보 추적 테스트"""
        # 성공 케이스
        success_func = Mock(return_value={"result": "success"})
        retry_manager.execute_with_retry("success_endpoint", success_func)

        # 재시도 후 성공 케이스
        retry_func = Mock(
            side_effect=[
                RetryableError("First failure", status_code=429),
                {"result": "success after retry"},
            ]
        )
        retry_manager.execute_with_retry("retry_endpoint", retry_func)

        # 실패 케이스
        fail_func = Mock(side_effect=RetryableError("Always fails", status_code=500))
        try:
            retry_manager.execute_with_retry("fail_endpoint", fail_func)
        except RetryableError:
            pass

        # 통계 확인
        stats = retry_manager.get_statistics()

        assert stats["success_endpoint"]["total_requests"] == 1
        assert stats["success_endpoint"]["successful_requests"] == 1
        assert stats["success_endpoint"]["failed_requests"] == 0

        assert stats["retry_endpoint"]["total_requests"] == 2
        assert stats["retry_endpoint"]["successful_requests"] == 1
        assert stats["retry_endpoint"]["failed_requests"] == 0

        assert stats["fail_endpoint"]["total_requests"] == 3
        assert stats["fail_endpoint"]["successful_requests"] == 0
        assert stats["fail_endpoint"]["failed_requests"] == 1  # 전체 작업 실패는 1로 계산

    def test_reset_statistics(self, retry_manager):
        """통계 정보 초기화 테스트"""
        # 일부 요청 실행
        mock_func = Mock(return_value={"result": "success"})
        retry_manager.execute_with_retry("test_endpoint", mock_func)

        # 통계 확인
        stats = retry_manager.get_statistics()
        assert "test_endpoint" in stats

        # 통계 초기화
        retry_manager.reset_statistics()

        # 초기화 확인
        stats = retry_manager.get_statistics()
        assert len(stats) == 0

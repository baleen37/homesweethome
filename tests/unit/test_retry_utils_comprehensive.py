"""재시도 유틸리티 테스트

TDD 접근법으로 작성된 재시도 메커니즘 테스트입니다.
"""

import time

from src.crawler.utils.retry import BackoffStrategy, RetryError, RetryState


class TestBackoffStrategy:
    """BackoffStrategy Enum 테스트"""

    def test_backoff_strategy_values(self):
        """백오프 전략 값 확인"""
        assert BackoffStrategy.EXPONENTIAL.value == "exponential"
        assert BackoffStrategy.LINEAR.value == "linear"
        assert BackoffStrategy.FIXED.value == "fixed"
        assert BackoffStrategy.FIBONACCI.value == "fibonacci"


class TestRetryError:
    """RetryError 예외 클래스 테스트"""

    def test_retry_error_creation(self):
        """재시도 오류 생성 테스트"""
        original_error = Exception("Original error")
        retry_error = RetryError(
            message="All retry attempts failed",
            attempts=3,
            last_exception=original_error,
            total_time=5.5,
        )

        assert str(retry_error) == "All retry attempts failed"
        assert retry_error.attempts == 3
        assert retry_error.last_exception == original_error
        assert retry_error.total_time == 5.5

    def test_retry_error_inheritance(self):
        """재시도 오류 상속 관계 테스트"""
        original_error = ValueError("Test error")
        retry_error = RetryError(
            message="Failed", attempts=1, last_exception=original_error, total_time=1.0
        )

        assert isinstance(retry_error, Exception)
        assert retry_error.last_exception == original_error


class TestRetryState:
    """RetryState 클래스 테스트"""

    def test_retry_state_initialization(self):
        """재시도 상태 초기화 테스트"""
        state = RetryState(
            max_attempts=5, base_delay=1.0, max_delay=60.0, strategy=BackoffStrategy.EXPONENTIAL
        )

        assert state.max_attempts == 5
        assert state.base_delay == 1.0
        assert state.max_delay == 60.0
        assert state.strategy == BackoffStrategy.EXPONENTIAL
        assert state.attempts == 0
        assert state.total_time == 0.0

    def test_retry_state_should_retry(self):
        """재시도 여부 확인 테스트"""
        state = RetryState(
            max_attempts=3, base_delay=1.0, max_delay=10.0, strategy=BackoffStrategy.LINEAR
        )

        # 초기 상태에서는 재시도 가능
        assert state.should_retry()

        # 시도 횟수 증가
        state.record_attempt()
        assert state.attempts == 1
        assert state.should_retry()

        state.record_attempt()
        assert state.attempts == 2
        assert state.should_retry()

        # 최대 시도 횟수 도달
        state.record_attempt()
        assert state.attempts == 3
        assert not state.should_retry()

    def test_retry_state_delay_calculation(self):
        """지연 시간 계산 테스트"""
        # 지수 백오프
        state = RetryState(
            max_attempts=5, base_delay=1.0, max_delay=10.0, strategy=BackoffStrategy.EXPONENTIAL
        )

        # 지연 시간 계산
        delay1 = state.get_delay()
        assert delay1 >= 1.0  # 기본 지연 이상

        state.record_attempt()
        delay2 = state.get_delay()
        assert delay2 >= delay1  # 증가해야 함

        # 선형 백오프
        state_linear = RetryState(
            max_attempts=5, base_delay=1.0, max_delay=5.0, strategy=BackoffStrategy.LINEAR
        )

        delay_linear1 = state_linear.get_delay()
        assert delay_linear1 == 1.0

        state_linear.record_attempt()
        delay_linear2 = state_linear.get_delay()
        assert delay_linear2 == 2.0

        # 고정 지연
        state_fixed = RetryState(
            max_attempts=5, base_delay=2.0, max_delay=10.0, strategy=BackoffStrategy.FIXED
        )

        assert state_fixed.get_delay() == 2.0
        state_fixed.record_attempt()
        assert state_fixed.get_delay() == 2.0

    def test_retry_state_time_tracking(self):
        """시간 추적 테스트"""
        state = RetryState(
            max_attempts=3, base_delay=0.1, max_delay=1.0, strategy=BackoffStrategy.FIXED
        )

        # 시도 기록
        state.record_attempt()
        time.sleep(0.1)  # 짧은 지연
        state.record_attempt()

        total_time = state.get_total_time()
        assert total_time > 0
        assert total_time < 1.0  # 1초보다는 작아야 함

    def test_retry_state_jitter(self):
        """지터(jitter) 테스트"""
        state = RetryState(
            max_attempts=5,
            base_delay=1.0,
            max_delay=10.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
        )

        # 지터가 있는 경우, 여러 번 계산해도 약간의 변동이 있어야 함
        delays = [state.get_delay() for _ in range(10)]
        assert len(set(delays)) > 1  # 모든 지연 시간이 동일하지 않아야 함

        # 지터가 없는 경우
        state_no_jitter = RetryState(
            max_attempts=5,
            base_delay=1.0,
            max_delay=10.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False,
        )

        delays_no_jitter = [state_no_jitter.get_delay() for _ in range(10)]
        assert len(set(delays_no_jitter)) == 1  # 모든 지연 시간이 동일해야 함

    def test_retry_state_max_delay_limit(self):
        """최대 지연 시간 제한 테스트"""
        state = RetryState(
            max_attempts=10, base_delay=1.0, max_delay=5.0, strategy=BackoffStrategy.EXPONENTIAL
        )

        # 여러 번 시도해도 최대 지연 시간을 초과하지 않아야 함
        for _ in range(5):
            state.record_attempt()

        delay = state.get_delay()
        assert delay <= 5.0

    def test_fibonacci_backoff(self):
        """피보나치 백오프 테스트"""
        state = RetryState(
            max_attempts=10, base_delay=1.0, max_delay=100.0, strategy=BackoffStrategy.FIBONACCI
        )

        delays = []
        for i in range(5):
            delays.append(state.get_delay())
            state.record_attempt()

        # 피보나치 수열: 1, 1, 2, 3, 5, ...
        assert delays[0] == 1.0
        assert delays[1] == 1.0
        assert delays[2] == 2.0
        assert delays[3] == 3.0
        assert delays[4] == 5.0

    def test_retry_state_reset(self):
        """재시도 상태 초기화 테스트"""
        state = RetryState(
            max_attempts=3, base_delay=1.0, max_delay=10.0, strategy=BackoffStrategy.EXPONENTIAL
        )

        # 상태 변경
        state.record_attempt()
        state.record_attempt()

        assert state.attempts == 2
        assert not state.should_retry()

        # 초기화
        state.reset()

        assert state.attempts == 0
        assert state.total_time == 0.0
        assert state.should_retry()

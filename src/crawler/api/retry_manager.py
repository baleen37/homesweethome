"""재시도 관리자 모듈

API 호출 안정성을 위한 재시도, fallback, 서킷 브레이커 기능 제공
"""

import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger(__name__)


class RetryStrategy(Enum):
    """재시도 전략"""

    FIXED_DELAY = "fixed_delay"  # 고정 지연
    LINEAR_BACKOFF = "linear_backoff"  # 선형 백오프
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 지수 백오프


class CircuitBreakerState(Enum):
    """서킷 브레이커 상태"""

    CLOSED = "closed"  # 정상 상태 (요청 허용)
    OPEN = "open"  # 개방 상태 (요청 거부)
    HALF_OPEN = "half_open"  # 반개방 상태 (일부 요청 허용)


class RetryableError(Exception):
    """재시도 가능한 에러"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class NonRetryableError(Exception):
    """재시도 불가능한 에러"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CircuitBreakerOpenError(Exception):
    """서킷 브레이커가 열려있음"""

    pass


@dataclass
class RetryConfig:
    """재시도 설정"""

    # 기본 재시도 설정
    max_attempts: int = 3
    base_delay: float = 1.0  # 초
    max_delay: float = 60.0  # 초
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0
    jitter_enabled: bool = True  # 지연 시간에 무작위성 추가

    # 재시도 가능한 HTTP 상태 코드
    retryable_status_codes: Set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})

    # 서킷 브레이커 설정
    circuit_breaker_threshold: int = 5  # 연속 실패 임계치
    circuit_breaker_timeout: float = 60.0  # 초

    # Fallback 엔드포인트 설정
    fallback_endpoints: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CircuitBreakerInfo:
    """서킷 브레이커 정보"""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    next_attempt_time: Optional[float] = None


@dataclass
class EndpointStatistics:
    """엔드포인트 통계"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    circuit_breaker_opened_count: int = 0
    fallback_used_count: int = 0


class RetryManager:
    """재시도 관리자

    API 호출의 안정성을 보장하기 위해 재시도, fallback, 서킷 브레이커 기능을 제공합니다.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """초기화

        Args:
            config: 재시도 설정. None이면 기본 설정 사용
        """
        self.config = config or RetryConfig()
        self.logger = logger.bind(component="RetryManager")

        # 서킷 브레이커 상태 관리
        self._circuit_breakers: Dict[str, CircuitBreakerInfo] = defaultdict(
            lambda: CircuitBreakerInfo()
        )

        # Fallback 함수 레지스트리
        self._fallback_funcs: Dict[str, Callable] = {}

        # 통계 정보
        self._statistics: Dict[str, EndpointStatistics] = defaultdict(lambda: EndpointStatistics())

    def register_fallback_func(self, endpoint: str, func: Callable):
        """Fallback 함수 등록

        Args:
            endpoint: 엔드포인트 이름
            func: Fallback 함수
        """
        self._fallback_funcs[endpoint] = func
        self.logger.info("Fallback function registered", endpoint=endpoint)

    def execute_with_retry(self, endpoint: str, func: Callable, *args, **kwargs) -> Any:
        """재시도와 fallback을 포함하여 함수 실행

        Args:
            endpoint: 엔드포인트 이름
            func: 실행할 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            CircuitBreakerOpenError: 서킷 브레이커가 열려있을 때
            Exception: 모든 재시도와 fallback이 실패했을 때
        """
        # 통계 초기화
        stats = self._statistics[endpoint]
        initial_requests = stats.total_requests

        # 서킷 브레이커 확인
        if not self._can_execute(endpoint):
            stats.circuit_breaker_opened_count += 1
            raise CircuitBreakerOpenError(f"Circuit breaker is open for endpoint: {endpoint}")

        # 주 엔드포인트 시도
        try:
            result = self._execute_with_attempts(endpoint, func, *args, **kwargs)

            # 성공 처리
            stats.total_requests = initial_requests + stats.total_retries + 1
            stats.successful_requests += 1
            self._record_success(endpoint)
            return result

        except Exception as e:
            # 실패 처리
            stats.total_requests = initial_requests + stats.total_retries
            stats.failed_requests += 1
            self._record_failure(endpoint)

            # 재시도 불가능한 에러이면 즉시 실패
            if isinstance(e, NonRetryableError):
                raise e

            # Fallback 시도
            if endpoint in self.config.fallback_endpoints:
                return self._execute_fallbacks(endpoint, *args, **kwargs)

            # Fallback이 없으면 원래 에러를 다시 발생
            raise e

    def _execute_with_attempts(self, endpoint: str, func: Callable, *args, **kwargs) -> Any:
        """지정된 횟수만큼 재시도하며 함수 실행

        Args:
            endpoint: 엔드포인트 이름
            func: 실행할 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과
        """
        last_exception = None
        stats = self._statistics[endpoint]

        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)

                # 성공하면 로그 기록
                if attempt > 0:
                    self.logger.info(
                        "Operation succeeded after retries",
                        endpoint=endpoint,
                        attempt=attempt + 1,
                        max_attempts=self.config.max_attempts,
                    )

                return result

            except Exception as e:
                last_exception = e
                stats.total_retries += 1

                # 재시도 가능 여부 확인
                if not self._is_retryable_error(e):
                    self.logger.warning(
                        "Non-retryable error occurred",
                        endpoint=endpoint,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    raise NonRetryableError(str(e), getattr(e, "status_code", None))

                # 마지막 시도가 아니면 지연
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.info(
                        "Retrying after delay",
                        endpoint=endpoint,
                        attempt=attempt + 1,
                        max_attempts=self.config.max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)

        # 모든 시도 실패
        self.logger.error(
            "All retry attempts failed",
            endpoint=endpoint,
            max_attempts=self.config.max_attempts,
            last_error=str(last_exception),
        )
        raise RetryableError(
            f"All {self.config.max_attempts} attempts failed: {str(last_exception)}",
            getattr(last_exception, "status_code", None),
        )

    def _execute_fallbacks(self, endpoint: str, *args, **kwargs) -> Any:
        """Fallback 엔드포인트들 시도

        Args:
            endpoint: 기본 엔드포인트 이름
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            Fallback 함수 실행 결과
        """
        fallback_endpoints = self.config.fallback_endpoints[endpoint]
        stats = self._statistics[endpoint]

        for fallback_endpoint in fallback_endpoints:
            if fallback_endpoint not in self._fallback_funcs:
                self.logger.warning(
                    "Fallback function not found", fallback_endpoint=fallback_endpoint
                )
                continue

            try:
                self.logger.info(
                    "Trying fallback endpoint",
                    primary_endpoint=endpoint,
                    fallback_endpoint=fallback_endpoint,
                )

                fallback_func = self._fallback_funcs[fallback_endpoint]
                result = self._execute_with_attempts(
                    fallback_endpoint, fallback_func, *args, **kwargs
                )

                stats.fallback_used_count += 1
                self.logger.info(
                    "Fallback endpoint succeeded",
                    primary_endpoint=endpoint,
                    fallback_endpoint=fallback_endpoint,
                )
                return result

            except Exception as e:
                self.logger.warning(
                    "Fallback endpoint failed",
                    primary_endpoint=endpoint,
                    fallback_endpoint=fallback_endpoint,
                    error=str(e),
                )
                continue

        # 모든 fallback 실패
        raise RetryableError(f"All fallback endpoints failed for {endpoint}")

    def _calculate_delay(self, attempt: int) -> float:
        """재시도 지연 시간 계산

        Args:
            attempt: 현재 시도 횟수 (0부터 시작)

        Returns:
            지연 시간 (초)
        """
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay

        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (1 + attempt)

        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier**attempt)

        else:
            delay = self.config.base_delay

        # 최대 지연 시간 제한
        delay = min(delay, self.config.max_delay)

        # Jitter 추가 (요청 분산 효과)
        if self.config.jitter_enabled:
            # 0.8 ~ 1.2 사이의 무작위 배수 적용
            jitter_factor = 0.8 + random.random() * 0.4
            delay = delay * jitter_factor

        return delay

    def _is_retryable_error(self, error: Exception) -> bool:
        """에러가 재시도 가능한지 확인

        Args:
            error: 발생한 에러

        Returns:
            재시도 가능 여부
        """
        # 이미 타입이 정해진 경우
        if isinstance(error, (RetryableError, NonRetryableError)):
            return isinstance(error, RetryableError)

        # HTTP 상태 코드 기반 판단
        status_code = getattr(error, "status_code", None)
        if status_code is not None:
            return status_code in self.config.retryable_status_codes

        # 타임아웃, 연결 에러 등은 재시도 가능
        error_classes = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        return isinstance(error, error_classes)

    def _can_execute(self, endpoint: str) -> bool:
        """서킷 브레이커 상태에 따라 실행 가능 여부 확인

        Args:
            endpoint: 엔드포인트 이름

        Returns:
            실행 가능 여부
        """
        breaker = self._circuit_breakers[endpoint]

        if breaker.state == CircuitBreakerState.CLOSED:
            return True

        elif breaker.state == CircuitBreakerState.OPEN:
            # 타임아웃 경과 확인
            if breaker.next_attempt_time is not None and time.time() >= breaker.next_attempt_time:
                breaker.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to half-open", endpoint=endpoint)
                return True
            return False

        elif breaker.state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def _record_success(self, endpoint: str):
        """성공 기록 (서킷 브레이커 상태 업데이트)

        Args:
            endpoint: 엔드포인트 이름
        """
        breaker = self._circuit_breakers[endpoint]

        if breaker.state == CircuitBreakerState.HALF_OPEN:
            # HALF_OPEN 상태에서 성공하면 CLOSED로 전환
            breaker.state = CircuitBreakerState.CLOSED
            breaker.failure_count = 0
            self.logger.info("Circuit breaker closed after successful request", endpoint=endpoint)

    def _record_failure(self, endpoint: str):
        """실패 기록 (서킷 브레이커 상태 업데이트)

        Args:
            endpoint: 엔드포인트 이름
        """
        breaker = self._circuit_breakers[endpoint]
        breaker.failure_count += 1
        breaker.last_failure_time = time.time()

        if breaker.state == CircuitBreakerState.CLOSED:
            # 임계치 도달 시 OPEN으로 전환
            if breaker.failure_count >= self.config.circuit_breaker_threshold:
                breaker.state = CircuitBreakerState.OPEN
                breaker.next_attempt_time = time.time() + self.config.circuit_breaker_timeout
                self.logger.warning(
                    "Circuit breaker opened",
                    endpoint=endpoint,
                    failure_count=breaker.failure_count,
                    threshold=self.config.circuit_breaker_threshold,
                )

        elif breaker.state == CircuitBreakerState.HALF_OPEN:
            # HALF_OPEN 상태에서 실패하면 다시 OPEN으로 전환
            breaker.state = CircuitBreakerState.OPEN
            breaker.next_attempt_time = time.time() + self.config.circuit_breaker_timeout
            self.logger.warning(
                "Circuit breaker reopened after half-open failure", endpoint=endpoint
            )

    def get_circuit_state(self, endpoint: str) -> CircuitBreakerState:
        """서킷 브레이커 상태 조회

        Args:
            endpoint: 엔드포인트 이름

        Returns:
            현재 서킷 브레이커 상태
        """
        # OPEN 상태인 경우 타임아웃 확인
        if self._circuit_breakers[endpoint].state == CircuitBreakerState.OPEN:
            self._can_execute(endpoint)  # 상태 업데이트 포함

        return self._circuit_breakers[endpoint].state

    def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """통계 정보 조회

        Returns:
            엔드포인트별 통계 정보
        """
        return {
            endpoint: {
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "total_retries": stats.total_retries,
                "circuit_breaker_opened_count": stats.circuit_breaker_opened_count,
                "fallback_used_count": stats.fallback_used_count,
            }
            for endpoint, stats in self._statistics.items()
        }

    def reset_statistics(self):
        """통계 정보 초기화"""
        self._statistics.clear()
        self.logger.info("Statistics reset")

    def reset_circuit_breaker(self, endpoint: str):
        """특정 엔드포인트의 서킷 브레이커 초기화

        Args:
            endpoint: 엔드포인트 이름
        """
        self._circuit_breakers[endpoint] = CircuitBreakerInfo()
        self.logger.info("Circuit breaker reset", endpoint=endpoint)

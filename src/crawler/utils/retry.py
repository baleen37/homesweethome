"""단순화된 재시도 유틸리티

기본적인 try/except 루프를 사용한 단순한 재시도 기능만 제공합니다.
"""

import time
from typing import Any, Callable, TypeVar, Optional

T = TypeVar("T")


class AdaptiveRateLimiter:
    """간단한 Rate Limiter 구현"""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 10.0, initial_delay: float = 2.0):
        """초기화

        Args:
            min_delay: 최소 지연 시간
            max_delay: 최대 지연 시간
            initial_delay: 초기 지연 시간
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = initial_delay

    def wait(self):
        """현재 지연 시간만큼 대기"""
        time.sleep(self.current_delay)

    def on_success(self):
        """성공 시 지연 시간 감소"""
        self.current_delay = max(self.min_delay, self.current_delay * 0.9)

    def on_error(self):
        """에러 시 지연 시간 증가"""
        self.current_delay = min(self.max_delay, self.current_delay * 1.5)

    def on_rate_limit_error(self):
        """Rate limit 에러 시 최대 지연 시간으로 설정"""
        self.current_delay = self.max_delay


def retry_with_delay(
    func: Callable[..., T],
    max_attempts: int = 3,
    delay: float = 1.0,
    logger: Optional[Any] = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """단순한 재시도 함수

    Args:
        func: 재시도할 함수
        max_attempts: 최대 시도 횟수 (기본값: 3)
        delay: 재시도 간 지연 시간 (초, 기본값: 1.0)
        logger: 로거 객체 (선택사항)
        *args: 함수에 전달할 인자
        **kwargs: 함수에 전달한 키워드 인자

    Returns:
        함수 실행 결과

    Raises:
        Exception: 모든 시도가 실패한 경우 마지막 예외
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:  # 마지막 시도가 아니면
                if logger:
                    logger.warning(
                        "retry_attempt_failed",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        error=str(e),
                        delay=delay,
                    )
                else:
                    print(f"시도 {attempt + 1} 실패: {str(e)}. {delay}초 후 재시도...")
                time.sleep(delay)
            else:
                if logger:
                    logger.error(
                        "retry_all_attempts_failed",
                        max_attempts=max_attempts,
                        final_error=str(last_exception) if last_exception else "Unknown error",
                    )
                else:
                    print(f"모든 시도 ({max_attempts}회) 실패")

    # 모든 시도가 실패하면 마지막 예외를 다시 발생
    assert last_exception is not None
    raise last_exception

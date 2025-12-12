"""단순화된 재시도 유틸리티

기본적인 try/except 루프를 사용한 단순한 재시도 기능만 제공합니다.
"""

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def retry_with_delay(
    func: Callable[..., T], max_attempts: int = 3, delay: float = 1.0, *args: Any, **kwargs: Any
) -> T:
    """단순한 재시도 함수

    Args:
        func: 재시도할 함수
        max_attempts: 최대 시도 횟수 (기본값: 3)
        delay: 재시도 간 지연 시간 (초, 기본값: 1.0)
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
                print(f"시도 {attempt + 1} 실패: {str(e)}. {delay}초 후 재시도...")
                time.sleep(delay)
            else:
                print(f"모든 시도 ({max_attempts}회) 실패")

    # 모든 시도가 실패하면 마지막 예외를 다시 발생
    assert last_exception is not None
    raise last_exception

"""향상된 에러 핸들러 테스트

TDD 접근법으로 작성된 향상된 에러 핸들러 테스트입니다.
"""

import pytest
import time
import threading
from datetime import datetime
from collections import OrderedDict

from src.crawler.utils.enhanced_error_handler import LRUCache, ErrorType, ErrorInfo


class TestLRUCache:
    """LRUCache 클래스 테스트"""

    def test_cache_initialization(self):
        """캐시 초기화 테스트"""
        cache = LRUCache()
        assert cache.max_size == 1000
        assert len(cache) == 0
        assert cache.cache == OrderedDict()

        cache = LRUCache(max_size=100)
        assert cache.max_size == 100

    def test_get_and_set(self):
        """get 및 set 메서드 테스트"""
        cache = LRUCache(max_size=3)

        # 새 항목 설정
        cache.set("key1", 100)
        assert len(cache) == 1
        assert cache.get("key1") == 100

        # 기본값 테스트
        assert cache.get("nonexistent") == 0
        assert cache.get("nonexistent", 5) == 5

        # 기존 항목 업데이트
        cache.set("key1", 200)
        assert cache.get("key1") == 200
        assert len(cache) == 1

    def test_increment(self):
        """increment 메서드 테스트"""
        cache = LRUCache()

        # 새 키 증가
        cache.increment("counter")
        assert cache.get("counter") == 1

        # 기존 키 증가
        cache.increment("counter", 5)
        assert cache.get("counter") == 6

        # 기본 증가값 테스트
        cache.increment("counter2")
        assert cache.get("counter2") == 1

    def test_lru_eviction(self):
        """LRU eviction 정책 테스트"""
        cache = LRUCache(max_size=3)

        # 캐시 채우기
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert len(cache) == 3
        assert list(cache.cache.keys()) == ["a", "b", "c"]

        # 'a'에 접근 (최근 사용으로 변경)
        cache.get("a")
        assert list(cache.cache.keys()) == ["b", "c", "a"]

        # 새 항목 추가 - 'b'가 제거됨 (가장 오래된 항목)
        cache.set("d", 4)
        assert len(cache) == 3
        assert list(cache.cache.keys()) == ["c", "a", "d"]
        assert cache.get("b") == 0  # 'b'는 제거됨

    def test_items_method(self):
        """items 메서드 테스트"""
        cache = LRUCache()

        cache.set("key1", 100)
        cache.set("key2", 200)
        cache.set("key3", 300)

        items = cache.items()
        assert isinstance(items, list)
        assert len(items) == 3
        assert ("key1", 100) in items
        assert ("key2", 200) in items
        assert ("key3", 300) in items

    def test_clear(self):
        """clear 메서드 테스트"""
        cache = LRUCache()

        cache.set("key1", 100)
        cache.set("key2", 200)

        assert len(cache) == 2

        cache.clear()
        assert len(cache) == 0
        assert cache.items() == []

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        cache = LRUCache(max_size=100)
        errors = []

        def writer(thread_id):
            try:
                for i in range(50):
                    key = f"thread{thread_id}_key{i}"
                    cache.set(key, i)
                    cache.increment(f"counter_{thread_id}")
                    time.sleep(0.001)  # 짧은 지연
            except Exception as e:
                errors.append(e)

        def reader(thread_id):
            try:
                for i in range(50):
                    cache.get(f"thread{thread_id}_key{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # 여러 스레드 실행
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=writer, args=(i,))
            t2 = threading.Thread(target=reader, args=(i,))
            threads.extend([t1, t2])

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 에러가 없어야 함
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # 데이터 무결성 확인
        assert len(cache) > 0


class TestErrorType:
    """ErrorType Enum 테스트"""

    def test_error_type_values(self):
        """오류 타입 값 확인"""
        assert ErrorType.NOT_FOUND.value == "not_found"
        assert ErrorType.SERVER_ERROR.value == "server_error"
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.NETWORK_ERROR.value == "network_error"
        assert ErrorType.AUTH_ERROR.value == "auth_error"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.UNKNOWN.value == "unknown"


class TestErrorInfo:
    """ErrorInfo 데이터클래스 테스트"""

    def test_error_info_creation(self):
        """오류 정보 생성 테스트"""
        timestamp = datetime.now()
        error_info = ErrorInfo(
            error_type=ErrorType.NOT_FOUND,
            status_code=404,
            message="Apartment not found",
            timestamp=timestamp,
            apartment_id="APT001",
            retry_count=2,
            is_transient=False,
        )

        assert error_info.error_type == ErrorType.NOT_FOUND
        assert error_info.status_code == 404
        assert error_info.message == "Apartment not found"
        assert error_info.timestamp == timestamp
        assert error_info.apartment_id == "APT001"
        assert error_info.retry_count == 2
        assert error_info.is_transient is False

    def test_error_info_defaults(self):
        """오류 정보 기본값 테스트"""
        timestamp = datetime.now()
        error_info = ErrorInfo(
            error_type=ErrorType.UNKNOWN,
            status_code=None,
            message="Unknown error",
            timestamp=timestamp,
        )

        assert error_info.apartment_id is None
        assert error_info.retry_count == 0
        assert error_info.is_transient is False

    def test_error_info_immutability(self):
        """오류 정보 불변성 테스트"""
        timestamp = datetime.now()
        error_info = ErrorInfo(
            error_type=ErrorType.NOT_FOUND,
            status_code=404,
            message="Not found",
            timestamp=timestamp,
        )

        # frozen=True 이므로 속성 변경 시도 시 에러 발생
        with pytest.raises(Exception):
            error_info.message = "New message"

    def test_error_info_with_transient_error(self):
        """일시적 오류 정보 테스트"""
        error_info = ErrorInfo(
            error_type=ErrorType.RATE_LIMIT,
            status_code=429,
            message="Rate limit exceeded",
            timestamp=datetime.now(),
            is_transient=True,
        )

        assert error_info.is_transient is True
        assert error_info.error_type == ErrorType.RATE_LIMIT
        assert error_info.status_code == 429

    def test_error_info_with_apartment_id(self):
        """아파트 ID 포함 오류 정보 테스트"""
        error_info = ErrorInfo(
            error_type=ErrorType.NOT_FOUND,
            status_code=404,
            message="Invalid apartment ID",
            timestamp=datetime.now(),
            apartment_id="INVALID_ID",
        )

        assert error_info.apartment_id == "INVALID_ID"
        assert error_info.error_type == ErrorType.NOT_FOUND

    def test_error_info_retry_count(self):
        """재시도 횟수 포함 오류 정보 테스트"""
        error_info = ErrorInfo(
            error_type=ErrorType.SERVER_ERROR,
            status_code=500,
            message="Server error",
            timestamp=datetime.now(),
            retry_count=5,
        )

        assert error_info.retry_count == 5
        assert error_info.error_type == ErrorType.SERVER_ERROR

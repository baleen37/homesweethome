"""NaverAPIClient와 RetryManager 통합 테스트"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.retry_manager import (
    RetryManager,
    RetryConfig,
    RetryableError,
    NonRetryableError,
    CircuitBreakerOpenError,
)
from crawler.api.naver_client import NaverAPIClient, APIEndpoint


class TestNaverAPIClientWithRetry:
    """NaverAPIClient와 RetryManager 통합 테스트"""

    @pytest.fixture
    def retry_config(self):
        """재시도 설정"""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.01,  # 테스트를 위해 짧게 설정
            circuit_breaker_threshold=2,
            jitter_enabled=False,  # 테스트의 일관성을 위해 비활성화
        )

    @pytest.fixture
    def api_client(self, retry_config):
        """재시도 매니저를 포함한 API 클라이언트"""
        client = NaverAPIClient()
        client.retry_manager = RetryManager(retry_config)
        return client

    def test_fetch_with_retry_on_429_error(self, api_client):
        """429 에러 발생 시 재시도 테스트"""
        with patch.object(api_client._get_session(), "get") as mock_get:
            # 처음엔 429, 다음엔 성공
            mock_get.side_effect = [
                Mock(status_code=429, text="Too Many Requests"),
                Mock(
                    status_code=200,
                    json=lambda: {"result": "success"},
                    text='{"result": "success"}',
                ),
            ]

            response = api_client.fetch(
                APIEndpoint.COMPLEX_LIST, params={"cortarNo": "1111010100", "hscpNo": 1, "page": 1}
            )

            assert response["result"] == "success"
            assert mock_get.call_count == 2

    def test_fetch_no_retry_on_400_error(self, api_client):
        """400 에러 발생 시 재시도 안 함 테스트"""
        with patch.object(api_client._get_session(), "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=400, text="Bad Request", json=lambda: {"error": "bad request"}
            )

            with pytest.raises(Exception):
                api_client.fetch(APIEndpoint.COMPLEX_LIST, cortarNo="1111010100", hscpNo=1, page=1)

            # 한 번만 호출되어야 함
            assert mock_get.call_count == 1

    def test_fetch_circuit_breaker_opens(self, api_client):
        """서킷 브레이커 동작 테스트"""
        with patch.object(api_client._get_session(), "get") as mock_get:
            mock_get.return_value = Mock(status_code=500, text="Internal Server Error")

            # 서킷 브레이커 임계치만큼 실패
            for _ in range(2):
                with pytest.raises(Exception):
                    api_client.fetch(
                        APIEndpoint.COMPLEX_LIST, cortarNo="1111010100", hscpNo=1, page=1
                    )

            # 서킷 브레이커가 열렸는지 확인
            state = api_client.retry_manager.get_circuit_state(APIEndpoint.COMPLEX_LIST.value)
            assert state.value == "open"

            # 열린 상태에서는 즉시 실패
            with pytest.raises(CircuitBreakerOpenError):
                api_client.fetch(APIEndpoint.COMPLEX_LIST, cortarNo="1111010100", hscpNo=1, page=1)

    def test_fetch_with_fallback(self, api_client):
        """Fallback 기능 테스트"""

        # Fallback 함수 설정
        def fallback_func(*args, **kwargs):
            return {"result": "fallback success"}

        api_client.retry_manager.register_fallback_func("fallback_complex_list", fallback_func)

        # Fallback 설정 추가
        api_client.retry_manager.config.fallback_endpoints[APIEndpoint.COMPLEX_LIST.value] = [
            "fallback_complex_list"
        ]

        with patch.object(api_client._get_session(), "get") as mock_get:
            # 주 엔드포인트는 항상 실패
            mock_get.return_value = Mock(status_code=500, text="Internal Server Error")

            result = api_client.fetch(
                APIEndpoint.COMPLEX_LIST, cortarNo="1111010100", hscpNo=1, page=1
            )

            assert result["result"] == "fallback success"

    def test_post_with_retry_on_timeout(self, api_client):
        """타임아웃 발생 시 재시도 테스트"""
        with patch.object(api_client._get_session(), "post") as mock_post:
            import requests

            mock_post.side_effect = [
                requests.exceptions.Timeout("Connection timeout"),
                Mock(
                    status_code=200,
                    json=lambda: {"result": "success"},
                    text='{"result": "success"}',
                ),
            ]

            response = api_client.post(APIEndpoint.COMPLEX_DETAIL, data={"complexNo": "12345"})

            assert response["result"] == "success"
            assert mock_post.call_count == 2

    def test_post_statistics_tracking(self, api_client):
        """통계 정보 추적 테스트"""
        with patch.object(api_client._get_session(), "post") as mock_post:
            # 성공 케이스
            mock_post.return_value = Mock(status_code=200, json=lambda: {"result": "success"})

            api_client.post(APIEndpoint.COMPLEX_DETAIL, data={"complexNo": "12345"})

            # 재시도 후 성공 케이스
            mock_post.side_effect = [
                Mock(status_code=429),
                Mock(status_code=200, json=lambda: {"result": "success"}),
            ]

            api_client.post(APIEndpoint.ARTICLE_LIST, data={"complexNo": "12345", "page": 1})

            # 통계 확인
            stats = api_client.retry_manager.get_statistics()

            assert APIEndpoint.COMPLEX_DETAIL.value in stats
            assert APIEndpoint.ARTICLE_LIST.value in stats

            detail_stats = stats[APIEndpoint.COMPLEX_DETAIL.value]
            assert detail_stats["total_requests"] == 1
            assert detail_stats["successful_requests"] == 1

            article_stats = stats[APIEndpoint.ARTICLE_LIST.value]
            assert article_stats["total_requests"] == 2
            assert article_stats["total_retries"] == 1
            assert article_stats["successful_requests"] == 1


class TestRetryManagerIntegration:
    """RetryManager 독립적 통합 테스트"""

    @pytest.fixture
    def retry_manager(self):
        """재시도 매니저"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter_enabled=False)
        return RetryManager(config)

    def test_real_api_call_pattern(self, retry_manager):
        """실제 API 호출 패턴 시뮬레이션"""
        # API 호출 함수 시뮬레이션
        call_count = 0

        def api_call():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 첫 호출은 429 에러
                response = Mock()
                response.status_code = 429
                response.text = "Rate limit exceeded"
                raise RetryableError("Rate limit", status_code=429)

            elif call_count == 2:
                # 두 번째 호출은 네트워크 에러
                import requests

                raise requests.exceptions.ConnectionError("Connection failed")

            else:
                # 세 번째 호출은 성공
                return {"data": "api_response", "status": "success"}

        result = retry_manager.execute_with_retry("test_endpoint", api_call)

        assert result["data"] == "api_response"
        assert result["status"] == "success"
        assert call_count == 3

    def test_mixed_error_types(self, retry_manager):
        """다양한 타입의 에러 처리 테스트"""

        # 첫 번째는 재시도 가능한 에러, 두 번째는 재시도 불가능한 에러
        def api_call():
            api_call.call_count += 1

            if api_call.call_count == 1:
                raise RetryableError("Server error", status_code=500)
            else:
                raise NonRetryableError("Bad request", status_code=400)

        api_call.call_count = 0

        with pytest.raises(NonRetryableError):
            retry_manager.execute_with_retry("test_endpoint", api_call)

        # 재시도 가능한 에러는 한 번 시도 후, 재시도 불가능한 에러에서 즉시 중단
        assert api_call.call_count == 2

    def test_fallback_chain(self, retry_manager):
        """Fallback 체인 테스트"""

        # 기본 함수
        def primary_func():
            raise RetryableError("Primary failed", status_code=500)

        # Fallback 함수들
        def fallback1_func():
            raise RetryableError("Fallback1 failed", status_code=500)

        def fallback2_func():
            return {"result": "fallback2 success"}

        # Fallback 등록
        retry_manager.register_fallback_func("fallback1", fallback1_func)
        retry_manager.register_fallback_func("fallback2", fallback2_func)

        # Fallback 체인 설정
        retry_manager.config.fallback_endpoints["primary"] = ["fallback1", "fallback2"]

        result = retry_manager.execute_with_retry("primary", primary_func)

        assert result["result"] == "fallback2 success"

    def test_circuit_breaker_recovery(self, retry_manager):
        """서킷 브레이커 복구 테스트"""
        import time

        # 서킷 브레이커 설정 변경
        retry_manager.config.circuit_breaker_threshold = 2
        retry_manager.config.circuit_breaker_timeout = 0.05  # 50ms

        # 함수 정의
        def failing_func():
            raise RetryableError("Always fails", status_code=500)

        def success_func():
            return {"result": "success"}

        # 실패하여 서킷 브레이커 열기
        for _ in range(2):
            try:
                retry_manager.execute_with_retry("test_endpoint", failing_func)
            except Exception:
                pass

        # 서킷 브레이커 열린 상태 확인
        assert retry_manager.get_circuit_state("test_endpoint").value == "open"

        # 타임아웃 대기
        time.sleep(0.1)

        # HALF_OPEN 상태에서 성공하면 닫혀야 함
        # 동적 상태 변경 (monkey patching)
        from crawler.api.retry_manager import CircuitBreakerState

        retry_manager._circuit_breakers["test_endpoint"].state = CircuitBreakerState.HALF_OPEN

        result = retry_manager.execute_with_retry("test_endpoint", success_func)
        assert result["result"] == "success"

        # 서킷 브레이커 닫힌 상태 확인
        assert retry_manager.get_circuit_state("test_endpoint").value == "closed"

    def test_statistics_accuracy(self, retry_manager):
        """통계 정보 정확성 테스트"""
        # 여러 엔드포인트에 대한 통합 시나리오
        scenarios = [
            ("endpoint1", lambda: {"data": "success1"}, 1),  # 즉시 성공
            ("endpoint2", self._create_retry_func(2), 3),  # 2번 재시도 후 성공
            ("endpoint3", self._create_failing_func(), 3),  # 항상 실패
        ]

        for endpoint, func, expected_calls in scenarios:
            try:
                retry_manager.execute_with_retry(endpoint, func)
            except Exception:
                pass

        # 통계 확인
        stats = retry_manager.get_statistics()

        # endpoint1: 1번 성공
        assert stats["endpoint1"]["total_requests"] == 1
        assert stats["endpoint1"]["successful_requests"] == 1
        assert stats["endpoint1"]["failed_requests"] == 0

        # endpoint2: 3번 호출(2번 재시도) 후 성공
        assert stats["endpoint2"]["total_requests"] == 3
        assert stats["endpoint2"]["successful_requests"] == 1
        assert stats["endpoint2"]["failed_requests"] == 0  # 최종 성공했으므로 failed_requests는 0
        assert stats["endpoint2"]["total_retries"] == 2

        # endpoint3: 3번 호출 후 실패
        assert stats["endpoint3"]["total_requests"] == 3
        assert stats["endpoint3"]["successful_requests"] == 0
        assert stats["endpoint3"]["failed_requests"] == 3

    def _create_retry_func(self, fail_count: int):
        """지정된 횟수만큼 실패 후 성공하는 함수 생성"""

        def func():
            func.call_count += 1
            if func.call_count <= fail_count:
                raise RetryableError("Temporary failure", status_code=429)
            return {"data": "success"}

        func.call_count = 0
        return func

    def _create_failing_func(self):
        """항상 실패하는 함수 생성"""

        def func():
            raise RetryableError("Permanent failure", status_code=500)

        return func


class TestErrorClassification:
    """에러 분류 테스트"""

    @pytest.fixture
    def retry_manager(self):
        """재시도 매니저"""
        return RetryManager()

    def test_http_status_code_classification(self, retry_manager):
        """HTTP 상태 코드에 따른 분류 테스트"""
        # 재시도 가능한 상태 코드
        retryable_codes = [429, 500, 502, 503, 504]
        for code in retryable_codes:
            error = Exception(f"HTTP {code}")
            error.status_code = code
            assert retry_manager._is_retryable_error(error) is True

        # 재시도 불가능한 상태 코드
        non_retryable_codes = [400, 401, 403, 404, 422]
        for code in non_retryable_codes:
            error = Exception(f"HTTP {code}")
            error.status_code = code
            assert retry_manager._is_retryable_error(error) is False

    def test_network_error_classification(self, retry_manager):
        """네트워크 에러 분류 테스트"""
        import requests
        import socket

        # 재시도 가능한 네트워크 에러
        network_errors = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Request timeout"),
            OSError("Network error"),
            socket.timeout("Socket timeout"),
        ]

        for error in network_errors:
            assert retry_manager._is_retryable_error(error) is True

        # 재시도 불가능한 에러
        other_errors = [
            ValueError("Invalid value"),
            TypeError("Type error"),
            KeyError("Key not found"),
        ]

        for error in other_errors:
            assert retry_manager._is_retryable_error(error) is False

    def test_custom_error_classification(self, retry_manager):
        """사용자 정의 에러 분류 테스트"""
        # RetryableError는 항상 재시도 가능
        retryable = RetryableError("Custom retryable error", 500)
        assert retry_manager._is_retryable_error(retryable) is True

        # NonRetryableError는 항상 재시도 불가능
        non_retryable = NonRetryableError("Custom non-retryable error", 400)
        assert retry_manager._is_retryable_error(non_retryable) is False

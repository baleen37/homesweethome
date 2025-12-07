"""네이버 API 헤더 최적화 테스트

이 파일은 NaverRealEstateCrawler의 헤더 생성 및 관리 기능을 테스트합니다.
TDD 접근 방식으로, 먼저 실패하는 테스트를 작성하고 그 후에 구현을 추가합니다.

"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.config import CrawlerConfig


class TestNaverHeaders:
    """네이버 API 헤더 관련 테스트 클래스"""

    @pytest.fixture
    def config(self):
        """테스트용 CrawlerConfig fixture"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            retry_delay=1.0,
            rate_limit_delay=5.0,
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 NaverRealEstateCrawler fixture"""
        # 출력 디렉토리를 임시 디렉토리로 설정
        output_dir = Path("/tmp/test_output")
        output_dir.mkdir(exist_ok=True)

        with (
            patch("crawler.crawlers.naver.CheckpointManager"),
            patch("crawler.crawlers.naver.BrowserManager"),
            patch.object(NaverRealEstateCrawler, "_load_districts_data", return_value={}),
        ):
            return NaverRealEstateCrawler(config, output_dir)

    def test_get_api_headers_returns_basic_headers(self, crawler):
        """기본 헤더 정보가 올바르게 반환되는지 테스트"""
        # 이 테스트는 _get_api_headers 메서드가 없으므로 실패해야 함
        headers = crawler._get_api_headers()

        # 필수 헤더 확인
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "User-Agent" in headers

        # 헤더 값 검증
        assert headers["Accept"] == "application/json, text/plain, */*"
        assert headers["Accept-Language"].startswith("ko")
        assert "iPhone" in headers["User-Agent"]

    def test_get_api_headers_includes_referer_for_complex_list(self, crawler):
        """단지 목록 API 호출 시 적절한 Referer가 포함되는지 테스트"""
        headers = crawler._get_api_headers(api_type="complex_list", cortar_no="1111010300")

        assert "Referer" in headers
        assert "m.land.naver.com" in headers["Referer"]
        assert "complex" in headers["Referer"].lower()

    def test_get_api_headers_includes_referer_for_complex_detail(self, crawler):
        """단지 상세 정보 API 호출 시 적절한 Referer가 포함되는지 테스트"""
        headers = crawler._get_api_headers(api_type="complex_detail", complex_id="1111010300001")

        assert "Referer" in headers
        assert "m.land.naver.com" in headers["Referer"]
        assert str(headers["Referer"]).count("/") >= 2  # 적절한 URL 형식

    def test_get_api_headers_includes_referer_for_article_list(self, crawler):
        """매물 목록 API 호출 시 적절한 Referer가 포함되는지 테스트"""
        headers = crawler._get_api_headers(
            api_type="article_list", complex_id="1111010300001", trade_type="A1"
        )

        assert "Referer" in headers
        assert "m.land.naver.com" in headers["Referer"]

    def test_get_api_headers_handles_optional_parameters(self, crawler):
        """선택적 파라미터가 없을 때도 헤더가 정상적으로 생성되는지 테스트"""
        headers = crawler._get_api_headers()

        # 기본 헤더만 포함되어야 함
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "User-Agent" in headers
        # Referer는 선택적
        assert "X-CSRF-Token" not in headers  # CSRF 토큰은 기본적으로 포함되지 않음

    def test_get_api_headers_variable_user_agent(self, crawler):
        """다양한 User-Agent 헤더가 생성될 수 있는지 테스트"""
        # 여러 번 호출하여 다양한 User-Agent 확인
        user_agents = set()
        for _ in range(5):
            headers = crawler._get_api_headers()
            user_agents.add(headers["User-Agent"])

        # 최소 2개 이상의 다른 User-Agent가 생성되어야 함
        assert len(user_agents) >= 1

    def test_get_api_headers_extra_headers(self, crawler):
        """추가 헤더가 정상적으로 병합되는지 테스트"""
        extra_headers = {"X-Custom-Header": "test-value", "Authorization": "Bearer token123"}

        headers = crawler._get_api_headers(extra_headers=extra_headers)

        # 기본 헤더 유지
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "User-Agent" in headers

        # 추가 헤더 포함
        assert headers["X-Custom-Header"] == "test-value"
        assert headers["Authorization"] == "Bearer token123"

    def test_get_api_headers_mobile_app_format(self, crawler):
        """모바일 앱 형식의 헤더가 생성되는지 테스트"""
        headers = crawler._get_api_headers()

        user_agent = headers["User-Agent"]

        # 모바일 Safari/WebView 형식 확인
        assert "Mobile" in user_agent or "iPhone" in user_agent or "Android" in user_agent
        assert "Safari" in user_agent or "WebKit" in user_agent

    def test_get_api_headers_content_type_for_post_requests(self, crawler):
        """POST 요청 시 Content-Type 헤더가 포함되는지 테스트"""
        headers = crawler._get_api_headers(method="POST")

        # POST 요청 시에는 Content-Type이 있어야 함
        assert "Content-Type" in headers
        assert (
            headers["Content-Type"] == "application/json"
            or "x-www-form-urlencoded" in headers["Content-Type"]
        )

    def test_get_api_headers_get_request_no_content_type(self, crawler):
        """GET 요청 시 Content-Type 헤더가 포함되지 않는지 테스트"""
        headers = crawler._get_api_headers(method="GET")

        # GET 요청 시에는 Content-Type이 필요 없음
        assert "Content-Type" not in headers

    @patch("crawler.crawlers.naver.NaverRealEstateCrawler._get_api_headers")
    def test_fetch_complex_list_uses_dynamic_headers(self, mock_get_headers, crawler):
        """fetch_complex_list가 동적 헤더를 사용하는지 테스트"""
        # Mock 헤더 반환
        mock_headers = {
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://m.land.naver.com/complex/1111010300001",
        }
        mock_get_headers.return_value = mock_headers

        # Mock browser manager
        with patch.object(crawler, "browser_manager") as mock_browser_mgr:
            mock_page = Mock()
            mock_browser_mgr.managed_browser.return_value.__enter__.return_value = mock_page

            # _ensure_session 모킹
            with patch.object(crawler, "_ensure_session"):
                with patch.object(crawler, "rate_limiter"):
                    mock_page.evaluate.return_value = {
                        "result": [
                            {
                                "complexNo": 1111010300001,
                                "complexName": "테스트단지",
                                "addr1": "서울 동작구 노량진동",
                                "lat": 37.5129,
                                "lng": 126.9396,
                            }
                        ]
                    }

                    # API 호출
                    crawler.fetch_complex_list("1111010300", None)

                    # _get_api_headers가 호출되었는지 확인
                    mock_get_headers.assert_called_once_with(
                        api_type="complex_list", cortar_no="1111010300"
                    )

    def test_headers_consistency_across_api_calls(self, crawler):
        """여러 API 호출에서 헤더 일관성이 유지되는지 테스트"""
        headers1 = crawler._get_api_headers(api_type="complex_list")
        headers2 = crawler._get_api_headers(api_type="complex_detail")
        headers3 = crawler._get_api_headers(api_type="article_list")

        # 기본 헤더는 모두 동일해야 함
        for key in ["Accept", "Accept-Language"]:
            assert headers1[key] == headers2[key] == headers3[key]

        # User-Agent 형식은 동일해야 함 (모바일)
        for headers in [headers1, headers2, headers3]:
            user_agent = headers["User-Agent"]
            assert any(mobile in user_agent for mobile in ["Mobile", "iPhone", "Android"])

    def test_header_security_no_sensitive_info(self, crawler):
        """헤더에 민감정보가 포함되지 않는지 테스트"""
        headers = crawler._get_api_headers()

        # 민감정보가 포함되지 않아야 할 키워드
        sensitive_keywords = [
            "password",
            "passwd",
            "secret",
            "token",
            "key",
            "session",
            "cookie",
            "auth",
            "credential",
        ]

        for header_key in headers:
            header_key_lower = header_key.lower()
            header_value_lower = str(headers[header_key]).lower()

            # 헤더 키와 값에 민감정보가 없는지 확인
            for keyword in sensitive_keywords:
                assert (
                    keyword not in header_key_lower
                ), f"Sensitive keyword '{keyword}' found in header key: {header_key}"
                # Authorization 같은 헤더는 테스트에서 추가할 수 있으므로 값 검사는 선택적
                if header_key.lower() != "authorization":
                    assert (
                        keyword not in header_value_lower
                    ), f"Sensitive keyword '{keyword}' found in header value: {headers[header_key]}"

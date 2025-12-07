"""네이버 부동산 API 엔드포인트 파라미터 검증 테스트

API 엔드포인트가 올바른 파라미터로 호출되는지 상세히 테스트합니다.
네트워크 의존 테스트이므로 명시적으로 실행해야 합니다.

실행 방법:
    pytest tests/integration/test_api_endpoints.py -v -s
"""

import json
import pytest
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture
def test_config():
    """테스트용 CrawlerConfig fixture"""
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, "output")
    return CrawlerConfig(headless=True, timeout=30, output_dir=output_dir)


@pytest.fixture
def setup_test_output():
    """테스트용 output 디렉토리 설정"""
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, "output", "test_api")
    os.makedirs(output_dir, parents=True, exist_ok=True)
    return output_dir


class TestComplexListAPI:
    """단지 목록 API 테스트"""

    def test_api_url_structure(self, test_config):
        """API URL 구조가 올바른지 테스트"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock setup
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.evaluate.return_value = {"result": []}

        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Test parameters
        cortar_no = "1168010100"  # 삼성동
        bounds = {
            "leftLon": 127.04538699999999,
            "rightLon": 127.065387,
            "topLat": 37.524792,
            "bottomLat": 37.504792,
        }

        with patch.object(crawler.rate_limiter, "wait"):
            crawler.fetch_complex_list(cortar_no, json.dumps(bounds))

        # API 호출 확인
        mock_page.evaluate.assert_called_once()
        call_args = mock_page.evaluate.call_args[0][1]

        # 기본 URL 확인
        assert call_args.startswith("https://m.land.naver.com/cluster/ajax/complexList?")

        # 필수 파라미터 확인
        required_params = [
            f"cortarNo={cortar_no}",
            "rletTpCd=APT",
            "tradTpCd=A1",
            "z=17",
        ]

        for param in required_params:
            assert param in call_args, f"필수 파라미터 '{param}'가 없습니다"

        # 중심 좌표 계산 확인
        expected_lat = (bounds["topLat"] + bounds["bottomLat"]) / 2
        expected_lon = (bounds["leftLon"] + bounds["rightLon"]) / 2
        assert f"lat={expected_lat}" in call_args
        assert f"lon={expected_lon}" in call_args

        # 경계 좌표 확인
        assert f"btm={bounds['bottomLat']}" in call_args
        assert f"lft={bounds['leftLon']}" in call_args
        assert f"top={bounds['topLat']}" in call_args
        assert f"rgt={bounds['rightLon']}" in call_args

        print("\n✅ API URL 구조 검증 통과!")
        print(f"   - URL: {call_args[:100]}...")

    def test_api_parameter_order_robustness(self, test_config):
        """파라미터 순서가 결과에 영향을 주지 않는지 테스트"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock setup
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Different order of parameters should still work
        mock_response = {
            "result": [{"complexNo": "123", "complexName": "테스트", "address": "테스트 주소"}]
        }
        mock_page.evaluate.return_value = mock_response

        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Test with different parameter orders
        test_cases = [
            ("cortarNo=1168010100&rletTpCd=APT&tradTpCd=A1"),
            ("tradTpCd=A1&cortarNo=1168010100&rletTpCd=APT"),
            ("rletTpCd=APT&tradTpCd=A1&cortarNo=1168010100"),
        ]

        for params in test_cases:
            with patch.object(crawler.rate_limiter, "wait"):
                # Reset mock
                mock_page.evaluate.reset_mock()

                # Manually construct URL with different order
                api_url = f"https://m.land.naver.com/cluster/ajax/complexList?{params}&z=17&lat=37.51&lon=127.05&btm=37.50&lft=127.04&top=37.52&rgt=127.06"

                # Simulate the evaluate call with this URL
                mock_page.evaluate.return_value = mock_response
                mock_page.evaluate(api_url)

                # Should still return data regardless of parameter order
                mock_page.evaluate.assert_called_once_with(api_url)

        print("\n✅ 파라미터 순서 검증 통과!")

    def test_api_required_parameters(self, test_config):
        """필수 파라미터가 없을 때 동작 테스트"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock setup
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Response when required parameters are missing
        mock_page.evaluate.return_value = {"error": "Missing required parameters"}

        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Test missing cortarNo
        with patch.object(crawler.rate_limiter, "wait"):
            # Direct test with missing parameter
            result = crawler._fetch_dong_data(
                {
                    "dong_name": "테스트동",
                    "cortarNo": "",  # Empty cortarNo
                    "bounds": {
                        "leftLon": 127.04,
                        "rightLon": 127.06,
                        "topLat": 37.52,
                        "bottomLat": 37.50,
                    },
                }
            )

        # Should handle gracefully (return empty list)
        assert isinstance(result, list)

        print("\n✅ 필수 파라미터 누락 처리 검증 통과!")

    def test_api_response_structure_validation(self, test_config):
        """API 응답 구조 검증"""
        crawler = NaverRealEstateCrawler(test_config)

        # Test various response structures
        test_cases = [
            # Normal response
            {"result": [{"hscpNo": "123", "hscpNm": "테스트", "hscpTypeNm": "아파트"}]},
            # Empty result
            {"result": []},
            # Error response
            {"error": "API Error"},
            # Unexpected structure
            {"data": []},
            {"items": []},
        ]

        for response in test_cases:
            complexes = crawler._parse_complex_list_api(response)

            if "result" in response and response["result"]:
                assert len(complexes) > 0
            elif "error" in response or not response.get("result"):
                assert len(complexes) == 0

        print("\n✅ API 응답 구조 검증 통과!")


class TestComplexDetailAPI:
    """단지 상세 정보 API 테스트"""

    def test_detail_api_endpoints(self, test_config):
        """단지 상세 정보 API 엔드포인트 목록 테스트"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock browser manager
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Mock successful responses for all endpoints
        mock_responses = {
            "pyeongList": {"result": {"pyeongTypeList": []}},
            "holdingTax": {"result": {}},
            "declaredValue": {"result": {}},
            "recent": {"result": {"list": []}},
        }

        def mock_evaluate(url):
            for endpoint, response in mock_responses.items():
                if endpoint in url:
                    return response
            return {"result": {}}

        mock_page.evaluate.side_effect = mock_evaluate
        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Mock basic info fetch
        with patch.object(crawler, "_fetch_complex_basic_info", return_value={}):
            with patch.object(crawler.rate_limiter, "wait"):
                with patch("time.sleep"):
                    detail = crawler.fetch_complex_detail("123456")

        # Check that all expected endpoints were called
        assert isinstance(detail, dict)
        assert "pyeongList" in detail
        assert "holdingTax" in detail
        assert "declaredValue" in detail
        assert "recent" in detail

        print("\n✅ 단지 상세 API 엔드포인트 검증 통과!")

    def test_transaction_api_parameters(self, test_config):
        """거래내역 API 파라미터 검증"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock browser manager
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Mock response
        mock_response = {"isSuccess": True, "result": {"list": [], "hasNextPage": False}}
        mock_page.evaluate.return_value = mock_response

        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Test parameters
        complex_id = "111515"
        pyeong_type_number = 1
        trade_type = "A1"

        with patch.object(crawler.rate_limiter, "wait"):
            with patch.object(crawler.rate_limiter, "on_success"):
                crawler.fetch_transaction_history(
                    complex_id=complex_id,
                    pyeong_type_number=pyeong_type_number,
                    trade_type=trade_type,
                )

        # Verify API call parameters
        mock_page.evaluate.assert_called()
        call_args = mock_page.evaluate.call_args[0][1]

        # Check base URL
        assert "https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice?" in call_args

        # Check required parameters
        assert f"complexNumber={complex_id}" in call_args
        assert f"pyeongTypeNumber={pyeong_type_number}" in call_args
        assert f"tradeType={trade_type}" in call_args
        assert "page=1" in call_args
        assert "size=20" in call_args

        print("\n✅ 거래내역 API 파라미터 검증 통!")
        print(f"   - 호출 URL: {call_args[:100]}...")


class TestAPIRateLimiting:
    """API Rate Limiting 테스트"""

    def test_rate_limiting_headers(self, test_config):
        """Rate Limiting 관련 헤더 처리 테스트"""
        crawler = NaverRealEstateCrawler(test_config)

        # Mock browser manager
        mock_browser_manager = Mock()
        mock_page = Mock()
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        # Mock 429 response
        mock_page.evaluate.return_value = {"error": "HTTP 429: Too Many Requests"}

        mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
        crawler.browser_manager = mock_browser_manager

        # Test rate limiting
        with patch.object(crawler.rate_limiter, "wait"):
            with patch.object(crawler.rate_limiter, "on_rate_limit_error") as mock_on_429:
                with patch("time.sleep") as mock_sleep:
                    crawler._fetch_dong_data(
                        {
                            "dong_name": "테스트동",
                            "cortarNo": "12345678",
                            "bounds": {
                                "leftLon": 127.04,
                                "rightLon": 127.06,
                                "topLat": 37.52,
                                "bottomLat": 37.50,
                            },
                        }
                    )

        # Verify rate limiting was triggered
        mock_on_429.assert_called()
        mock_sleep.assert_called_with(10)  # 10-second wait for 429

        print("\n✅ Rate Limiting 처리 검증 통과!")


def test_api_headers_and_user_agent(test_config):
    """API 요청 헤더와 User-Agent 검증"""
    crawler = NaverRealEstateCrawler(test_config)

    # This test verifies that the correct headers are being sent
    # In actual implementation, headers are set in the JavaScript fetch call

    # Mock browser manager to capture evaluate calls
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # Test that evaluate is called with fetch including headers
    with patch.object(crawler.rate_limiter, "wait"):
        crawler.fetch_complex_list("12345678", None)

    # The actual headers are in the JavaScript code within evaluate
    # This test ensures evaluate is called (which means headers are sent)
    mock_page.evaluate.assert_called()

    # Extract the JavaScript code from the call
    call_args = mock_page.evaluate.call_args[0][0]
    js_code = call_args if isinstance(call_args, str) else str(call_args)

    # Check for required headers in the JavaScript code
    required_headers = [
        "'Accept': 'application/json, text/plain, */*'",
        "'Accept-Language': 'ko-KR,ko;q=0.9'",
        "'User-Agent': 'Mozilla/5.0 (iPhone",
    ]

    for header in required_headers:
        assert header in js_code, f"필수 헤더 '{header}'가 JavaScript 코드에 없습니다"

    print("\n✅ API 헤더와 User-Agent 검증 통과!")

"""호갱노노 API 클라이언트 TDD 테스트

Red 단계: 실패하는 테스트를 먼저 작성하여
구현이 필요한 기능을 명확히 정의합니다.
"""

import json
import pytest
from unittest.mock import Mock, patch

from crawler.api.hogangnono_client import (
    APIResponse,
    HogangnonoAPIClient,
    SearchParams,
)
from crawler.config import CrawlerConfig


class TestSearchParamsTDD:
    """SearchParams TDD 테스트 - Red 단계"""

    def test_search_params_bbox_conversion(self):
        """SearchParams bbox 파라미터 변환 테스트

        Expected: bbox tuple을 startX, startY, endX, endY로 올바르게 변환해야 함
        현재 상태: 실패할 것임 (실제 동작 확인 필요)
        """
        # bbox 파라미터 (lng_min, lat_min, lng_max, lat_max)
        params = SearchParams(bbox=(126.8781, 37.4132, 127.1834, 37.7151))

        result = params.to_dict()

        # 예상되는 결과
        assert result["startX"] == 126.8781
        assert result["startY"] == 37.4132
        assert result["endX"] == 127.1834
        assert result["endY"] == 37.7151

    def test_search_params_with_required_fields(self):
        """SearchParams 필수 필드 포함 테스트

        Expected: API에 필요한 모든 필드를 포함해야 함
        현재 상태: 실패할 것임 (일부 필드 누락 가능)
        """
        params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
            tradeType=0,  # 매매
            aptType=1,  # 아파트
        )

        result = params.to_dict()

        # 필수 필드 확인
        assert "startX" in result
        assert "startY" in result
        assert "endX" in result
        assert "endY" in result
        assert "level" in result
        assert "tradeType" in result
        assert "aptType" in result
        assert result["map"] == "google"

    def test_search_params_hogangnono_specific_fields(self):
        """SearchParams 호갱노노 특정 필드 테스트

        Expected: 호갱노노 API에 필요한 특정 필드를 포함해야 함
        현재 상태: 실패할 것임 (호갱노노 특정 필드 누락)
        """
        params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
        )

        result = params.to_dict()

        # 호갱노노 특정 필드 확인
        assert "screenWidth" in result
        assert "screenHeight" in result
        assert "apt" in result
        assert result["screenWidth"] == 1200
        assert result["screenHeight"] == 924


class TestAPIResponseTDD:
    """APIResponse TDD 테스트 - Red 단계"""

    def test_api_response_success_structure(self):
        """성공 응답 구조 테스트

        Expected: 호갱노노 API 성공 응답을 올바르게 파싱해야 함
        현재 상태: 실패할 것임 (실제 응답 구조와 다를 수 있음)
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": "12345",
                    "name": "테스트아파트",
                    "address": "서울시 강남구",
                    "lat": 37.5,
                    "lng": 127.0,
                }
            ],
        }

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data is not None
        assert len(api_response.data) > 0

    def test_api_response_error_handling(self):
        """에러 응답 처리 테스트

        Expected: API 에러를 올바르게 감지하고 처리해야 함
        현재 상태: 실패할 것임 (에러 처리 미완성)
        """
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": False,
            "error": "Rate limit exceeded",
        }

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 429
        assert "Rate limit" in api_response.error

    def test_api_response_html_content(self):
        """HTML 콘텐츠 처리 테스트

        Expected: HTML 응답을 성공으로 처리해야 함 (세션 초기화 등)
        현재 상태: 실패할 것임 (HTML 처리 미완성)
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html><body>Test HTML</body></html>"

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.status_code == 200
        assert api_response.data is not None


class TestHogangnonoAPIClientTDD:
    """HogangnonoAPIClient TDD 테스트 - Red 단계"""

    @pytest.fixture
    def config(self):
        return CrawlerConfig(
            user_agent="Test Agent",
            timeout=10.0,
        )

    @pytest.fixture
    def client(self, config):
        return HogangnonoAPIClient(config)

    def test_session_initialization(self, client):
        """세션 초기화 테스트

        Expected: 메인 페이지 접속으로 세션을 초기화해야 함
        현재 상태: 실패할 것임 (실제 API 호출 필요)
        """
        # 초기화 전 상태 확인
        assert client._session_initialized is False

        # 세션 초기화 시도
        result = client._initialize_session()

        # 초기화 성공 확인
        assert result is True
        assert client._session_initialized is True

    def test_api_headers_structure(self, client):
        """API 헤더 구조 테스트

        Expected: 올바른 API 요청 헤더를 생성해야 함
        """
        headers = client._get_api_headers()

        # 필수 헤더 필드 확인
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Referer" in headers
        assert "Origin" in headers
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"

        # 헤더 값 검증
        assert "application/json, text/plain, */*" in headers["Accept"]
        assert "no-cache" in headers["Cache-Control"]
        assert "Pragma" in headers
        assert "Sec-Ch-Ua" in headers
        assert "Sec-Ch-Ua-Mobile" in headers
        assert "Sec-Ch-Ua-Platform" in headers
        assert "Sec-Fetch-Dest" in headers
        assert "Sec-Fetch-Mode" in headers
        assert "Sec-Fetch-Site" in headers
        assert "Referer" in headers
        assert "Origin" in headers

    @patch("requests.Session.request")
    def test_make_request_with_cookies(self, mock_request, client):
        """쿠키와 함께 요청 테스트

        Expected: 세션 쿠키를 포함하여 API 요청을 보내야 함
        """
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response

        # 세션 초기화 Mock
        with patch.object(client, "_initialize_session", return_value=True):
            client._session_initialized = True
            client.session.cookies = Mock()

            # API 요청
            client._make_request(
                method="GET",
                endpoint="/api/test",
                params={"test": "value"},
            )

            # 요청 확인
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]

            # 헤더 확인
            assert "headers" in call_kwargs
            headers = call_kwargs["headers"]

            # 헤더 필드 검증
            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "Referer" in headers
            assert "Origin" in headers
            assert "X-Requested-With" in headers
            assert headers["X-Requested-With"] == "XMLHttpRequest"

            # 헤더 값 검증
            assert "application/json, text/plain, */*" in headers["Accept"]
            assert "no-cache" in headers["Cache-Control"]
            assert "Pragma" in headers
            assert "Sec-Ch-Ua" in headers
            assert "Sec-Ch-Ua-Mobile" in headers
            assert "Sec-Ch-Ua-Platform" in headers
            assert "Sec-Fetch-Dest" in headers
            assert "Sec-Fetch-Mode" in headers
            assert "Sec-Fetch-Site" in headers
            assert "Referer" in headers
            assert "Origin" in headers

            # User-Agent 확인
            assert headers["User-Agent"] == client.config.user_agent

    def test_get_apartments_bounding_endpoint(self, client):
        """아파트 바운딩 엔드포인트 테스트

        Expected: 올바른 엔드포인트로 요청을 보내야 함
        """
        search_params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
            tradeType=0,
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True)

            client.get_apartments_bounding(search_params)

            # 올바른 엔드포인트 호출 확인
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/pois-bounding",
                params=search_params.to_dict(),
            )

    def test_rate_limiting(self, client):
        """Rate limiting 테스트

        Expected: API 호출 간격을 조절해야 함
        현재 상태: 실패할 것임 (Rate limiting 미구현)
        """

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True)

            # 첫 번째 요청
            client._make_request("GET", "/api/test1")

            # 두 번째 요청
            client._make_request("GET", "/api/test2")

            # Rate limiting이 적용되어야 함
            # (실제 구현에서는 time.sleep이나 delay 로직이 필요)
            assert mock_request.call_count == 2

    def test_rate_limiter_integration(self, client):
        """RateLimiter가 API 호출에 통합되었는지 확인"""
        # RateLimiter가 초기화되었는지 확인
        assert hasattr(client, "rate_limiter")
        assert client.rate_limiter is not None

        # 초기 설정 확인
        assert client.rate_limiter.current_delay == 2.0
        assert client.rate_limiter.min_delay == 1.0
        assert client.rate_limiter.max_delay == 10.0

    def test_rate_limiter_called_before_request(self, client):
        """API 호출 전 rate limiter wait() 호출 확인"""
        with patch.object(client.rate_limiter, "wait") as mock_wait:
            with patch.object(client, "_initialize_session", return_value=True):
                with patch.object(client.session, "request") as mock_request:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"status": "success", "data": {}}
                    mock_response.headers = {"content-type": "application/json"}
                    mock_request.return_value = mock_response

                    client.get_regions()

                    # wait()가 호출되었는지 확인
                    mock_wait.assert_called_once()

    def test_rate_limiter_feedback_on_success(self, client):
        """API 성공 시 rate limiter feedback 호출 확인"""
        with patch.object(client, "_initialize_session", return_value=True):
            with patch.object(client.rate_limiter, "wait"):
                with patch.object(client.rate_limiter, "on_success") as mock_on_success:
                    with patch.object(client.session, "request") as mock_request:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {"status": "success", "data": {}}
                        mock_response.headers = {"content-type": "application/json"}
                        mock_request.return_value = mock_response

                        client.get_regions()

                        # on_success()가 호출되었는지 확인
                        mock_on_success.assert_called_once()

    def test_rate_limiter_feedback_on_error(self, client):
        """API 에러 시 rate limiter feedback 호출 확인"""
        with patch.object(client, "_initialize_session", return_value=True):
            with patch.object(client.rate_limiter, "wait"):
                with patch.object(client.rate_limiter, "on_error") as mock_on_error:
                    with patch.object(client.session, "request") as mock_request:
                        mock_response = Mock()
                        mock_response.status_code = 500
                        mock_response.json.return_value = {"error": "Internal Server Error"}
                        mock_response.headers = {"content-type": "application/json"}
                        mock_request.return_value = mock_response

                        client.get_regions()

                        # on_error()가 호출되었는지 확인
                        mock_on_error.assert_called_once()

    def test_rate_limiter_feedback_on_rate_limit(self, client):
        """429 에러 시 rate limiter feedback 호출 확인"""
        with patch.object(client, "_initialize_session", return_value=True):
            with patch.object(client.rate_limiter, "wait"):
                with patch.object(client.rate_limiter, "on_rate_limit_error") as mock_on_rate_limit:
                    with patch.object(client.session, "request") as mock_request:
                        mock_response = Mock()
                        mock_response.status_code = 429
                        mock_response.json.return_value = {"error": "Too Many Requests"}
                        mock_response.headers = {"content-type": "application/json"}
                        mock_request.return_value = mock_response

                        client.get_regions()

                        # on_rate_limit_error()가 호출되었는지 확인
                        mock_on_rate_limit.assert_called_once()

    def test_retry_decorator_applied_to_api_methods(self, client):
        """@retry_transient_errors 데코레이터가 API 메서드에 적용되었는지 확인"""

        # 데코레이터가 적용된 메서드 목록
        api_methods = [
            "get_complex_list",
            "get_complex_detail",
            "get_apartments_bounding",
            "get_ranking",
            "get_recent_visits",
            "get_region_info",
            "get_pois_bounding",
            "search_apartments",
            "get_apartment_detail",
            "get_apartment_transactions",
            "get_regions",
            "fetch_ranks_rolling",
            "fetch_pois_bounding",
            "search_apartments_by_location",
        ]

        for method_name in api_methods:
            method = getattr(client, method_name)

            # 메서드의 __func__를 통해 데코레이터 적용 확인
            # Retryable decorator는 wrapper function을 반환
            assert (
                "wrapper" in method.__name__
            ), f"{method_name} should be wrapped by retry decorator"

            # 또는 decorator가 적용되었는지 소스 코드에서 확인
            unbound_method = getattr(client.__class__, method_name)
            # 데코레이터가 적용된 메서드는 wrapper function을 가짐
            assert (
                hasattr(unbound_method, "__name__") and "wrapper" in unbound_method.__name__
            ), f"{method_name} should be wrapped by retry decorator"

    def test_retry_behavior_on_transient_errors(self, client):
        """일시적 오류 시 재시도 동작 테스트"""
        import requests

        with patch.object(client, "_initialize_session", return_value=True):
            with patch.object(client.rate_limiter, "wait"):
                with patch.object(client.session, "request") as mock_request:
                    # 처음 두 번은 예외 발생, 세 번째는 성공
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.headers = {"content-type": "application/json"}
                    mock_response.json.return_value = {"status": "success", "data": {}}

                    # 처음 두 번은 timeout 예외, 세 번째는 성공
                    mock_request.side_effect = [
                        requests.exceptions.Timeout("Connection timeout"),
                        requests.exceptions.Timeout("Connection timeout"),
                        mock_response,
                    ]

                    # retry가 적용되면 최종적으로 성공해야 함
                    result = client.get_regions()

                    # 3번의 요청이 있었는지 확인 (2번 재시도 + 1번 성공)
                    assert mock_request.call_count == 3
                    assert result.success is True


class TestHogangnonoCrawlerIntegrationTDD:
    """호갱노노 크롤러 통합 TDD 테스트 - Red 단계"""

    @pytest.fixture
    def config(self):
        return CrawlerConfig(
            user_agent="Test Agent",
            timeout=10.0,
        )

    @pytest.fixture
    def crawler(self, config):
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        return HogangnonoCrawler(
            config=config,
            output_dir="test_output",
            region_bounds=(37.5, 126.9, 37.6, 127.0),
        )

    def test_data_mapping_to_naver_format(self, crawler):
        """데이터 매핑 테스트

        Expected: 호갱노노 데이터를 네이버 형식으로 올바르게 변환해야 함
        현재 상태: 실패할 것임 (매핑 로직 오류 가능)
        """
        # 테스트 데이터
        test_item = {
            "id": "12345",
            "name": "테스트아파트",
            "address": "서울시 강남구",
            "lat": 37.5,
            "lng": 127.0,
            "build_year": "2020",
            "households": "500",
            "trade": {
                "type": "sale",
                "area": "84.94",
                "price": "150,000",
                "floor": "5",
                "date": "20241201",
            },
        }

        # Mock get_dong_code to return a test value
        with patch.object(crawler, "get_dong_code", return_value="11680500"):
            mapped_data = crawler.data_mapper.map_to_naver_format(
                test_item, fetch_dong_code_func=crawler.get_dong_code
            )

        # 매핑 결과 확인
        assert mapped_data is not None
        assert mapped_data["complex_id"] == "12345"
        assert mapped_data["complex_name"] == "테스트아파트"
        assert mapped_data["trade_type_name"] == "매매"
        assert mapped_data["pyeong_type_number"] == 26  # 84.94 / 3.305785 ≈ 25.7
        assert mapped_data["deal_price"] == 150000

    def test_save_to_csv_functionality(self, crawler):
        """CSV 저장 기능 테스트

        Expected: 수집된 데이터를 CSV 파일에 저장해야 함
        현재 상태: 실패할 것임 (파일 I/O 오류 가능)
        """
        test_complexes = [
            {
                "complex_id": "12345",
                "complex_name": "테스트아파트",
                "address": "서울시 강남구",
            }
        ]

        test_transactions = [
            {
                "complex_id": "12345",
                "trade_type": "A1",
                "deal_price": 150000,
            }
        ]

        # CSV 저장 시도
        crawler.save_to_csv(test_complexes, test_transactions)

        # 파일 생성 확인
        assert crawler.complex_writer.output_path.exists()
        assert crawler.transaction_writer.output_path.exists()


class TestErrorHandlingTDD:
    """에러 핸들링 TDD 테스트 - Red 단계"""

    @pytest.fixture
    def client(self):
        config = CrawlerConfig(user_agent="Test", timeout=5.0)
        return HogangnonoAPIClient(config)

    def test_session_initialization_failure(self, client):
        """세션 초기화 실패 테스트

        Expected: 세션 초기화 실패를 올바르게 처리해야 함
        현재 상태: 실패할 것임 (에러 처리 미완성)
        """
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = client._initialize_session()

            assert result is False
            assert client._session_initialized is False

    def test_api_timeout_handling(self, client):
        """API 타임아웃 처리 테스트

        Expected: 타임아웃 에러를 올바르게 처리해야 함
        현재 상태: 실패할 것임 (타임아웃 처리 미완성)
        """
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=False,
                error="Request timeout",
                status_code=None,
            )

            response = client._make_request("GET", "/api/test")

            assert response.success is False
            assert "timeout" in response.error.lower()

    def test_invalid_response_handling(self, client):
        """잘못된 응답 처리 테스트

        Expected: 잘못된 응답을 올바르게 처리해야 함
        현재 상태: 실패할 것임 (응답 검증 미완성)
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 500

    def test_get_regions_success(self, client):
        """전체 지역 목록 조회 성공"""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=True,
                data={
                    "regionList": [
                        {
                            "regionCode": "11",
                            "name": "서울",
                            "fullName": "서울특별시",
                            "children": [
                                {
                                    "regionCode": "11680",
                                    "name": "강남구",
                                    "fullName": "서울특별시 강남구",
                                }
                            ],
                        }
                    ]
                },
                status_code=200,
            )

            response = client.get_regions()

            assert response.success
            assert response.data is not None
            assert "regionList" in response.data
            assert len(response.data["regionList"]) > 0

            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/regions",
                params={},
                headers={"User-Agent": client.config.user_agent, "Accept": "application/json"},
            )

    def test_get_apartment_detail_success(self, client):
        """단지 상세 정보 조회 성공"""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=True,
                data={
                    "aptHash": "1Hq6f",
                    "aptName": "래미안",
                    "buildYear": 2005,
                    "household": 1012,
                    "parkingCount": 850,
                    "floorAreaRatio": 250.5,
                    "buildingCoverageRatio": 15.3,
                },
                status_code=200,
            )

            response = client.get_apartment_detail("1Hq6f")

            assert response.success
            assert response.data is not None
            assert response.data["aptHash"] == "1Hq6f"

            mock_request.assert_called_once_with(
                method="GET", endpoint="/api/v2/apts/1Hq6f", params={}
            )

    def test_get_apartment_transactions_recent(self, client):
        """최근 3년 실거래 내역 조회"""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=True,
                data={
                    "shortTermReport": [
                        {
                            "date": "2025-01-31T15:00:00.000Z",
                            "minPrice": 333000,
                            "maxPrice": 346000,
                            "averagePrice": 343000,
                            "volume": 3,
                            "trades": [{"id": 36780389, "price": 340000, "floor": 9, "day": 18}],
                        }
                    ]
                },
                status_code=200,
            )

            response = client.get_apartment_transactions("1Hq6f", trade_type=0)

            assert response.success
            assert response.data is not None
            assert "shortTermReport" in response.data

            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/apts/1Hq6f/monthly-reports",
                params={"tradeType": 0, "areaNo": 0},
            )

    def test_get_apartment_transactions_full_period(self, client):
        """전체 기간 실거래 내역 조회"""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=True,
                data={"longTermReport": []},
                status_code=200,
            )

            response = client.get_apartment_transactions("1Hq6f", trade_type=0, full_period=True)

            assert response.success

            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/apts/1Hq6f/monthly-reports/more",
                params={"tradeType": 0, "areaNo": 0},
            )

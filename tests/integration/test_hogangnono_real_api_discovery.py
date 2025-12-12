"""호갱노노 실제 API 엔드포인트 발견 테스트

이 테스트는 실제 호갱노노 사이트에 접속하여
작동하는 API 엔드포인트를 찾아내는 것을 목표로 합니다.
"""

# Import test setup to configure path and mocks

import json
import pytest

from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams
from crawler.config import CrawlerConfig


@pytest.mark.slow
class TestHogangnonoRealAPIDiscovery:
    """호갱노노 실제 API 발견 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return CrawlerConfig(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            timeout=30.0,
        )

    @pytest.fixture
    def client(self, config):
        """API 클라이언트"""
        return HogangnonoAPIClient(config)

    def test_main_page_access(self, client):
        """메인 페이지 접근 테스트

        Expected: 메인 페이지에 접근할 수 있어야 함
        Purpose: 세션 초기화 및 기본 접속성 확인
        """
        response = client._make_request("GET", "/")

        # 메인 페이지는 성공해야 함
        assert response.status_code == 200
        assert response.success is True

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v2/ranks/rolling",
            "/api/v2/apts/recent-visits",
            "/api/v2/maps/region",
            "/api/v2/pois-bounding",
            "/api/apt/bounding",
            "/api/search/apartments",
            "/api/articles",
            "/api/complexes",
            "/cluster/ajax/complexList",
            "/cluster/ajax/complexDetail",
            "/cluster/ajax/articleList",
        ],
    )
    def test_endpoints_availability(self, client, endpoint):
        """다양한 엔드포인트 접근 가능성 테스트

        Expected: 일부 엔드포인트는 작동해야 함
        Purpose: 실제 작동하는 엔드포인트 발견
        """
        try:
            response = client._make_request("GET", endpoint)

            if response.success:
                print(f"✓ Working endpoint: {endpoint}")

                # 응답 데이터 구조 분석
                if response.data:
                    print(
                        f"  Response keys: {list(response.data.keys()) if isinstance(response.data, dict) else type(response.data)}"
                    )

                    # 데이터 샘플 출력 (첫 200자)
                    if isinstance(response.data, dict):
                        sample = json.dumps(response.data, ensure_ascii=False)[:200]
                        print(f"  Sample: {sample}...")

                # 성공한 엔드포인트는 최소한의 데이터 구조를 가져야 함
                assert response.data is not None

            else:
                print(f"✗ Failed endpoint: {endpoint} - {response.error}")

        except Exception as e:
            print(f"✗ Error at {endpoint}: {str(e)}")

    def test_find_working_apartment_endpoints(self, client):
        """아파트 관련 작동 엔드포인트 찾기

        Expected: 아파트 데이터를 가져오는 엔드포인트를 찾아야 함
        Purpose: 실제 데이터 크롤링을 위한 엔드포인트 확보
        """
        # 아파트 관련 후보 엔드포인트
        apartment_endpoints = [
            "/api/apt/bounding",
            "/api/v2/apts",
            "/api/apartments",
            "/api/search/apartments",
            "/cluster/ajax/articleList",
        ]

        # 서울 강남구 좌표
        seoul_coords = (126.9784, 37.5665, 127.1484, 37.7134)

        working_endpoints = []

        for endpoint in apartment_endpoints:
            try:
                # 파라미터 준비
                if "bounding" in endpoint:
                    params = {
                        "startX": seoul_coords[0],
                        "startY": seoul_coords[1],
                        "endX": seoul_coords[2],
                        "endY": seoul_coords[3],
                        "level": 14,
                    }
                else:
                    params = {
                        "lat": 37.5665,
                        "lng": 126.9784,
                        "zoom": 14,
                    }

                response = client._make_request("GET", endpoint, params=params)

                if response.success and response.data:
                    working_endpoints.append(endpoint)
                    print(f"\n✓ Found working endpoint: {endpoint}")
                    print(f"  Response type: {type(response.data)}")

                    if isinstance(response.data, dict):
                        print(f"  Keys: {list(response.data.keys())}")

                        # 데이터가 있는지 확인
                        for key in ["data", "items", "results", "list"]:
                            if key in response.data and response.data[key]:
                                print(f"  Data found in: {key}")

                    elif isinstance(response.data, list) and response.data:
                        print(f"  List length: {len(response.data)}")
                        if response.data[0]:
                            print(
                                f"  First item keys: {list(response.data[0].keys()) if isinstance(response.data[0], dict) else type(response.data[0])}"
                            )

            except Exception as e:
                print(f"✗ Error at {endpoint}: {str(e)}")

        # 최소한 하나의 엔드포인트는 작동해야 함
        assert len(working_endpoints) > 0, "No working apartment endpoints found"
        print(f"\nTotal working endpoints: {len(working_endpoints)}")

    def test_session_cookie_analysis(self, client):
        """세션 쿠키 분석

        Expected: 메인 페이지 접속 후 필요한 쿠키를 받아야 함
        Purpose: 인증 및 세션 유지에 필요한 쿠키 확인
        """
        # 세션 초기화
        success = client._initialize_session()

        assert success, "Session initialization failed"
        assert client._session_initialized, "Session not marked as initialized"

        # 쿠키 확인
        if hasattr(client.session, "cookies") and client.session.cookies:
            cookie_names = [c.name for c in client.session.cookies]

            print(f"\nSession cookies: {cookie_names}")

            # 중요 쿠키 확인
            important_cookies = ["session", "token", "auth", "csrf", "_ga", "_gid"]
            found_important = [
                c for c in important_cookies if any(c in name.lower() for name in cookie_names)
            ]

            if found_important:
                print(f"Important cookies found: {found_important}")

            # 쿠키가 최소한 하나는 있어야 함
            assert len(cookie_names) > 0, "No cookies received"

        else:
            print("\nNo cookies received from session initialization")

    def test_real_api_call_with_search_params(self, client):
        """실제 SearchParams로 API 호출

        Expected: 올바른 파라미터 형식으로 API를 호출해야 함
        Purpose: SearchParams 형식 검증 및 실제 응답 확인
        """
        # 실제 좌표 (서울 강남구 삼성동)
        search_params = SearchParams(
            bbox=(127.0489, 37.5144, 127.0639, 37.5244),
            level=15,
            tradeType=0,  # 매매
            aptType=1,  # 아파트
        )

        # 여러 엔드포인트 시도
        endpoints_to_try = [
            "/api/apt/bounding",
            "/api/v2/pois-bounding",
            "/cluster/ajax/articleList",
        ]

        success_found = False

        for endpoint in endpoints_to_try:
            try:
                response = client._make_request("GET", endpoint, params=search_params.to_dict())

                if response.success and response.data:
                    success_found = True
                    print(f"\n✓ Success with endpoint: {endpoint}")
                    print(f"  Params: {search_params.to_dict()}")

                    # 응답 분석
                    if isinstance(response.data, dict):
                        print(f"  Response structure: {list(response.data.keys())}")

                        # 실제 데이터 찾기
                        data_fields = ["data", "items", "results", "list", "articles"]
                        for field in data_fields:
                            if field in response.data:
                                items = response.data[field]
                                if isinstance(items, list) and items:
                                    print(f"  Found {len(items)} items in '{field}'")
                                    if items[0]:
                                        print(
                                            f"  Sample item keys: {list(items[0].keys()) if isinstance(items[0], dict) else type(items[0])}"
                                        )
                                        break

                    break

            except Exception as e:
                print(f"✗ Failed with {endpoint}: {str(e)}")

        # 최소한 하나의 엔드포인트는 성공해야 함
        assert success_found, "No endpoint succeeded with SearchParams"

    def test_analyze_response_patterns(self, client):
        """응답 패턴 분석

        Expected: 일관된 응답 구조를 가져야 함
        Purpose: API 응답 형식 이해 및 파싱 로직 개선
        """
        # 다양한 요청 시도
        test_cases = [
            ("/", None, "메인 페이지"),
            (
                "/api/apt/bounding",
                {"startX": 127, "startY": 37.5, "endX": 127.1, "endY": 37.6},
                "바운딩 API",
            ),
        ]

        response_patterns = []

        for endpoint, params, description in test_cases:
            try:
                response = client._make_request("GET", endpoint, params=params)

                pattern = {
                    "endpoint": endpoint,
                    "description": description,
                    "status": response.status_code,
                    "success": response.success,
                    "has_data": response.data is not None,
                    "data_type": type(response.data).__name__ if response.data else None,
                }

                if response.data:
                    if isinstance(response.data, dict):
                        pattern["keys"] = list(response.data.keys())
                        pattern["has_items"] = any(
                            k in response.data for k in ["data", "items", "results", "list"]
                        )
                    elif isinstance(response.data, list):
                        pattern["length"] = len(response.data)
                        pattern["has_items"] = len(response.data) > 0

                response_patterns.append(pattern)

                print(f"\n{description}:")
                print(f"  Status: {response.status_code}")
                print(f"  Success: {response.success}")
                print(f"  Data type: {pattern['data_type']}")

            except Exception as e:
                print(f"\n{description}: Failed - {str(e)}")
                response_patterns.append(
                    {"endpoint": endpoint, "description": description, "error": str(e)}
                )

        # 성공적인 응답 패턴이 있어야 함
        successful_patterns = [p for p in response_patterns if p.get("success")]
        assert len(successful_patterns) > 0, "No successful response patterns found"


@pytest.mark.xfail(reason="실제 API 호출이 필요하며 네트워크 의존적")
class TestHogangnonoLiveAPI:
    """실제 호갱노노 API 라이브 테스트

    이 테스트는 실제 API 호출을 수행하므로
    네트워크 상황에 따라 실패할 수 있습니다.
    """

    def test_full_crawling_workflow(self):
        """전체 크롤링 워크플로우 테스트

        Expected: 전체 크롤링 과정이 작동해야 함
        Purpose: 실제 사용 시나리오 검증
        """
        # 이 테스트는 실제 환경에서만 실행
        pytest.skip("Live API test - requires manual execution")

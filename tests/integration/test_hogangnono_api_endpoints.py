"""호갱노노 API 엔드포인트 통합 테스트

TDD 접근법: 현재 실패하는 테스트를 먼저 작성하고,
어떤 부분이 개선되어야 하는지 명확히 보여줍니다.
"""

import json
import pytest
import requests
from unittest.mock import Mock

from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams, APIResponse
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


class TestHogangnonoAPIEndpoints:
    """호갱노노 API 엔드포인트 테스트

    TDD 원칙에 따라:
    1. 실패하는 테스트를 먼저 작성
    2. 실패 원인을 명확히 진단
    3. 성공 기준을 명확히 정의
    """

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            user_agent="Mozilla/5.0 (Test)",
            timeout=10.0,
        )

    @pytest.fixture
    def client(self, config):
        """API 클라이언트 fixture"""
        return HogangnonoAPIClient(config)

    @pytest.fixture
    def crawler(self, config):
        """크롤러 fixture"""
        return HogangnonoCrawler(
            config=config,
            output_dir="test_output",
            region_bounds=(37.5, 126.9, 37.6, 127.0),  # 서울 일부 지역
        )

    def test_base_url_accessibility(self, client):
        """기본 URL 접근성 테스트

        Expected: 호갱노노 메인 페이지는 접근 가능해야 함
        """
        response = client._make_request("GET", "/")

        # 메인 페이지는 HTML을 반환하므로 JSON 파싱에 실패할 수 있음
        # 중요한 것은 200 OK 응답을 받는 것
        assert response.status_code == 200
        assert response.success is True  # HTML이라도 성공으로 간주

    @pytest.mark.xfail(reason="API 엔드포인트가 존재하지 않을 수 있음")
    def test_ranking_api_endpoint(self, client):
        """랭킹 API 엔드포인트 테스트

        Expected: 랭킹 데이터를 반환해야 함
        현재 상태: 엔드포인트가 존재하지 않을 수 있음 (xfail 마크)
        """
        response = client.get_ranking(rank_type="daily", limit=10)

        assert response.success is True
        assert response.data is not None
        assert "data" in response.data or isinstance(response.data, list)

    @pytest.mark.xfail(reason="API 엔드포인트가 존재하지 않을 수 있음")
    def test_recent_visits_api_endpoint(self, client):
        """최근 조회 매물 API 엔드포인트 테스트

        Expected: 최근 조회 매물 목록을 반환해야 함
        현재 상태: 엔드포인트가 존재하지 않을 수 있음 (xfail 마크)
        """
        response = client.get_recent_visits(apt_type="apart", limit=10)

        assert response.success is True
        assert response.data is not None

    @pytest.mark.xfail(reason="API 엔드포인트가 존재하지 않을 수 있음")
    def test_region_info_api_endpoint(self, client):
        """지역 정보 API 엔드포인트 테스트

        Expected: 지역 정보를 반환해야 함
        현재 상태: 엔드포인트가 존재하지 않을 수 있음 (xfail 마크)
        """
        response = client.get_region_info(lat=37.5, lng=126.9, zoom=14)

        assert response.success is True
        assert response.data is not None

    @pytest.mark.xfail(reason="Bounding API가 실패할 것으로 예상")
    def test_pois_bounding_api_current_implementation(self, client):
        """현재 POI 바운딩 API 구현 테스트

        Expected: 실패해야 함 (현재 잘못된 엔드포인트/파라미터 사용)
        이 테스트의 실패가 API 수정의 필요성을 보여줌
        """
        search_params = SearchParams(
            bbox=(37.5, 126.9, 37.6, 127.0),
            zoom=14,
            limit=10,
        )

        response = client.get_pois_bounding(search_params)

        # 이 테스트는 실패해야 함
        # 실패하는 이유를 기록하기 위함
        if not response.success:
            pytest.fail(f"Bounding API failed: {response.error} (Status: {response.status_code})")

    def test_api_response_structure(self, client):
        """API 응답 구조 테스트

        Expected: APIResponse 객체가 올바르게 생성되어야 함
        """
        # Mock 응답 테스트
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"items": []}}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data == {"items": []}
        assert api_response.status_code == 200
        assert api_response.error is None

    def test_api_response_error_handling(self, client):
        """API 응답 에러 처리 테스트

        Expected: 에러 상황을 올바르게 처리해야 함
        """
        # Mock 에러 응답 테스트
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 404
        assert "HTTP error" in api_response.error

    @pytest.mark.xfail(reason="실제 API 호출이 실패할 것으로 예상")
    def test_real_api_call_bounding_box(self, client):
        """실제 API 호출 테스트 - 바운딩 박스

        Expected: 실패해야 함 (실제 엔드포인트 확인 필요)
        이 테스트를 통해 실제 동작하는 엔드포인트를 찾아냄
        """
        # 실제 좌표 (서울 강남구 일부)
        search_params = SearchParams(
            bbox=(37.5132, 127.0286, 37.5232, 127.0386),
            zoom=15,
            limit=5,
        )

        response = client.get_pois_bounding(search_params)

        # 성공하면 데이터 구조 확인
        if response.success:
            assert response.data is not None
            # 데이터 구조 로깅
            print(f"Response data: {json.dumps(response.data, indent=2, ensure_ascii=False)}")
        else:
            pytest.fail(f"Real API call failed: {response.error}")

    def test_find_working_endpoints(self, client):
        """작동하는 엔드포인트 찾기 테스트

        Expected: 가능한 모든 엔드포인트를 테스트하여
                 실제로 작동하는 엔드포인트를 찾아냄
        """
        # 테스트할 엔드포인트 목록
        endpoints_to_test = [
            "/api/v2/ranks/rolling",
            "/api/v2/apts/recent-visits",
            "/api/v2/maps/region",
            "/api/v2/pois-bounding",
            "/api/apt/bounding",
            "/api/search/apartments",
        ]

        working_endpoints = []
        failed_endpoints = []

        for endpoint in endpoints_to_test:
            try:
                response = client._make_request("GET", endpoint)
                if response.success:
                    working_endpoints.append(endpoint)
                    print(f"✓ Working: {endpoint}")
                else:
                    failed_endpoints.append((endpoint, response.error))
                    print(f"✗ Failed: {endpoint} - {response.error}")
            except Exception as e:
                failed_endpoints.append((endpoint, str(e)))
                print(f"✗ Error: {endpoint} - {str(e)}")

        # 최소 하나의 엔드포인트는 작동해야 함
        assert len(working_endpoints) > 0, "No working endpoints found"

        # 실패한 엔드포인트 정보 출력
        if failed_endpoints:
            print("\nFailed endpoints:")
            for endpoint, error in failed_endpoints:
                print(f"  - {endpoint}: {error}")

    @pytest.mark.xfail(reason="크롤러의 API 호출이 실패할 것으로 예상")
    def test_crawler_api_integration(self, crawler):
        """크롤러 API 통합 테스트

        Expected: 실패해야 함 (현재 크롤러 구현이 잘못됨)
        이 테스트의 실패가 크롤러 수정의 필요성을 보여줌
        """
        complexes, transactions = crawler.crawl_region(
            region_bounds=(37.5, 126.9, 37.6, 127.0),
            apt_type="apart",
            max_pages=1,
        )

        # 성공하면 데이터 확인
        assert len(complexes) > 0 or len(transactions) > 0

        # 데이터 구조 확인
        if complexes:
            complex_item = complexes[0]
            assert "complex_id" in complex_item
            assert "complex_name" in complex_item

        if transactions:
            transaction_item = transactions[0]
            assert "complex_id" in transaction_item
            assert "trade_type" in transaction_item

    def test_search_params_conversion(self):
        """SearchParams 변환 테스트

        Expected: SearchParams가 올바르게 딕셔너리로 변환되어야 함
        """
        # bbox가 있는 경우
        params = SearchParams(
            bbox=(37.5, 126.9, 37.6, 127.0),
            zoom=14,
            limit=100,
            filters={"apt_type": "apart"},
        )

        result = params.to_dict()

        assert result["lat_min"] == 37.5
        assert result["lng_min"] == 126.9
        assert result["lat_max"] == 37.6
        assert result["lng_max"] == 127.0
        assert result["zoom"] == 14
        assert result["limit"] == 100
        assert result["apt_type"] == "apart"

        # bbox가 없는 경우
        params = SearchParams(
            zoom=15,
            limit=50,
        )

        result = params.to_dict()

        assert "lat_min" not in result
        assert "lng_min" not in result
        assert result["zoom"] == 15
        assert result["limit"] == 50

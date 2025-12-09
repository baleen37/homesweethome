"""호갱노노 API 404 오류 수정을 위한 TDD 테스트

이 테스트는 현재 API 호출이 404를 반환하는 문제를 확인하고,
TDD 방식으로 해결하기 위해 작성되었습니다.
"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams
from crawler.config import CrawlerConfig


@pytest.mark.integration
class TestHogangnonoAPIFix:
    """호갱노노 API 수정 테스트 클래스"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            timeout=10.0,
        )

    @pytest.fixture
    def client(self, config):
        """테스트용 API 클라이언트"""
        return HogangnonoAPIClient(config)

    @pytest.fixture
    def sample_working_params(self):
        """성공하는 API 파라미터 (api_analysis_result.json에서 추출)"""
        return {
            "map": "google",
            "level": "17",
            "screenWidth": 1200,
            "screenHeight": 924,
            "apt": "",
            "areaNo": "",
            "startX": 127.106812,
            "endX": 127.1196866,
            "startY": 37.3906896,
            "endY": 37.3985655,
            "tradeType": 0,
            "areaFrom": 0,
            "areaTo": 80,
            "priceFrom": 0,
            "priceTo": 401000,
            "gapPriceFrom": 0,
            "gapPriceTo": 151000,
            "gapPriceNeg": False,
            "sinceFrom": 0,
            "sinceTo": 30,
            "floorAreaRatioFrom": 0,
            "floorAreaRatioTo": 900,
            "buildingCoverageRatioFrom": 0,
            "buildingCoverageRatioTo": 100,
            "rentalBusinessRatioFrom": 0,
            "rentalBusinessRatioTo": 100,
            "householdFrom": 0,
            "householdTo": 5000,
            "parking": 0,
            "profitRatio": 0,
            "rentRateFrom": 0,
            "rentRateTo": 200,
            "aptType": -1,
            "isIgnorePin": False,
            "auctionState": -1,
            "reconstructionStep": 0,
            "reconstructionStepFrom": 1,
            "reconstructionStepTo": 10,
            "r": 84424,
        }

    def test_current_api_returns_404(self, client):
        """Red 단계: 현재 API 엔드포인트가 404를 반환하는지 확인"""
        # SearchParams 생성
        params = SearchParams(
            bbox=(127.106812, 37.3906896, 127.1196866, 37.3985655),
            level=17,
            tradeType=0,
        )

        # API 호출
        response = client.get_apartments_bounding(params)

        # 404 오류가 발생해야 함 (Red 단계)
        assert not response.success, "API 호출이 성공해서는 안 됩니다"
        assert response.status_code == 404, f"상태 코드가 404가 아니라 {response.status_code}입니다"
        assert (
            "404" in response.error or "Not Found" in response.error
        ), f"에러 메시지에 404 또는 Not Found가 포함되어야 합니다: {response.error}"

    @patch("requests.Session.request")
    def test_working_api_endpoint_exists(self, mock_request, client, sample_working_params):
        """성공하는 API 엔드포인트 테스트

        api_analysis_result.json에서 확인된 성공하는 파라미터로
        API 호출이 성공하는 것을 확인
        """
        # 성공 응답 Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "name": "테스트 아파트",
                    "lat": 37.394627,
                    "lng": 127.113249,
                    "category": 1,
                }
            ],
        }
        mock_request.return_value = mock_response

        # 실제 성공하는 파라미터로 API 호출
        response = client._make_request(
            method="GET",
            endpoint="/api/apt/bounding",
            params=sample_working_params,
        )

        # 성공 확인
        assert response.success, "성공하는 파라미터로 API 호출이 성공해야 합니다"
        assert response.status_code == 200, f"상태 코드가 200이어야 합니다: {response.status_code}"

        # API 요청 확인
        mock_request.assert_called_once()
        call_args = mock_request.call_args

        # URL 확인
        assert "/api/apt/bounding" in call_args[0][1], "엔드포인트가 /api/apt/bounding이어야 합니다"

        # 파라미터 확인
        params = call_args[1]["params"]
        assert params["map"] == "google", "map 파라미터가 google이어야 합니다"
        assert params["apt"] == "", "apt 파라미터가 빈 문자열이어야 합니다"
        assert params["screenWidth"] == 1200, "screenWidth 파라미터가 1200이어야 합니다"
        assert params["screenHeight"] == 924, "screenHeight 파라미터가 924이어야 합니다"

    @patch("requests.Session.request")
    def test_required_parameters_step_by_step(self, mock_request, client, sample_working_params):
        """파라미터별 테스트: 필수 파라미터를 하나씩 추가하며 성공 조건 확인"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response

        # 최소한의 파라미터로 시작
        minimal_params = {
            "startX": sample_working_params["startX"],
            "endX": sample_working_params["endX"],
            "startY": sample_working_params["startY"],
            "endY": sample_working_params["endY"],
        }

        # 필수 파라미터들을 하나씩 추가하며 테스트
        required_params = [
            ("map", "google"),
            ("level", "17"),
            ("screenWidth", 1200),
            ("screenHeight", 924),
            ("apt", ""),
            ("areaNo", ""),
        ]

        current_params = minimal_params.copy()

        for param_name, param_value in required_params:
            current_params[param_name] = param_value

            # API 호출
            response = client._make_request(
                method="GET",
                endpoint="/api/apt/bounding",
                params=current_params,
            )

            # 각 단계에서 성공하는지 확인
            assert response.success, f"파라미터 {param_name} 추가 후 API 호출이 성공해야 합니다"

            # 요청 파라미터 확인
            call_args = mock_request.call_args
            actual_params = call_args[1]["params"]
            assert (
                actual_params[param_name] == param_value
            ), f"파라미터 {param_name}이(가) {param_value}로 설정되어야 합니다"

    @patch("requests.Session.request")
    def test_endpoint_comparison_working_vs_broken(
        self, mock_request, client, sample_working_params
    ):
        """작동하는 엔드포인트와 현재 엔드포인트 비교"""
        # 실패 응답 설정 (404)
        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        mock_response_404.headers = {"content-type": "text/html"}
        mock_response_404.text = "<h1>404 Not Found</h1>"

        # 성공 응답 설정
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.headers = {"content-type": "application/json"}
        mock_response_200.json.return_value = {"success": True, "data": []}

        # 엔드포인트별로 다른 응답 반환
        def side_effect(*args, **kwargs):
            if kwargs.get("endpoint", "") == "/api/v2/apartments-bounding":
                return mock_response_404
            else:
                return mock_response_200

        mock_request.side_effect = side_effect

        # 현재 잘못된 엔드포인트 테스트
        response_broken = client._make_request(
            method="GET",
            endpoint="/api/v2/apartments-bounding",
            params=sample_working_params,
        )
        assert not response_broken.success, "잘못된 엔드포인트는 실패해야 합니다"
        assert response_broken.status_code == 404, "잘못된 엔드포인트는 404를 반환해야 합니다"

        # 올바른 엔드포인트 테스트
        response_working = client._make_request(
            method="GET",
            endpoint="/api/apt/bounding",
            params=sample_working_params,
        )
        assert response_working.success, "올바른 엔드포인트는 성공해야 합니다"
        assert response_working.status_code == 200, "올바른 엔드포인트는 200을 반환해야 합니다"

    def test_searchparams_to_dict_includes_all_required(self, sample_working_params):
        """SearchParams.to_dict()가 필수 파라미터를 모두 포함하는지 확인"""
        params = SearchParams(
            bbox=(
                sample_working_params["startX"],
                sample_working_params["startY"],
                sample_working_params["endX"],
                sample_working_params["endY"],
            ),
            level=17,
            tradeType=0,
        )

        param_dict = params.to_dict()

        # 필수 파라미터 확인
        assert "map" in param_dict, "map 파라미터가 필수입니다"
        assert "screenWidth" in param_dict, "screenWidth 파라미터가 필수입니다"
        assert "screenHeight" in param_dict, "screenHeight 파라미터가 필수입니다"
        assert "apt" in param_dict, "apt 파라미터가 필수입니다"

        # 값 확인
        assert param_dict["map"] == "google", "map은 google이어야 합니다"
        assert param_dict["screenWidth"] == 1200, "screenWidth는 1200이어야 합니다"
        assert param_dict["screenHeight"] == 924, "screenHeight는 924이어야 합니다"
        assert param_dict["apt"] == "", "apt는 빈 문자열이어야 합니다"

    @patch("requests.Session.request")
    def test_api_headers_validation(self, mock_request, client, sample_working_params):
        """API 헤더 검증"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response

        # API 호출
        client._make_request(
            method="GET",
            endpoint="/api/apt/bounding",
            params=sample_working_params,
        )

        # 요청 헤더 확인
        call_args = mock_request.call_args
        headers = call_args[1]["headers"]

        # 필수 헤더 확인
        assert "User-Agent" in headers, "User-Agent 헤더가 필요합니다"
        assert "Accept" in headers, "Accept 헤더가 필요합니다"
        assert "Referer" in headers, "Referer 헤더가 필요합니다"
        assert (
            headers.get("Accept") == "application/json, text/plain, */*"
        ), "Accept 헤더가 application/json을 포함해야 합니다"

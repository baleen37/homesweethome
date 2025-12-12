"""강력한 API 응답 처리 테스트

손상되거나 비정상적인 API 응답을 처리하는 능력을 검증합니다.
"""

# Import test setup to configure path and mocks

import json
from unittest.mock import Mock, patch

import requests

from src.crawler.api.hogangnono_client import APIResponse, HogangnonoAPIClient
from src.crawler.config import CrawlerConfig


class TestAPIResponseHandling:
    """API 응답 처리 강건성 테스트"""

    def test_malformed_json_response(self):
        """손상된 JSON 응답 처리 테스트"""
        # 손상된 JSON 응답 모의
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = '{"incomplete": json'  # 손상된 JSON

        # APIResponse 처리
        api_response = APIResponse.from_response(mock_response)

        # 성공적으로 처리되어야 함 (HTML로 간주)
        assert api_response.success is True
        assert api_response.status_code == 200
        assert "raw_content" in api_response.data

    def test_missing_required_fields(self):
        """필수 필드가 누락된 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            # "data" 필드 누락
            "error": None,
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공하지만 data는 None
        assert api_response.success is True
        assert api_response.data is None
        assert api_response.status_code == 200

    def test_null_response_data(self):
        """null 데이터 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = None

        api_response = APIResponse.from_response(mock_response)

        # 성공하지만 data는 None
        assert api_response.success is True
        assert api_response.data is None

    def test_empty_array_response(self):
        """빈 배열 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = []

        api_response = APIResponse.from_response(mock_response)

        # 성공하고 빈 배열 반환
        assert api_response.success is True
        assert api_response.data == []

    def test_response_with_unexpected_structure(self):
        """예상치 못한 구조의 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "unexpected": {"nested": {"structure": ["data1", "data2"]}}
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공하고 원본 데이터 반환
        assert api_response.success is True
        assert api_response.data == {"unexpected": {"nested": {"structure": ["data1", "data2"]}}}

    def test_html_response_with_json_content_type(self):
        """JSON Content-Type이지만 HTML인 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "<html><body>HTML content</body></html>"

        api_response = APIResponse.from_response(mock_response)

        # HTML로 성공 처리
        assert api_response.success is True
        assert api_response.data["raw_content"] == "<html><body>HTML content</body></html>"

    def test_server_error_without_message(self):
        """메시지 없는 서버 에러 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": False
            # "error" 필드 없음
        }
        mock_response.reason = "Internal Server Error"

        api_response = APIResponse.from_response(mock_response)

        # 실패 처리
        assert api_response.success is False
        assert "HTTP error: 500" in api_response.error
        assert api_response.status_code == 500

    def test_response_with_none_values(self):
        """null 값을 포함한 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {"id": None, "name": None, "address": "서울시 강남구"},
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리 (null 값은 그대로 유지)
        assert api_response.success is True
        assert api_response.data["data"]["id"] is None
        assert api_response.data["data"]["name"] is None
        assert api_response.data["data"]["address"] == "서울시 강남구"

    def test_unicode_content_in_response(self):
        """유니코드 콘텐츠가 포함된 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json; charset=utf-8"}
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "name": "래미안아파트",
                "address": "서울특별시 강남구 역삼동",
                "description": "최고급 아파트 🏢",
            },
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리 (유니코드 보존)
        assert api_response.success is True
        assert api_response.data["data"]["name"] == "래미안아파트"
        assert "🏢" in api_response.data["data"]["description"]

    def test_extremely_large_response(self):
        """매우 큰 응답 처리 테스트"""
        # 대용량 데이터 생성
        large_data = []
        for i in range(10000):
            large_data.append(
                {
                    "id": f"apt_{i}",
                    "name": f"아파트{i}",
                    "description": "A" * 1000,  # 1000자 설명
                }
            )

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": large_data}

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리
        assert api_response.success is True
        assert len(api_response.data["data"]) == 10000

    def test_response_with_special_characters(self):
        """특수 문자가 포함된 응답 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "name": "테스트'아파트\"테스트",
                "address": "서울시 강남구\n개포동",
                "description": "특수문자: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            },
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리 (특수문자 보존)
        assert api_response.success is True
        assert "'" in api_response.data["data"]["name"]
        assert '"' in api_response.data["data"]["name"]
        assert "\n" in api_response.data["data"]["address"]

    @patch("requests.Session.request")
    def test_api_client_robust_handling(self, mock_request):
        """API 클라이언트의 강건한 처리 테스트"""
        # 설정
        config = CrawlerConfig()
        client = HogangnonoAPIClient(config)

        # 다양한 손상된 응답 시뮬레이션
        test_cases = [
            # Case 1: 손상된 JSON
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "json_side_effect": json.JSONDecodeError("Invalid", "", 0),
                "text": '{"invalid": json',
            },
            # Case 2: 누락된 필드
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "json_return": {"success": True},  # data 누락
            },
            # Case 3: 서버 에러
            {
                "status_code": 500,
                "headers": {"content-type": "application/json"},
                "json_return": {"success": False},
            },
        ]

        for case in test_cases:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = case["status_code"]
            mock_response.headers = case["headers"]

            if "json_side_effect" in case:
                mock_response.json.side_effect = case["json_side_effect"]
                mock_response.text = case.get("text", "")
            else:
                mock_response.json.return_value = case["json_return"]

            mock_request.return_value = mock_response

            # API 호출
            response = client._make_request("GET", "/test")

            # 항상 APIResponse 객체 반환
            assert isinstance(response, APIResponse)
            assert response.status_code == case["status_code"]
            assert response.error is not None or response.data is not None

    def test_nested_null_values(self):
        """중첩된 null 값 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "complex": {
                    "id": "123",
                    "name": None,
                    "address": {"gu": None, "dong": "역삼동", "detail": None},
                },
                "transactions": None,
            },
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리
        assert api_response.success is True
        assert api_response.data["data"]["complex"]["name"] is None
        assert api_response.data["data"]["complex"]["address"]["gu"] is None
        assert api_response.data["data"]["transactions"] is None

    def test_response_with_numeric_strings(self):
        """문자열 형태의 숫자 처리 테스트"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {"id": "123", "price": "500000", "area": "84.5", "build_year": "2020"},
        }

        api_response = APIResponse.from_response(mock_response)

        # 성공 처리 (문자열 그대로 유지)
        assert api_response.success is True
        assert api_response.data["data"]["id"] == "123"
        assert api_response.data["data"]["price"] == "500000"
        assert isinstance(api_response.data["data"]["area"], str)

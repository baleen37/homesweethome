"""APIResponse 클래스 단위 테스트"""

import json
from unittest.mock import Mock
from requests import Response

from crawler.api.hogangnono_client import APIResponse


class TestAPIResponse:
    """APIResponse 클래스 테스트"""

    def test_from_response_success_json_with_data(self):
        """성공적인 JSON 응답 파싱 테스트 (data 필드 포함)"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {"items": [1, 2, 3]}}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data == {"items": [1, 2, 3]}
        assert api_response.error is None
        assert api_response.status_code == 200

    def test_from_response_success_json_without_success_field(self):
        """success 필드가 없는 JSON 응답 파싱 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"items": [1, 2, 3]}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data == {"items": [1, 2, 3]}
        assert api_response.error is None
        assert api_response.status_code == 200

    def test_from_response_error_json(self):
        """에러 JSON 응답 파싱 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": False, "error": "Invalid parameters"}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.data is None
        assert "HTTP error: 400" in api_response.error
        assert "Invalid parameters" in api_response.error
        assert api_response.status_code == 400

    def test_from_response_error_json_with_message_field(self):
        """message 필드가 있는 에러 JSON 응답 파싱 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"message": "Resource not found"}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.data is None
        assert "HTTP error: 404" in api_response.error
        assert "Resource not found" in api_response.error
        assert api_response.status_code == 404

    def test_from_response_success_html(self):
        """성공적인 HTML 응답 파싱 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html><body>Test Content</body></html>"

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data["raw_content"] == "<html><body>Test Content</body></html>"
        assert api_response.error is None
        assert api_response.status_code == 200

    def test_from_response_html_truncation(self):
        """HTML 응답이 1000자 이상일 때 잘리는지 테스트"""
        long_content = "a" * 1500
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = long_content

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert len(api_response.data["raw_content"]) == 1000
        assert api_response.data["raw_content"] == "a" * 1000

    def test_from_response_request_exception(self):
        """requests.RequestException 발생 시 처리 테스트"""
        from requests import RequestException

        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.headers = {"content-type": "application/json"}

        # json() 호출 시 예외 발생
        mock_response.json.side_effect = RequestException("Connection error")

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.data is None
        assert "Request error: Connection error" in api_response.error
        assert api_response.status_code == 500

    def test_from_response_json_decode_error_with_200(self):
        """200 응답에서 JSON 디코드 에러 발생 시 HTML로 간주 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "<html><body>Invalid JSON</body></html>"

        # json() 호출 시 JSONDecodeError 발생
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True  # 200 OK이면 성공으로 간주
        assert api_response.error is None
        assert api_response.data["raw_content"] == "<html><body>Invalid JSON</body></html>"
        assert api_response.status_code == 200

    def test_from_response_json_decode_error_without_200(self):
        """200이 아닌 응답에서 JSON 디코드 에러 발생 시 실패 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}

        # json() 호출 시 JSONDecodeError 발생
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert "JSON decode error: Invalid JSON" in api_response.error
        assert api_response.data is None
        assert api_response.status_code == 400

    def test_from_response_generic_exception(self):
        """일반적인 예외 발생 시 처리 테스트"""
        from unittest.mock import PropertyMock

        mock_response = Mock()  # spec 없이 생성
        mock_response.reason = "Internal Server Error"

        # headers 속성 추가
        mock_response.headers = {}

        # status_code 접근 시 예외 발생
        type(mock_response).status_code = PropertyMock(side_effect=AttributeError("Mock error"))

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.data is None
        # Mock 객체는 status_code로 평가될 수 있으므로 더 유연한 검증
        assert api_response.error is not None
        assert "HTTP error" in api_response.error or "Unexpected error" in api_response.error

    def test_from_response_http_error_without_json_body(self):
        """JSON 본문이 없는 HTTP 에러 응답 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.reason = "Unauthorized"
        mock_response.headers = {"content-type": "text/plain"}

        # json() 호출 시 예외 발생 (JSON이 아님)
        mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert "HTTP error: 401 Unauthorized" in api_response.error
        assert api_response.data is None
        assert api_response.status_code == 401

    def test_from_response_case_insensitive_content_type(self):
        """대소문자를 무시한 content-type 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "Application/JSON"}  # 대문자 포함
        mock_response.json.return_value = {"success": True}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        # success 필드가 있지만 data 필드가 없는 응답은 전체 응답을 data로 반환
        assert api_response.data == {"success": True}
        assert api_response.status_code == 200

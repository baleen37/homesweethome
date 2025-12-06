"""
에러 인젝션 헬퍼 - 테스트를 위한 제어된 에러 주입
"""
import random
from typing import Any, Optional, Callable, Dict, List
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class ErrorInjector:
    """테스트를 위한 에러 인젝션 헬퍼 클래스"""

    def __init__(self):
        self.call_count = 0
        self.error_config = {}
        self.call_history: List[Dict[str, Any]] = []

    def configure(self, error_config: Dict[str, Any]):
        """
        에러 인젝션 패턴 설정

        예시:
        {
            "error_after": 3,  # 3번의 성공 호출 후 에러 주입
            "error_type": "timeout",  # 에러 타입
            "error_probability": 0.5,  # 50% 확률로 에러 발생
            "error_message": "Simulated timeout",  # 에러 메시지
            "max_injections": 2,  # 최대 에러 주입 횟수
            "retry_after": 5  # 5번의 호출 후 다시 에러 주입 시작
        }
        """
        self.error_config = error_config
        self.call_count = 0
        self.call_history = []

    def reset(self):
        """인젝터 상태 초기화"""
        self.call_count = 0
        self.call_history = []

    def maybe_inject_error(self, default_return: Optional[Any] = None) -> Optional[Any]:
        """
        현재 호출에서 에러를 주입해야 하는지 확인

        Returns:
            - 에러가 주입된 경우: 해당 에러를 발생시킴
            - 에러가 주입되지 않은 경우: None 반환
            - 특정 값을 반환해야 하는 경우: 해당 값 반환
        """
        self.call_count += 1
        self.call_history.append({"call_number": self.call_count, "injected": False})

        # 설정된 에러 주입 횟수 초과 확인
        max_injections = self.error_config.get("max_injections", float('inf'))
        injected_count = sum(1 for h in self.call_history if h["injected"])
        if injected_count >= max_injections:
            return None

        # 대기 기간 확인
        retry_after = self.error_config.get("retry_after")
        if retry_after and self.call_count < retry_after:
            return None

        # 특정 호출 횟수 후에만 에러 시작
        error_after = self.error_config.get("error_after", 0)
        if self.call_count < error_after:
            return None

        # 에러 확률 확인
        error_probability = self.error_config.get("error_probability", 0)
        if random.random() > error_probability:
            return None

        # 에러 주입
        error_type = self.error_config.get("error_type", "exception")
        error_message = self.error_config.get("error_message", "Simulated error")

        # 호출 기록 업데이트
        self.call_history[-1]["injected"] = True

        # 타입에 따른 에러 생성
        if error_type == "timeout":
            raise PlaywrightTimeoutError(error_message)
        elif error_type == "connection":
            raise ConnectionError(error_message)
        elif error_type == "rate_limit":
            return {"error": {"message": f"HTTP 429: {error_message}"}}
        elif error_type == "server_error":
            return {"error": {"message": f"HTTP 500: {error_message}"}}
        elif error_type == "invalid_response":
            return {"invalid": "response structure"}
        elif error_type == "return_value":
            return self.error_config.get("error_return_value", default_return)
        else:
            raise Exception(error_message)

    def get_injection_stats(self) -> Dict[str, Any]:
        """에러 인젝션 통계 반환"""
        total_calls = len(self.call_history)
        injected_calls = sum(1 for h in self.call_history if h["injected"])
        return {
            "total_calls": total_calls,
            "injected_calls": injected_calls,
            "injection_rate": injected_calls / total_calls if total_calls > 0 else 0,
            "last_injected_at": next(
                (h["call_number"] for h in reversed(self.call_history) if h["injected"]),
                None
            )
        }


class ScenarioErrorInjector:
    """다중 시나리오 에러 인젝터"""

    def __init__(self):
        self.scenarios = []
        self.current_scenario_index = 0
        self.call_count = 0

    def add_scenario(self, scenario: Dict[str, Any]):
        """에러 시나리오 추가"""
        self.scenarios.append(scenario)

    def maybe_inject_error(self) -> Optional[Any]:
        """현재 시나리오에 따라 에러 주입"""
        self.call_count += 1

        if self.current_scenario_index >= len(self.scenarios):
            return None

        current_scenario = self.scenarios[self.current_scenario_index]

        # 시나리오 완료 조건 확인
        scenario_end_after = current_scenario.get("end_after")
        if scenario_end_after and self.call_count >= scenario_end_after:
            self.current_scenario_index += 1
            return None

        # 에러 주입 조건 확인
        error_at = current_scenario.get("error_at")
        if error_at and self.call_count == error_at:
            error_type = current_scenario.get("error_type", "exception")
            error_message = current_scenario.get("error_message", "Scenario error")

            if error_type == "timeout":
                raise PlaywrightTimeoutError(error_message)
            elif error_type == "connection":
                raise ConnectionError(error_message)
            elif error_type == "rate_limit":
                return {"error": {"message": f"HTTP 429: {error_message}"}}
            else:
                raise Exception(error_message)

        # 특정 값 반환
        return_value = current_scenario.get("return_value")
        if return_value is not None:
            return return_value

        return None


class MockResponseBuilder:
    """모의 응답 빌더"""

    @staticmethod
    def success_response(data: Any) -> Dict[str, Any]:
        """성공 응답 생성"""
        return {
            "result": data,
            "timestamp": "2025-12-07T00:00:00Z"
        }

    @staticmethod
    def error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            "error": {
                "message": message,
                "status": status_code,
                "code": f"ERR_{status_code}"
            }
        }

    @staticmethod
    def rate_limit_response(retry_after: int = 60) -> Dict[str, Any]:
        """Rate Limit 응답 생성"""
        return {
            "error": {
                "message": "HTTP 429: Too Many Requests",
                "retry_after": retry_after
            }
        }

    @staticmethod
    def timeout_response() -> Dict[str, Any]:
        """타임아웃 응답 생성"""
        raise PlaywrightTimeoutError("Request timed out")

    @staticmethod
    def connection_error_response() -> None:
        """연결 에러 응답 생성"""
        raise ConnectionError("Connection failed")

    @staticmethod
    def invalid_response() -> Dict[str, Any]:
        """잘못된 형식의 응답 생성"""
        return {"invalid": "response structure"}

    @staticmethod
    def large_response(item_count: int = 10000) -> Dict[str, Any]:
        """대용량 응답 생성"""
        data = [{"item": f"item_{i}"} for i in range(item_count)]
        return MockResponseBuilder.success_response({"items": data})


class ErrorSequence:
    """정의된 순서대로 에러 발생"""

    def __init__(self, responses: List[Any]):
        self.responses = responses
        self.index = 0

    def next(self) -> Any:
        """다음 응답/에러 반환"""
        if self.index >= len(self.responses):
            return None

        response = self.responses[self.index]
        self.index += 1

        # 에러인 경우 예외 발생
        if isinstance(response, Exception):
            raise response

        return response

    def reset(self):
        """시퀀스 초기화"""
        self.index = 0

    @property
    def has_more(self) -> bool:
        """더 많은 응답이 있는지 확인"""
        return self.index < len(self.responses)
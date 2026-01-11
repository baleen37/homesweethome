"""네이버 부동산 Front API 클라이언트

네이버 부동산 Front API (https://fin.land.naver.com)를 호출하는 클라이언트입니다.

API 엔드포인트:
- /front-api/v1/article/key - 매물 연관 키 조회
- /front-api/v1/article/basicInfo - 매물 상세 정보
- /front-api/v1/complex - 단지 정보
- /front-api/v1/complex/evStaion - 전기차 충전소 (오타 주의)
"""

import urllib.parse
from typing import Any

import requests


class NaverFrontAPIClient:
    """네이버 부동산 Front API 클라이언트"""

    BASE_URL = "https://fin.land.naver.com"

    # fin.land.naver.com은 PC 사이트이므로 Desktop User-Agent 사용
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://fin.land.naver.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self) -> None:
        """클라이언트 초기화"""
        self.base_url = self.BASE_URL

    # =============================================================================
    # Article Key 관련 메서드
    # =============================================================================

    def get_article_key_url(self, article_id: str) -> str:
        """매물 연관 키 조회 URL을 빌드합니다

        Args:
            article_id: 매물 ID

        Returns:
            요청 URL
        """
        endpoint = f"{self.base_url}/front-api/v1/article/key"
        params = {"articleId": article_id}
        query_string = urllib.parse.urlencode(params, doseq=True)
        return f"{endpoint}?{query_string}"

    def parse_article_key_response(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """매물 연관 키 응답을 파싱합니다

        Args:
            response: API 응답 딕셔너리

        Returns:
            파싱된 결과 딕셔너리 또는 None
        """
        if not response:
            return None
        result = response.get("result")
        if not result or not isinstance(result, dict):
            return None
        return {
            "complexNumber": result.get("complexNumber"),
            "pyeongTypeNumber": result.get("pyeongTypeNumber"),
            "articleId": result.get("articleId"),
        }

    # =============================================================================
    # Article Basic Info 관련 메서드
    # =============================================================================

    def get_article_basic_info_url(
        self, article_id: str, real_estate_type: str, trade_type: str
    ) -> str:
        """매물 상세 정보 조회 URL을 빌드합니다

        Args:
            article_id: 매물 ID
            real_estate_type: 부동산 유형 (APT, OPST 등)
            trade_type: 거래 유형 (A1=매매, B1=전세, B2=월세)

        Returns:
            요청 URL
        """
        endpoint = f"{self.base_url}/front-api/v1/article/basicInfo"
        params = {
            "articleId": article_id,
            "realEstateType": real_estate_type,
            "tradeType": trade_type,
        }
        query_string = urllib.parse.urlencode(params, doseq=True)
        return f"{endpoint}?{query_string}"

    def parse_basic_info_price(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """매물 상세 정보에서 가격 정보를 파싱합니다

        Args:
            response: API 응답 딕셔너리

        Returns:
            가격 정보 딕셔너리 또는 None
        """
        if not response:
            return None
        result = response.get("result")
        if not result or not isinstance(result, dict):
            return None
        article_detail = result.get("articleDetail")
        if not article_detail or not isinstance(article_detail, dict):
            return None
        return {
            "dealPrice": article_detail.get("dealPrice"),
            "warrantPrice": article_detail.get("warrantPrice"),
        }

    def parse_basic_info_detail(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """매물 상세 정보에서 상세 정보(층수, 방수, 방향)를 파싱합니다

        Args:
            response: API 응답 딕셔너리

        Returns:
            상세 정보 딕셔너리 또는 None
        """
        if not response:
            return None
        result = response.get("result")
        if not result or not isinstance(result, dict):
            return None
        article_detail = result.get("articleDetail")
        if not article_detail or not isinstance(article_detail, dict):
            return None
        return {
            "floorInfo": article_detail.get("floorInfo"),
            "roomCount": article_detail.get("roomCount"),
            "direction": article_detail.get("direction"),
        }

    def parse_basic_info_size(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """매물 상세 정보에서 면적 정보를 파싱합니다

        Args:
            response: API 응답 딕셔너리

        Returns:
            면적 정보 딕셔너리 또는 None
        """
        if not response:
            return None
        result = response.get("result")
        if not result or not isinstance(result, dict):
            return None
        article_detail = result.get("articleDetail")
        if not article_detail or not isinstance(article_detail, dict):
            return None
        return {
            "area1": article_detail.get("area1"),
            "area2": article_detail.get("area2"),
        }

    # =============================================================================
    # Complex 관련 메서드
    # =============================================================================

    def get_complex_url(self, complex_number: str) -> str:
        """단지 정보 조회 URL을 빌드합니다

        Args:
            complex_number: 단지번호

        Returns:
            요청 URL
        """
        endpoint = f"{self.base_url}/front-api/v1/complex"
        params = {"complexNumber": complex_number}
        query_string = urllib.parse.urlencode(params, doseq=True)
        return f"{endpoint}?{query_string}"

    def parse_complex_response(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """단지 정보 응답을 파싱합니다

        Args:
            response: API 응답 딕셔너리

        Returns:
            파싱된 결과 딕셔너리 또는 None
        """
        if not response:
            return None
        result = response.get("result")
        if not result or not isinstance(result, dict):
            return None
        return {
            "complexName": result.get("complexName"),
            "address": result.get("address"),
            "houseHoldCount": result.get("houseHoldCount"),
            "builtYear": result.get("builtYear"),
            "maxFloor": result.get("maxFloor"),
        }

    # =============================================================================
    # 전기차 충전소 관련 메서드 (evStaion 오타 유지)
    # =============================================================================

    def get_ev_station_url(self, complex_number: str) -> str:
        """전기차 충전소 조회 URL을 빌드합니다

        Args:
            complex_number: 단지번호

        Returns:
            요청 URL (오타 주의: evStaion)
        """
        # 네이버 API 사양에 따라 오타를 유지합니다
        endpoint = f"{self.base_url}/front-api/v1/complex/evStaion"
        params = {"complexNumber": complex_number}
        query_string = urllib.parse.urlencode(params, doseq=True)
        return f"{endpoint}?{query_string}"

    # =============================================================================
    # HTTP 요청 메서드
    # =============================================================================

    def fetch(self, url: str) -> dict[str, Any]:
        """헤더 포함 HTTP GET 요청

        Args:
            url: 요청 URL

        Returns:
            JSON 응답 딕셔너리

        Raises:
            requests.HTTPError: HTTP 요청 실패 시
            requests.JSONDecodeError: JSON 파싱 실패 시
        """
        response = requests.get(url, headers=self.DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()

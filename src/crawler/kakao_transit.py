"""카카오맵 대중교통 경로 검색 API 클라이언트.

이 모듈은 웹 스크래핑 기반의 BaseCrawler 패턴을 따르지 않고,
카카오맵 REST API를 직접 호출하여 대중교통 경로 정보를 가져옵니다.
"""

import logging
from typing import Any
from urllib.parse import urlencode

import requests

from crawler.coordinate_converter import wgs84_to_wcongnamul
from crawler.dto.kakao_transit import (
    KakaoTransitResponseDTO,
    KakaoTransitRouteDTO,
    KakaoTransitStepDTO,
)

# 주요 역/장소 좌표
MAJOR_LOCATIONS = {
    "강남역": {"latitude": 37.498095, "longitude": 127.027610},
    "판교역": {"latitude": 37.394726, "longitude": 127.111209},
    "광화문": {"latitude": 37.576022, "longitude": 126.976900},
    "서울역": {"latitude": 37.552987, "longitude": 126.972592},
    "여의도": {"latitude": 37.523890, "longitude": 126.926670},
}


class KakaoTransitCrawler:
    """
    카카오맵 대중교통 경로 검색 API 클라이언트

    BaseCrawler 패턴을 따르지 않는 외부 API 클라이언트입니다.
    카카오맵 REST API를 직접 호출하여 아파트 위치에서 주요 장소까지의
    대중교통 경로를 검색합니다.
    """

    BASE_URL = "https://map.kakao.com"
    API_URL = f"{BASE_URL}/route/pubtrans.json"

    def __init__(self, headless: bool = True):
        """
        Args:
            headless: Playwright 헤드리스 모드 (현재는 사용하지 않음)
        """
        self.headless = headless
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://map.kakao.com/",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def search_transit_route(
        self,
        start_lat: float,
        start_lon: float,
        end_name: str,
    ) -> KakaoTransitResponseDTO:
        """
        대중교통 경로 검색

        Args:
            start_lat: 출발지 위도
            start_lon: 출발지 경도
            end_name: 도착지 이름 (강남역, 판교역, 광화문, 서울역, 여의도 중 하나)

        Returns:
            KakaoTransitResponseDTO: 경로 검색 결과

        Raises:
            ValueError: 지원하지 않는 도착지인 경우
            requests.RequestException: API 요청 실패
        """
        if end_name not in MAJOR_LOCATIONS:
            raise ValueError(
                f"지원하지 않는 도착지입니다: {end_name}. "
                f"지원하는 장소: {list(MAJOR_LOCATIONS.keys())}"
            )

        end_location = MAJOR_LOCATIONS[end_name]

        # 위경도를 WCONGNAMUL 좌표로 변환
        start_x, start_y = wgs84_to_wcongnamul(start_lat, start_lon)
        end_x, end_y = wgs84_to_wcongnamul(end_location["latitude"], end_location["longitude"])

        params = {
            "inputCoordSystem": "WCONGNAMUL",
            "outputCoordSystem": "WCONGNAMUL",
            "service": "map.daum.net",
            "sX": start_x,
            "sY": start_y,
            "sName": "",  # 출발지 이름 (아파트 이름을 알 수 없으므로 비워둠)
            "sid": "",
            "eX": end_x,
            "eY": end_y,
            "eName": end_name,
            "eid": "",
        }

        url = f"{self.API_URL}?{urlencode(params)}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        # JSON 응답 파싱
        data = response.json()
        return self._parse_response(data, end_name)

    def _parse_response(self, data: dict[str, Any], end_name: str) -> KakaoTransitResponseDTO:
        """API 응답 파싱"""
        in_local = data.get("in_local", {})
        start = in_local.get("start", {})
        end = in_local.get("end", {})
        routes = in_local.get("routes", {})

        # 총 경로 수
        number_of_routes = in_local.get("numberOfRoutes", {})
        total_routes = int(number_of_routes.get("total", 0))

        # 경로 파싱 (routes는 리스트 형태)
        parsed_routes = []
        if isinstance(routes, list):
            for route_data in routes:
                if isinstance(route_data, dict):
                    parsed_routes.append(self._parse_route(route_data))
        elif isinstance(routes, dict):
            for route_id, route_data in routes.items():
                if isinstance(route_data, dict):
                    parsed_routes.append(self._parse_route(route_data))

        # 추천 경로 우선 정렬
        parsed_routes.sort(key=lambda r: (not r.recommended, r.ranking))

        return KakaoTransitResponseDTO(
            start_name=start.get("name", ""),
            start_x=float(start.get("x", 0)),
            start_y=float(start.get("y", 0)),
            end_name=end.get("name", end_name),
            end_x=float(end.get("x", 0)),
            end_y=float(end.get("y", 0)),
            total_routes=total_routes,
            routes=parsed_routes,
        )

    def _parse_route(self, route_data: dict[str, Any]) -> KakaoTransitRouteDTO:
        """단일 경로 파싱"""
        distance = route_data.get("distance", {})
        time = route_data.get("time", {})
        walking_distance = route_data.get("walkingDistance", {})
        walking_time = route_data.get("walkingTime", {})
        fare = route_data.get("fare", {})

        steps = []
        for step_data in route_data.get("steps", []):
            step = self._parse_step(step_data)
            if step:
                steps.append(step)

        return KakaoTransitRouteDTO(
            ranking=int(route_data.get("ranking", 0)),
            type=str(route_data.get("type", "")),
            distance=int(distance.get("value", 0)),
            distance_text=str(distance.get("text", "")),
            time=int(time.get("value", 0)),
            time_text=str(time.get("text", "")),
            walking_distance=int(walking_distance.get("value", 0)),
            walking_distance_text=str(walking_distance.get("text", "")),
            walking_time=int(walking_time.get("value", 0)),
            walking_time_text=str(walking_time.get("text", "")),
            transfers=int(route_data.get("transfers", 0)),
            fare_cash=int(fare.get("cash", 0)),
            fare_card=int(fare.get("card", 0)),
            recommended=bool(route_data.get("recommended", False)),
            shortest_time=bool(route_data.get("shortestTime", False)),
            least_transfer=bool(route_data.get("leastTransfer", False)),
            steps=steps,
        )

    def _parse_step(self, step_data: dict[str, Any]) -> KakaoTransitStepDTO | None:
        """단일 스텝 파싱"""
        distance = step_data.get("distance", {})
        time = step_data.get("time", {})

        return KakaoTransitStepDTO(
            action=str(step_data.get("action", "")),
            action_name=str(step_data.get("actionName", "")),
            type=str(step_data.get("type", "")) if step_data.get("type") else None,
            distance=int(distance.get("value", 0)) if distance.get("value") else None,
            distance_text=str(distance.get("text", "")) if distance.get("text") else None,
            time=int(time.get("value", 0)) if time.get("value") else None,
            time_text=str(time.get("text", "")) if time.get("text") else None,
            start_location=step_data.get("startLocation"),
            end_location=step_data.get("endLocation"),
            lane=step_data.get("lane"),
            station_count=int(step_data.get("stationCount", 0))
            if step_data.get("stationCount")
            else None,
        )

    def search_multiple_destinations(
        self, start_lat: float, start_lon: float, destinations: list[str]
    ) -> dict[str, KakaoTransitResponseDTO]:
        """
        여러 도착지에 대한 경로 검색

        Args:
            start_lat: 출발지 위도
            start_lon: 출발지 경도
            destinations: 도착지 이름 리스트

        Returns:
            dict[str, KakaoTransitResponseDTO]: 도착지별 경로 검색 결과
        """
        results = {}
        for dest in destinations:
            try:
                results[dest] = self.search_transit_route(start_lat, start_lon, dest)
            except ValueError as e:
                # 지원하지 않는 도착지인 경우
                self.logger.warning("지원하지 않는 도착지입니다: %s - %s", dest, e)
            except requests.RequestException as e:
                # API 요청 실패
                self.logger.error("API 요청 실패 (%s): %s", dest, e)
            except Exception as e:
                # 기타 예기치 않은 에러
                self.logger.error("경로 검색 중 알 수 없는 에러 발생 (%s): %s", dest, e)
        return results

"""카카오맵 대중교통 경로 검색 DTO."""

from dataclasses import dataclass
from typing import Any


@dataclass
class KakaoTransitStepDTO:
    """대중교통 경로의 각 단계 (승차, 하차, 환승, 도보 등)"""

    action: str  # DEPARTURE, GETON, TRANSFER, GETOFF, MOVE, ARRIVAL
    action_name: str  # 한글 액션명
    type: str | None = None  # SUBWAY, BUS, WALKING 등
    distance: int | None = None  # 거리 (미터)
    distance_text: str | None = None  # 거리 텍스트 (예: "5.2km")
    time: int | None = None  # 소요시간 (초)
    time_text: str | None = None  # 시간 텍스트 (예: "10분")
    start_location: dict[str, Any] | None = None  # 시작 장소 정보
    end_location: dict[str, Any] | None = None  # 도착 장소 정보
    lane: dict[str, Any] | None = None  # 노선 정보 (지하철 호선, 버스 번호 등)
    station_count: int | None = None  # 역 수


@dataclass
class KakaoTransitRouteDTO:
    """대중교통 경로 정보"""

    ranking: int  # 경로 순위
    type: str  # SUBWAY, BUS, MIXED
    distance: int  # 총 거리 (미터)
    distance_text: str  # 거리 텍스트
    time: int  # 총 소요시간 (초)
    time_text: str  # 시간 텍스트
    walking_distance: int  # 도보 거리 (미터)
    walking_distance_text: str  # 도보 거리 텍스트
    walking_time: int  # 도보 시간 (초)
    walking_time_text: str  # 도보 시간 텍스트
    transfers: int  # 환승 횟수
    fare_cash: int  # 현금 요금
    fare_card: int  # 카드 요금
    recommended: bool  # 추천 경로 여부
    shortest_time: bool  # 최단 시간 여부
    least_transfer: bool  # 최소 환승 여부
    steps: list[KakaoTransitStepDTO]  # 경로 상세 단계


@dataclass
class KakaoTransitResponseDTO:
    """대중교통 경로 검색 응답"""

    start_name: str  # 출발지 이름
    start_x: float  # 출발지 X 좌표
    start_y: float  # 출발지 Y 좌표
    end_name: str  # 도착지 이름
    end_x: float  # 도착지 X 좌표
    end_y: float  # 도착지 Y 좌표
    total_routes: int  # 전체 경로 수
    routes: list[KakaoTransitRouteDTO]  # 경로 리스트


@dataclass
class KakaoTransitAccessInfoDTO:
    """시작점에서 첫 역까지 접근 정보"""

    route_ranking: int  # 경로 순위
    station_name: str  # 역 이름
    walking_distance: int  # 도보 거리 (미터)
    walking_time: int  # 도보 소요시간 (초)
    walking_time_text: str  # 도보 소요시간 텍스트 (예: "3분")


@dataclass
class KakaoTransitRawResponseDTO:
    """카카오맵 대중교통 API 원천 응답 데이터"""

    raw_data: dict[str, Any]  # API 응답 JSON 그대로 저장

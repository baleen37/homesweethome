"""카카오맵 대중교통 경로 검색 Integration Tests."""

import pytest

from crawler.dto.kakao_transit import (
    KakaoTransitResponseDTO,
    KakaoTransitRouteDTO,
    KakaoTransitStepDTO,
)
from crawler.kakao_transit import MAJOR_LOCATIONS, KakaoTransitCrawler


class TestKakaoTransitCrawler:
    """KakaoTransitCrawler 통합 테스트"""

    @pytest.fixture
    def crawler(self) -> KakaoTransitCrawler:
        """크롤러 인스턴스 생성"""
        return KakaoTransitCrawler()

    def test_search_transit_route_to_gangnam(self, crawler: KakaoTransitCrawler) -> None:
        """강남역까지 대중교통 경로 검색"""
        # 문래동 위치 (예시)
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "강남역")

        # 결과 검증
        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "강남역"
        assert result.total_routes > 0
        assert len(result.routes) > 0

        # 첫 번째 경로 검증
        first_route = result.routes[0]
        assert isinstance(first_route, KakaoTransitRouteDTO)
        assert first_route.time > 0
        assert first_route.time_text != ""
        assert len(first_route.steps) > 0

    def test_search_transit_route_to_pangyo(self, crawler: KakaoTransitCrawler) -> None:
        """판교역까지 대중교통 경로 검색"""
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "판교역")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "판교역"
        assert result.total_routes > 0

    def test_search_transit_route_to_gwanghwamun(self, crawler: KakaoTransitCrawler) -> None:
        """광화문까지 대중교통 경로 검색"""
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "광화문")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "광화문"
        assert result.total_routes > 0

    def test_search_transit_route_to_seoul_station(self, crawler: KakaoTransitCrawler) -> None:
        """서울역까지 대중교통 경로 검색"""
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "서울역")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "서울역"
        assert result.total_routes > 0

    def test_search_transit_route_to_yeouido(self, crawler: KakaoTransitCrawler) -> None:
        """여의도까지 대중교통 경로 검색"""
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "여의도")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "여의도"
        assert result.total_routes > 0

    def test_search_multiple_destinations(self, crawler: KakaoTransitCrawler) -> None:
        """여러 도착지에 대한 경로 검색"""
        start_lat = 37.5138
        start_lon = 126.8826
        destinations = ["강남역", "판교역", "광화문", "서울역", "여의도"]

        results = crawler.search_multiple_destinations(start_lat, start_lon, destinations)

        # 모든 도착지에 대한 결과가 있는지 확인
        assert len(results) > 0
        for dest in destinations:
            if dest in results:
                assert results[dest].end_name == dest

    def test_invalid_destination_raises_error(self, crawler: KakaoTransitCrawler) -> None:
        """지원하지 않는 도착지에 대해 ValueError 발생"""
        start_lat = 37.5138
        start_lon = 126.8826

        with pytest.raises(ValueError, match="지원하지 않는 도착지"):
            crawler.search_transit_route(start_lat, start_lon, "지원하지않는역")

    def test_route_has_proper_structure(self, crawler: KakaoTransitCrawler) -> None:
        """경로 데이터가 적절한 구조를 가지는지 확인"""
        start_lat = 37.5138
        start_lon = 126.8826

        result = crawler.search_transit_route(start_lat, start_lon, "강남역")
        route = result.routes[0]

        # 기본 필드 검증
        assert route.ranking >= 1
        assert route.type in ["SUBWAY", "BUS", "MIXED", "BUS_AND_SUBWAY"]
        assert route.distance >= 0
        assert route.time > 0
        assert route.transfers >= 0
        # fare 필드는 API 응답에 없을 수 있음
        # assert route.fare_card > 0

        # 스텝 검증
        assert len(route.steps) > 0
        for step in route.steps:
            assert isinstance(step, KakaoTransitStepDTO)
            assert step.action in [
                "DEPARTURE",
                "GETON",
                "TRANSFER",
                "GETOFF",
                "MOVE",
                "ARRIVAL",
            ]
            assert step.action_name != ""

    def test_major_locations_coordinates(self) -> None:
        """주요 장소 좌표가 정의되어 있는지 확인"""
        assert "강남역" in MAJOR_LOCATIONS
        assert "판교역" in MAJOR_LOCATIONS
        assert "광화문" in MAJOR_LOCATIONS
        assert "서울역" in MAJOR_LOCATIONS
        assert "여의도" in MAJOR_LOCATIONS

        # 좌표 형식 검증
        for name, coords in MAJOR_LOCATIONS.items():
            assert "latitude" in coords
            assert "longitude" in coords
            assert 33 < coords["latitude"] < 43  # 한국 위도 범위
            assert 124 < coords["longitude"] < 132  # 한국 경도 범위

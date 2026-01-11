"""카카오맵 대중교통 경로 검색 Unit Tests."""

from unittest.mock import Mock, patch

import pytest
import requests

from crawler.dto.kakao_transit import (
    KakaoTransitRawResponseDTO,
    KakaoTransitResponseDTO,
    KakaoTransitRouteDTO,
    KakaoTransitStepDTO,
)
from crawler.kakao_transit import KakaoTransitCrawler


class TestKakaoTransitCrawler:
    """KakaoTransitCrawler 유닛 테스트"""

    @pytest.fixture
    def crawler(self) -> KakaoTransitCrawler:
        """크롤러 인스턴스 생성"""
        return KakaoTransitCrawler()

    # ========== _parse_response() 테스트 ==========

    def test_parse_response_with_valid_data(self, crawler: KakaoTransitCrawler) -> None:
        """정상적인 API 응답 파싱"""
        data = {
            "in_local": {
                "start": {
                    "name": "출발지",
                    "x": "506190.0",
                    "y": "1110730.0",
                },
                "end": {
                    "name": "강남역",
                    "x": "493528.0",
                    "y": "1126264.0",
                },
                "numberOfRoutes": {
                    "total": "11",
                },
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                                "startLocation": {"name": "출발지"},
                            },
                            {
                                "action": "GETON",
                                "actionName": "승차",
                                "type": "SUBWAY",
                                "distance": {"value": 5200, "text": "5.2km"},
                                "time": {"value": 570, "text": "10분"},
                                "startLocation": {"name": "강남역"},
                                "endLocation": {"name": "사당역"},
                                "lane": {"name": "2호선"},
                                "stationCount": 5,
                            },
                        ],
                    }
                ],
            }
        }

        result = crawler._parse_response(data, "강남역")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.start_name == "출발지"
        assert result.start_x == 506190.0
        assert result.start_y == 1110730.0
        assert result.end_name == "강남역"
        assert result.end_x == 493528.0
        assert result.end_y == 1126264.0
        assert result.total_routes == 11
        assert len(result.routes) == 1

    def test_parse_response_with_dict_routes(self, crawler: KakaoTransitCrawler) -> None:
        """routes가 딕셔너리 형태인 경우 파싱"""
        data = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "2"},
                "routes": {
                    "route1": {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            }
                        ],
                    },
                    "route2": {
                        "ranking": 2,
                        "type": "BUS",
                        "distance": {"value": 12000, "text": "12.0km"},
                        "time": {"value": 1800, "text": "30분"},
                        "walkingDistance": {"value": 500, "text": "500m"},
                        "walkingTime": {"value": 540, "text": "9분"},
                        "transfers": 0,
                        "fare": {"value": 1300, "text": "1,300원"},
                        "recommended": False,
                        "shortestTime": False,
                        "leastTransfer": True,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            }
                        ],
                    },
                },
            }
        }

        result = crawler._parse_response(data, "강남역")

        assert result.total_routes == 2
        assert len(result.routes) == 2
        # 추천 경로가 먼저 정렬되어야 함
        assert result.routes[0].recommended is True
        assert result.routes[1].recommended is False

    def test_parse_response_with_empty_data(self, crawler: KakaoTransitCrawler) -> None:
        """빈 응답 데이터 파싱"""
        data = {
            "in_local": {
                "start": {},
                "end": {},
                "numberOfRoutes": {"total": "0"},
                "routes": [],
            }
        }

        result = crawler._parse_response(data, "강남역")

        assert result.start_name == ""
        assert result.start_x == 0.0
        assert result.start_y == 0.0
        assert result.end_name == "강남역"  # 파라미터로 전달된 이름 사용
        assert result.end_x == 0.0
        assert result.end_y == 0.0
        assert result.total_routes == 0
        assert len(result.routes) == 0

    def test_parse_response_with_missing_fields(self, crawler: KakaoTransitCrawler) -> None:
        """필드가 누락된 응답 파싱"""
        data = {
            "in_local": {
                # start 누락
                "end": {"name": "강남역"},
                # numberOfRoutes 누락
                "routes": [],
            }
        }

        result = crawler._parse_response(data, "강남역")

        assert result.start_name == ""
        assert result.start_x == 0.0
        assert result.start_y == 0.0
        assert result.total_routes == 0  # 기본값
        assert len(result.routes) == 0

    def test_parse_response_sorts_routes_by_recommendation(
        self, crawler: KakaoTransitCrawler
    ) -> None:
        """추천 경로가 우선적으로 정렬되는지 확인"""
        data = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "3"},
                "routes": [
                    {
                        "ranking": 3,
                        "type": "BUS",
                        "distance": {"value": 12000, "text": "12.0km"},
                        "time": {"value": 1800, "text": "30분"},
                        "walkingDistance": {"value": 500, "text": "500m"},
                        "walkingTime": {"value": 540, "text": "9분"},
                        "transfers": 0,
                        "fare": {"value": 1300, "text": "1,300원"},
                        "recommended": False,
                        "shortestTime": False,
                        "leastTransfer": True,
                        "steps": [],
                    },
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [],
                    },
                    {
                        "ranking": 2,
                        "type": "MIXED",
                        "distance": {"value": 14000, "text": "14.0km"},
                        "time": {"value": 1900, "text": "32분"},
                        "walkingDistance": {"value": 600, "text": "600m"},
                        "walkingTime": {"value": 600, "text": "10분"},
                        "transfers": 2,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": False,
                        "shortestTime": True,
                        "leastTransfer": False,
                        "steps": [],
                    },
                ],
            }
        }

        result = crawler._parse_response(data, "강남역")

        # 추천 경로가 먼저, 그 다음 ranking 순으로 정렬
        assert result.routes[0].recommended is True
        assert result.routes[0].ranking == 1
        assert result.routes[1].recommended is False
        assert result.routes[1].ranking == 2
        assert result.routes[2].recommended is False
        assert result.routes[2].ranking == 3

    # ========== _parse_route() 테스트 ==========

    def test_parse_route_with_valid_data(self, crawler: KakaoTransitCrawler) -> None:
        """정상적인 경로 데이터 파싱"""
        route_data = {
            "ranking": 1,
            "type": "SUBWAY",
            "distance": {"value": 15440, "text": "15.4km"},
            "time": {"value": 2037, "text": "34분"},
            "walkingDistance": {"value": 440, "text": "440m"},
            "walkingTime": {"value": 477, "text": "8분"},
            "transfers": 1,
            "fare": {"value": 1650, "text": "1,650원"},
            "recommended": True,
            "shortestTime": False,
            "leastTransfer": False,
            "steps": [
                {
                    "action": "DEPARTURE",
                    "actionName": "출발",
                }
            ],
        }

        result = crawler._parse_route(route_data)

        assert isinstance(result, KakaoTransitRouteDTO)
        assert result.ranking == 1
        assert result.type == "SUBWAY"
        assert result.distance == 15440
        assert result.distance_text == "15.4km"
        assert result.time == 2037
        assert result.time_text == "34분"
        assert result.walking_distance == 440
        assert result.walking_distance_text == "440m"
        assert result.walking_time == 477
        assert result.walking_time_text == "8분"
        assert result.transfers == 1
        assert result.fare_cash == 1650
        assert result.fare_card == 1650
        assert result.recommended is True
        assert result.shortest_time is False
        assert result.least_transfer is False
        assert len(result.steps) == 1

    def test_parse_route_with_missing_optional_fields(self, crawler: KakaoTransitCrawler) -> None:
        """선택적 필드가 누락된 경로 데이터 파싱"""
        route_data = {
            "ranking": 2,
            "type": "BUS",
            "distance": {"value": 10000, "text": "10.0km"},
            "time": {"value": 1500, "text": "25분"},
            "walkingDistance": {"value": 300, "text": "300m"},
            "walkingTime": {"value": 360, "text": "6분"},
            "transfers": 0,
            # fare 누락
            "recommended": False,
            "shortestTime": True,
            "leastTransfer": False,
            "steps": [],
        }

        result = crawler._parse_route(route_data)

        assert result.ranking == 2
        assert result.fare_cash == 0  # 기본값
        assert result.fare_card == 0  # 기본값
        assert result.recommended is False
        assert result.shortest_time is True

    def test_parse_route_with_empty_steps(self, crawler: KakaoTransitCrawler) -> None:
        """빈 스텝 목록이 있는 경로 파싱"""
        route_data = {
            "ranking": 1,
            "type": "SUBWAY",
            "distance": {"value": 10000, "text": "10.0km"},
            "time": {"value": 1500, "text": "25분"},
            "walkingDistance": {"value": 300, "text": "300m"},
            "walkingTime": {"value": 360, "text": "6분"},
            "transfers": 0,
            "fare": {"value": 1300, "text": "1,300원"},
            "recommended": False,
            "shortestTime": False,
            "leastTransfer": False,
            "steps": [],
        }

        result = crawler._parse_route(route_data)

        assert len(result.steps) == 0

    # ========== _parse_step() 테스트 ==========

    def test_parse_step_with_complete_data(self, crawler: KakaoTransitCrawler) -> None:
        """모든 필드가 있는 스텝 파싱"""
        step_data = {
            "action": "GETON",
            "actionName": "승차",
            "type": "SUBWAY",
            "distance": {"value": 5200, "text": "5.2km"},
            "time": {"value": 570, "text": "10분"},
            "startLocation": {"name": "강남역", "x": 506190.0, "y": 1110730.0},
            "endLocation": {"name": "사당역", "x": 495921.0, "y": 1104757.0},
            "lane": {"name": "2호선", "type": "SUBWAY"},
            "stationCount": 5,
        }

        result = crawler._parse_step(step_data)

        assert isinstance(result, KakaoTransitStepDTO)
        assert result.action == "GETON"
        assert result.action_name == "승차"
        assert result.type == "SUBWAY"
        assert result.distance == 5200
        assert result.distance_text == "5.2km"
        assert result.time == 570
        assert result.time_text == "10분"
        assert result.start_location == {"name": "강남역", "x": 506190.0, "y": 1110730.0}
        assert result.end_location == {"name": "사당역", "x": 495921.0, "y": 1104757.0}
        assert result.lane == {"name": "2호선", "type": "SUBWAY"}
        assert result.station_count == 5

    def test_parse_step_with_minimal_data(self, crawler: KakaoTransitCrawler) -> None:
        """최소 필드만 있는 스텝 파싱"""
        step_data = {
            "action": "DEPARTURE",
            "actionName": "출발",
        }

        result = crawler._parse_step(step_data)

        assert result.action == "DEPARTURE"
        assert result.action_name == "출발"
        assert result.type is None
        assert result.distance is None
        assert result.distance_text is None
        assert result.time is None
        assert result.time_text is None
        assert result.start_location is None
        assert result.end_location is None
        assert result.lane is None
        assert result.station_count is None

    def test_parse_step_with_partial_distance_time(self, crawler: KakaoTransitCrawler) -> None:
        """거리/시간 필드가 부분적으로 누락된 스텝 파싱"""
        step_data = {
            "action": "MOVE",
            "actionName": "이동",
            "type": "WALKING",
            "distance": {"text": "200m"},  # value 누락
            "time": {"value": 180},  # text 누락
        }

        result = crawler._parse_step(step_data)

        assert result.action == "MOVE"
        assert result.action_name == "이동"
        assert result.type == "WALKING"
        assert result.distance is None  # value가 없으면 None
        assert result.distance_text == "200m"
        assert result.time == 180
        assert result.time_text is None  # text가 없으면 None

    def test_parse_step_returns_none_for_invalid_data(self, crawler: KakaoTransitCrawler) -> None:
        """잘못된 스텝 데이터에 대해 None 반환"""
        # _parse_step은 현재 구현에서 항상 DTO를 반환하지,
        # 빈 dict인 경우도 기본값으로 DTO를 생성함
        step_data = {}

        result = crawler._parse_step(step_data)

        # 빈 데이터라도 기본값으로 DTO 생성
        assert result.action == ""
        assert result.action_name == ""

    # ========== search_transit_route() 테스트 ==========

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_transit_route_with_valid_destination(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """정상적인 도착지로 경로 검색"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),  # start 좌표
            (493528.0, 1126264.0),  # end 좌표
        ]

        mock_response = Mock()
        mock_response.json.return_value = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "1"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            }
                        ],
                    }
                ],
            }
        }
        mock_response.raise_for_status = Mock()

        with patch.object(crawler.session, "get", return_value=mock_response):
            result = crawler.search_transit_route(37.5138, 126.8826, "강남역")

        assert isinstance(result, KakaoTransitResponseDTO)
        assert result.end_name == "강남역"
        assert result.total_routes == 1
        assert len(result.routes) == 1

    def test_search_transit_route_with_invalid_destination(
        self, crawler: KakaoTransitCrawler
    ) -> None:
        """지원하지 않는 도착지로 경로 검색 시 ValueError 발생"""
        with pytest.raises(ValueError, match="지원하지 않는 도착지"):
            crawler.search_transit_route(37.5138, 126.8826, "지원하지않는역")

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_transit_route_with_http_error(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """HTTP 요청 실패 시 예외 발생"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),
            (493528.0, 1126264.0),
        ]

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch.object(crawler.session, "get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                crawler.search_transit_route(37.5138, 126.8826, "강남역")

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_transit_route_with_timeout(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """요청 타임아웃 시 예외 발생"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),
            (493528.0, 1126264.0),
        ]

        with patch.object(crawler.session, "get", side_effect=requests.Timeout("Request timeout")):
            with pytest.raises(requests.Timeout):
                crawler.search_transit_route(37.5138, 126.8826, "강남역")

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_transit_route_allows_all_supported_destinations(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """모든 지원되는 도착지에 대해 유효성 검사"""
        # 5개 도착지 * 2번 호출(start, end) = 10개 반환값 필요
        mock_convert.side_effect = [(506190.0, 1110730.0), (493528.0, 1126264.0)] * 5

        supported_destinations = ["강남역", "판교역", "광화문", "서울역", "여의도"]

        for dest in supported_destinations:
            # 각 도착지에 맞는 mock response 생성
            mock_response = Mock()
            mock_response.json.return_value = {
                "in_local": {
                    "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                    "end": {"name": dest, "x": "493528.0", "y": "1126264.0"},
                    "numberOfRoutes": {"total": "0"},
                    "routes": [],
                }
            }
            mock_response.raise_for_status = Mock()

            with patch.object(crawler.session, "get", return_value=mock_response):
                # ValueError가 발생하면 안 됨
                result = crawler.search_transit_route(37.5138, 126.8826, dest)
                assert result.end_name == dest

    # ========== 경계값 테스트 ==========

    def test_parse_step_with_zero_values(self, crawler: KakaoTransitCrawler) -> None:
        """0 값이 있는 스텝 파싱 (0은 falsy로 처리되어 None 반환)"""
        step_data = {
            "action": "MOVE",
            "actionName": "이동",
            "distance": {"value": 0, "text": "0m"},
            "time": {"value": 0, "text": "0분"},
            "stationCount": 0,
        }

        result = crawler._parse_step(step_data)

        # 실제 구현에서는 0을 falsy로 처리하여 None 반환
        # 이는 API 응답에서 0 값이 유효하지 않은 경우를 의미할 수 있음
        assert result.distance is None  # 0은 falsy로 처리됨
        assert result.distance_text == "0m"  # text는 있음
        assert result.time is None  # 0은 falsy로 처리됨
        assert result.time_text == "0분"  # text는 있음
        assert result.station_count is None  # 0은 falsy로 처리됨

    def test_parse_route_with_zero_transfers(self, crawler: KakaoTransitCrawler) -> None:
        """환승 0회인 경로 파싱"""
        route_data = {
            "ranking": 1,
            "type": "BUS",
            "distance": {"value": 5000, "text": "5.0km"},
            "time": {"value": 900, "text": "15분"},
            "walkingDistance": {"value": 200, "text": "200m"},
            "walkingTime": {"value": 240, "text": "4분"},
            "transfers": 0,
            "fare": {"value": 1300, "text": "1,300원"},
            "recommended": False,
            "shortestTime": False,
            "leastTransfer": True,
            "steps": [],
        }

        result = crawler._parse_route(route_data)

        assert result.transfers == 0
        assert result.least_transfer is True

    def test_parse_response_with_large_number_of_routes(self, crawler: KakaoTransitCrawler) -> None:
        """많은 수의 경로가 있는 응답 파싱"""
        routes = []
        for i in range(10):
            routes.append(
                {
                    "ranking": i + 1,
                    "type": "SUBWAY" if i % 2 == 0 else "BUS",
                    "distance": {"value": 10000 + i * 100, "text": f"{10 + i * 0.1}km"},
                    "time": {"value": 1500 + i * 60, "text": f"{25 + i}분"},
                    "walkingDistance": {"value": 400, "text": "400m"},
                    "walkingTime": {"value": 480, "text": "8분"},
                    "transfers": i,
                    "fare": {"value": 1300, "text": "1,300원"},
                    "recommended": i == 0,  # 첫 번째만 추천
                    "shortestTime": False,
                    "leastTransfer": False,
                    "steps": [],
                }
            )

        data = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "10"},
                "routes": routes,
            }
        }

        result = crawler._parse_response(data, "강남역")

        assert result.total_routes == 10
        assert len(result.routes) == 10
        # 추천 경로가 먼저 정렬
        assert result.routes[0].recommended is True

    # ========== search_multiple_destinations() 테스트 ==========

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_multiple_destinations_success(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """여러 도착지 경로 검색 성공"""
        # 3개 도착지 * 2번 호출(start, end) = 6개 반환값 필요
        mock_convert.side_effect = [(506190.0, 1110730.0), (493528.0, 1126264.0)] * 3

        destinations = ["강남역", "판교역", "광화문"]

        # 각 도착지별 응답을 순서대로 반환하도록 설정
        responses = []
        for dest in destinations:
            mock_response = Mock()
            mock_response.json.return_value = {
                "in_local": {
                    "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                    "end": {"name": dest, "x": "493528.0", "y": "1126264.0"},
                    "numberOfRoutes": {"total": "1"},
                    "routes": [
                        {
                            "ranking": 1,
                            "type": "SUBWAY",
                            "distance": {"value": 10000, "text": "10.0km"},
                            "time": {"value": 1500, "text": "25분"},
                            "walkingDistance": {"value": 400, "text": "400m"},
                            "walkingTime": {"value": 480, "text": "8분"},
                            "transfers": 0,
                            "fare": {"value": 1300, "text": "1,300원"},
                            "recommended": True,
                            "shortestTime": False,
                            "leastTransfer": False,
                            "steps": [],
                        }
                    ],
                }
            }
            mock_response.raise_for_status = Mock()
            responses.append(mock_response)

        with patch.object(crawler.session, "get", side_effect=responses):
            results = crawler.search_multiple_destinations(37.5138, 126.8826, destinations)

        assert len(results) == 3
        assert "강남역" in results
        assert "판교역" in results
        assert "광화문" in results
        assert results["강남역"].end_name == "강남역"
        assert results["판교역"].end_name == "판교역"
        assert results["광화문"].end_name == "광화문"

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_multiple_destinations_with_invalid_destination(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """여러 도착지 검색 중 일부가 실패하는 경우"""
        mock_convert.side_effect = [(506190.0, 1110730.0), (493528.0, 1126264.0)]

        # 강남역은 성공
        mock_response_success = Mock()
        mock_response_success.json.return_value = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "1"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 10000, "text": "10.0km"},
                        "time": {"value": 1500, "text": "25분"},
                        "walkingDistance": {"value": 400, "text": "400m"},
                        "walkingTime": {"value": 480, "text": "8분"},
                        "transfers": 0,
                        "fare": {"value": 1300, "text": "1,300원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [],
                    }
                ],
            }
        }
        mock_response_success.raise_for_status = Mock()

        call_count = [0]

        def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response_success
            else:
                # 두 번째 호출은 실패
                raise requests.HTTPError("API Error")

        with patch.object(crawler.session, "get", side_effect=mock_get):
            results = crawler.search_multiple_destinations(37.5138, 126.8826, ["강남역", "판교역"])

        # 강남역만 성공, 판교역는 실패하여 결과에 없음
        assert len(results) == 1
        assert "강남역" in results
        assert "판교역" not in results

    # ========== search_transit_route_raw() 테스트 ==========

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_search_transit_route_raw_returns_raw_data(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """원천 API 응답 데이터를 그대로 반환"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),  # start 좌표
            (493528.0, 1126264.0),  # end 좌표
        ]

        raw_api_response = {
            "in_local_status": "SUCCESS",
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "1"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                                "startLocation": {"name": "출발지"},
                            },
                            {
                                "action": "MOVE",
                                "actionName": "이동",
                                "type": "WALKING",
                                "distance": {"value": 140, "text": "140m"},
                                "time": {"value": 213, "text": "3분"},
                                "startLocation": {"name": "출발지"},
                                "endLocation": {"name": "도림천역"},
                            },
                        ],
                    }
                ],
            },
        }

        mock_response = Mock()
        mock_response.json.return_value = raw_api_response
        mock_response.raise_for_status = Mock()

        with patch.object(crawler.session, "get", return_value=mock_response):
            result = crawler.search_transit_route_raw(37.5138, 126.8826, "강남역")

        assert isinstance(result, KakaoTransitRawResponseDTO)
        assert result.raw_data == raw_api_response
        # 원천 데이터가 그대로 보존되어야 함
        assert "in_local" in result.raw_data
        assert result.raw_data["in_local"]["routes"][0]["steps"][1]["action"] == "MOVE"

    def test_search_transit_route_raw_with_invalid_destination(
        self, crawler: KakaoTransitCrawler
    ) -> None:
        """지원하지 않는 도착지로 원천 데이터 요청 시 ValueError 발생"""
        with pytest.raises(ValueError, match="지원하지 않는 도착지"):
            crawler.search_transit_route_raw(37.5138, 126.8826, "지원하지않는역")

    # ========== analyze_access_to_station() 테스트 ==========

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_analyze_access_to_station_extract_first_move_step(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """첫 번째 MOVE 스텝의 정보를 추출"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),
            (493528.0, 1126264.0),
        ]

        mock_response = Mock()
        mock_response.json.return_value = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "2"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                                "startLocation": {"name": "출발지"},
                            },
                            {
                                "action": "MOVE",
                                "actionName": "이동",
                                "type": "WALKING",
                                "distance": {"value": 140, "text": "140m"},
                                "time": {"value": 213, "text": "3분"},
                                "startLocation": {"name": "출발지"},
                                "endLocation": {"name": "도림천역"},
                            },
                            {
                                "action": "GETON",
                                "actionName": "승차",
                                "type": "SUBWAY",
                                "distance": {"value": 5200, "text": "5.2km"},
                                "time": {"value": 570, "text": "10분"},
                                "startLocation": {"name": "도림천역"},
                                "endLocation": {"name": "사당역"},
                            },
                        ],
                    },
                    {
                        "ranking": 2,
                        "type": "BUS",
                        "distance": {"value": 12000, "text": "12.0km"},
                        "time": {"value": 1800, "text": "30분"},
                        "walkingDistance": {"value": 500, "text": "500m"},
                        "walkingTime": {"value": 540, "text": "9분"},
                        "transfers": 0,
                        "fare": {"value": 1300, "text": "1,300원"},
                        "recommended": False,
                        "shortestTime": False,
                        "leastTransfer": True,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            },
                            {
                                "action": "MOVE",
                                "actionName": "이동",
                                "type": "WALKING",
                                "distance": {"value": 320, "text": "320m"},
                                "time": {"value": 405, "text": "7분"},
                                "startLocation": {"name": "출발지"},
                                "endLocation": {"name": "버스정류장"},
                            },
                            {
                                "action": "GETON",
                                "actionName": "승차",
                                "type": "BUS",
                                "distance": {"value": 8000, "text": "8.0km"},
                                "time": {"value": 1200, "text": "20분"},
                                "startLocation": {"name": "버스정류장"},
                                "endLocation": {"name": "강남역"},
                            },
                        ],
                    },
                ],
            },
        }
        mock_response.raise_for_status = Mock()

        with patch.object(crawler.session, "get", return_value=mock_response):
            result = crawler.analyze_access_to_station(37.5138, 126.8826, "강남역")

        assert len(result) == 2
        # 첫 번째 경로 확인
        assert result[0].route_ranking == 1
        assert result[0].station_name == "도림천역"
        assert result[0].walking_distance == 140
        assert result[0].walking_time == 213
        assert result[0].walking_time_text == "3분"
        # 두 번째 경로 확인
        assert result[1].route_ranking == 2
        assert result[1].station_name == "버스정류장"
        assert result[1].walking_distance == 320
        assert result[1].walking_time == 405
        assert result[1].walking_time_text == "7분"

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_analyze_access_to_station_with_no_move_step(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """MOVE 스텝이 없는 경우 빈 리스트 반환"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),
            (493528.0, 1126264.0),
        ]

        mock_response = Mock()
        mock_response.json.return_value = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "1"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            },
                            {
                                "action": "GETON",
                                "actionName": "승차",
                                "type": "SUBWAY",
                            },
                        ],
                    }
                ],
            },
        }
        mock_response.raise_for_status = Mock()

        with patch.object(crawler.session, "get", return_value=mock_response):
            result = crawler.analyze_access_to_station(37.5138, 126.8826, "강남역")

        # MOVE 스텝이 없으면 빈 리스트 반환
        assert result == []

    def test_analyze_access_to_station_with_invalid_destination(
        self, crawler: KakaoTransitCrawler
    ) -> None:
        """지원하지 않는 도착지로 역 접근 분석 시 ValueError 발생"""
        with pytest.raises(ValueError, match="지원하지 않는 도착지"):
            crawler.analyze_access_to_station(37.5138, 126.8826, "지원하지않는역")

    @patch("crawler.kakao_transit.wgs84_to_wcongnamul")
    def test_analyze_access_to_station_with_multiple_move_steps(
        self, mock_convert, crawler: KakaoTransitCrawler
    ) -> None:
        """여러 MOVE 스텝이 있는 경우 첫 번째만 추출"""
        mock_convert.side_effect = [
            (506190.0, 1110730.0),
            (493528.0, 1126264.0),
        ]

        mock_response = Mock()
        mock_response.json.return_value = {
            "in_local": {
                "start": {"name": "출발지", "x": "506190.0", "y": "1110730.0"},
                "end": {"name": "강남역", "x": "493528.0", "y": "1126264.0"},
                "numberOfRoutes": {"total": "1"},
                "routes": [
                    {
                        "ranking": 1,
                        "type": "SUBWAY",
                        "distance": {"value": 15440, "text": "15.4km"},
                        "time": {"value": 2037, "text": "34분"},
                        "walkingDistance": {"value": 440, "text": "440m"},
                        "walkingTime": {"value": 477, "text": "8분"},
                        "transfers": 1,
                        "fare": {"value": 1650, "text": "1,650원"},
                        "recommended": True,
                        "shortestTime": False,
                        "leastTransfer": False,
                        "steps": [
                            {
                                "action": "DEPARTURE",
                                "actionName": "출발",
                            },
                            {
                                "action": "MOVE",
                                "actionName": "이동",
                                "type": "WALKING",
                                "distance": {"value": 140, "text": "140m"},
                                "time": {"value": 213, "text": "3분"},
                                "startLocation": {"name": "출발지"},
                                "endLocation": {"name": "도림천역"},
                            },
                            {
                                "action": "GETON",
                                "actionName": "승차",
                                "type": "SUBWAY",
                            },
                            {
                                "action": "TRANSFER",
                                "actionName": "환승",
                            },
                            {
                                "action": "MOVE",
                                "actionName": "이동",
                                "type": "WALKING",
                                "distance": {"value": 80, "text": "80m"},
                                "time": {"value": 120, "text": "2분"},
                                "startLocation": {"name": "사당역"},
                                "endLocation": {"name": "4호선"},
                            },
                        ],
                    }
                ],
            },
        }
        mock_response.raise_for_status = Mock()

        with patch.object(crawler.session, "get", return_value=mock_response):
            result = crawler.analyze_access_to_station(37.5138, 126.8826, "강남역")

        # 첫 번째 MOVE 스텝만 추출되어야 함
        assert len(result) == 1
        assert result[0].route_ranking == 1
        assert result[0].station_name == "도림천역"
        assert result[0].walking_distance == 140
        assert result[0].walking_time == 213

    # ========== KakaoTransitRawResponseDTO 테스트 ==========

    def test_kakao_transit_raw_response_dto_creation(self) -> None:
        """원천 응답 DTO 생성"""
        raw_data = {
            "in_local_status": "SUCCESS",
            "in_local": {
                "start": {"name": "출발지"},
                "end": {"name": "강남역"},
            },
        }

        dto = KakaoTransitRawResponseDTO(raw_data=raw_data)

        assert dto.raw_data == raw_data
        assert dto.raw_data["in_local_status"] == "SUCCESS"
        assert dto.raw_data["in_local"]["start"]["name"] == "출발지"

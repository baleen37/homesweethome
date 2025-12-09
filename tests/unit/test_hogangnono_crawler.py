"""HogangnonoCrawler 단위 테스트"""

from unittest.mock import patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.api.hogangnono_client import APIResponse


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig(
        user_agent="test-agent",
        timeout=10.0,
    )


@pytest.fixture
def temp_output_dir(tmp_path):
    """임시 출력 디렉토리"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def crawler(config, temp_output_dir):
    """테스트용 크롤러 객체"""
    return HogangnonoCrawler(
        config=config,
        output_dir=temp_output_dir,
        region_bounds=(37.5, 126.9, 37.6, 127.0),
    )


class TestHogangnonoCrawler:
    """HogangnonoCrawler 테스트 클래스"""

    def test_init(self, crawler):
        """초기화 테스트"""
        assert crawler.base_url == "https://hogangnono.com"
        assert crawler.region_bounds == (37.5, 126.9, 37.6, 127.0)
        assert crawler.output_dir.exists()

    def test_get_endpoint(self, crawler):
        """엔드포인트 반환 테스트"""
        endpoint = crawler.get_endpoint()
        assert endpoint == "/api/apt/bounding"

    def test_get_params(self, crawler):
        """요청 파라미터 반환 테스트"""
        params = crawler.get_params()
        expected = {
            "lat_min": 37.5,
            "lng_min": 126.9,
            "lat_max": 37.6,
            "lng_max": 127.0,
            "zoom": 14,
            "limit": 100,
            "apt_type": "apart",
        }
        assert params == expected

    def test_parse_response_empty_data(self, crawler):
        """빈 응답 파싱 테스트"""
        response_data = {"data": []}
        result = crawler.parse_response(response_data)
        assert result == []

    def test_parse_response_with_items(self, crawler):
        """아이템이 있는 응답 파싱 테스트"""
        # 호갱노노 형식의 더미 데이터
        response_data = {
            "data": [
                {
                    "id": "12345",
                    "name": "테스트아파트",
                    "address": "서울시 강남구 테헤란로",
                    "lat": 37.5,
                    "lng": 127.0,
                    "build_year": "2020",
                    "households": 500,
                    "floors": 35,
                    "trade": {
                        "type": "sale",
                        "area": "84.95",
                        "floor": "5층",
                        "price": "10,000,000",
                        "date": "20241201",
                    },
                }
            ]
        }

        result = crawler.parse_response(response_data)
        assert len(result) == 1

        # 매핑된 데이터 확인
        item = result[0]
        assert item["complex_id"] == "12345"
        assert item["complex_name"] == "테스트아파트"
        assert item["trade_type"] == "A1"
        assert item["trade_type_name"] == "매매"
        assert item["pyeong_type_number"] == 26  # 84.95 / 3.305785

    def test_parse_response_different_trade_types(self, crawler):
        """다양한 거래 타입 파싱 테스트"""
        response_data = {
            "data": [
                {
                    "id": "1",
                    "name": "매매아파트",
                    "recent_trade": {
                        "type": "sale",
                        "deal_price": "500,000,000",
                    },
                },
                {
                    "id": "2",
                    "name": "전세아파트",
                    "recent_trade": {
                        "type": "jeonse",
                        "jeonse_price": "300,000,000",
                    },
                },
                {
                    "id": "3",
                    "name": "월세아파트",
                    "recent_trade": {
                        "type": "monthly",
                        "deposit": "100,000,000",
                        "monthly_rent": "500,000",
                    },
                },
            ]
        }

        result = crawler.parse_response(response_data)
        assert len(result) == 3

        # 매매
        assert result[0]["trade_type"] == "A1"
        assert result[0]["deal_price"] == 500000000

        # 전세
        assert result[1]["trade_type"] == "B1"
        assert result[1]["deposit"] == 300000000

        # 월세
        assert result[2]["trade_type"] == "B2"
        assert result[2]["deposit"] == 100000000
        assert result[2]["monthly_rent"] == 500000

    def test_map_to_naver_format(self, crawler):
        """네이버 형식 매핑 테스트"""
        hogangnono_item = {
            "id": "test123",
            "name": "테스트단지",
            "address": "서울특별시 강남구",
            "latitude": 37.5,
            "longitude": 127.0,
            "completion_year": "2019",
            "household_count": 300,
            "max_floor": 20,
            "trade": {
                "type": "sale",
                "exclusive_area": "59.34",
                "floor_info": "10",
                "deal_price": "800,000,000",
                "trade_date": "2024-12-01",
            },
        }

        result = crawler._map_to_naver_format(hogangnono_item)
        assert result is not None

        # 단지 정보
        assert result["complex_id"] == "test123"
        assert result["complex_name"] == "테스트단지"
        assert result["build_year"] == 2019
        assert result["households"] == 300

        # 거래 정보
        assert result["trade_type"] == "A1"
        assert result["pyeong_type_number"] == 18  # 59.34 / 3.305785
        assert result["deal_price"] == 800000000
        assert result["trade_year"] == 2024

    def test_crawl_region_success(self, crawler):
        """지역 크롤링 성공 테스트"""
        # Mock API 응답
        mock_response = APIResponse(
            success=True,
            data={
                "data": {
                    "items": [
                        {
                            "id": "1",
                            "name": "아파트1",
                            "trade": {"type": "sale", "deal_price": "500,000,000"},
                        },
                        {
                            "id": "2",
                            "name": "아파트2",
                            "trade": {"type": "jeonse", "jeonse_price": "300,000,000"},
                        },
                    ]
                }
            },
        )

        with patch.object(
            crawler.hogangnono_client, "get_apartments_bounding", return_value=mock_response
        ):
            complexes, transactions = crawler.crawl_region()

        assert len(complexes) == 2
        assert len(transactions) == 2
        assert complexes[0]["complex_name"] == "아파트1"
        assert transactions[0]["trade_type"] == "A1"
        assert transactions[1]["trade_type"] == "B1"

    def test_crawl_region_with_pagination(self, crawler):
        """페이지네이션 포함 크롤링 테스트"""
        # 첫 페이지 응답
        first_response = APIResponse(
            success=True, data={"data": {"items": [{"id": "1", "name": "아파트1"}]}}
        )

        # 두 번째 페이지 응답
        second_response = APIResponse(
            success=True, data={"data": {"items": [{"id": "2", "name": "아파트2"}]}}
        )

        # 세 번째 페이지 (빈 응답)
        empty_response = APIResponse(success=True, data={"data": {"items": []}})

        with (
            patch.object(
                crawler.hogangnono_client, "get_apartments_bounding", return_value=first_response
            ),
            patch.object(
                crawler.hogangnono_client,
                "_make_request",
                side_effect=[second_response, empty_response],
            ),
        ):
            complexes, transactions = crawler.crawl_region(max_pages=5)

        assert len(complexes) == 2
        assert len(transactions) == 2

    def test_save_to_csv(self, crawler, temp_output_dir):
        """CSV 저장 테스트"""
        complexes = [
            {
                "complex_id": "1",
                "complex_name": "아파트1",
                "address": "주소1",
                "build_year": 2020,
                "households": 100,
                "floors": 10,
            }
        ]

        transactions = [
            {
                "complex_id": "1",
                "trade_type": "A1",
                "deal_price": 500000000,
                "trade_date": "20241201",
            }
        ]

        crawler.save_to_csv(complexes, transactions)

        # 파일 확인
        complexes_file = temp_output_dir / "hogangnono_complexes.csv"
        transactions_file = temp_output_dir / "hogangnono_transactions.csv"

        assert complexes_file.exists()
        assert transactions_file.exists()

        # 내용 확인
        with open(complexes_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "아파트1" in content

        with open(transactions_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "500000000" in content

    def test_crawl_and_save_integration(self, crawler):
        """크롤링과 저장 통합 테스트"""
        mock_response = APIResponse(
            success=True,
            data={
                "data": {
                    "items": [
                        {
                            "id": "1",
                            "name": "테스트아파트",
                            "address": "서울시 강남구",
                            "build_year": "2020",
                            "households": 200,
                            "floors": 15,
                            "trade": {
                                "type": "sale",
                                "deal_price": "1,000,000,000",
                                "date": "20241201",
                            },
                        }
                    ]
                }
            },
        )

        with patch.object(
            crawler.hogangnono_client, "get_apartments_bounding", return_value=mock_response
        ):
            crawler.crawl_and_save()

        # 파일이 생성되었는지 확인
        complexes_file = crawler.output_dir / "hogangnono_complexes.csv"
        transactions_file = crawler.output_dir / "hogangnono_transactions.csv"

        assert complexes_file.exists()
        assert transactions_file.exists()

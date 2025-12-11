"""HogangnonoCrawler 단위 테스트"""

from unittest.mock import patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.api.hogangnono_client import APIResponse
from crawler.utils.checkpoint import CheckpointManager


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

    def test_data_mapper_integration(self, crawler):
        """DataMapper 연동 테스트"""
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

        # Mock get_dong_code to return a test value
        with patch.object(crawler, "get_dong_code", return_value="11680500"):
            result = crawler.data_mapper.map_to_naver_format(
                hogangnono_item, fetch_dong_code_func=crawler.get_dong_code
            )

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

        # 주소 파싱 확인
        assert result["gu_name"] == "강남구"
        assert result["dong_name"] == ""  # 주소에 동 정보가 없음

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
        # The current implementation doesn't extract transactions
        assert len(transactions) == 0
        assert complexes[0]["complex_name"] == "아파트1"

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
        # transactions 파일은 데이터가 있을 때만 생성됨
        if transactions:
            assert transactions_file.exists()
        else:
            # 트랜잭션이 없을 경우 파일이 생성되지 않아야 함
            assert not transactions_file.exists()

        # 내용 확인
        with open(complexes_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "아파트1" in content

        if transactions:
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
        # 트랜잭션이 없을 경우 파일이 생성되지 않아야 함
        assert not transactions_file.exists()

    def test_filter_districts_all_seoul(self, crawler):
        """서울 전체 구 필터링"""
        all_regions = {
            "regionList": [
                {
                    "regionCode": "11",
                    "name": "서울",
                    "children": [
                        {"regionCode": "11680", "name": "강남구"},
                        {"regionCode": "11650", "name": "서초구"},
                    ],
                }
            ]
        }

        result = crawler._filter_districts(all_regions, regions=["11"], districts=None)

        assert len(result) == 2
        assert result[0]["regionCode"] == "11680"
        assert result[1]["regionCode"] == "11650"

    def test_filter_districts_specific(self, crawler):
        """특정 구만 필터링"""
        all_regions = {
            "regionList": [
                {
                    "regionCode": "11",
                    "name": "서울",
                    "children": [
                        {"regionCode": "11680", "name": "강남구"},
                        {"regionCode": "11650", "name": "서초구"},
                        {"regionCode": "11710", "name": "송파구"},
                    ],
                }
            ]
        }

        result = crawler._filter_districts(all_regions, regions=None, districts=["11680", "11710"])

        assert len(result) == 2
        assert result[0]["regionCode"] == "11680"
        assert result[1]["regionCode"] == "11710"

    def test_filter_districts_default_seoul(self, crawler):
        """기본값(서울) 필터링"""
        all_regions = {
            "regionList": [
                {
                    "regionCode": "11",
                    "name": "서울",
                    "children": [
                        {"regionCode": "11680", "name": "강남구"},
                        {"regionCode": "11650", "name": "서초구"},
                    ],
                },
                {
                    "regionCode": "26",
                    "name": "부산",
                    "children": [
                        {"regionCode": "26110", "name": "중구"},
                        {"regionCode": "26140", "name": "서구"},
                    ],
                },
            ]
        }

        result = crawler._filter_districts(all_regions, regions=None, districts=None)

        # 서울 구만 반환되어야 함
        assert len(result) == 2
        assert all(d["regionCode"].startswith("11") for d in result)

    def test_crawl_district(self, crawler):
        """단일 구/군 크롤링"""
        district = {"regionCode": "11680", "name": "강남구", "fullName": "서울특별시 강남구"}

        # Mock API 응답
        with patch.object(crawler, "_fetch_apartments_in_district") as mock_fetch:
            with patch.object(crawler.hogangnono_client, "get_apartment_detail") as mock_detail:
                with patch.object(
                    crawler.hogangnono_client, "get_apartment_transactions"
                ) as mock_trans:
                    with patch.object(crawler, "_save_apartment_data") as mock_save:
                        # 2개 단지 반환
                        mock_fetch.return_value = [
                            {"aptHash": "apt1", "aptName": "단지1"},
                            {"aptHash": "apt2", "aptName": "단지2"},
                        ]

                        # 상세 정보 Mock
                        mock_detail.return_value = APIResponse(
                            success=True, data={"parkingCount": 100}
                        )

                        # 실거래 내역 Mock
                        mock_trans.return_value = APIResponse(
                            success=True, data={"shortTermReport": []}
                        )

                        # 실행
                        crawler._crawl_district(district, full_period=False)

                        # 검증
                        assert mock_fetch.call_count == 1
                        assert mock_detail.call_count == 2
                        assert mock_trans.call_count == 2
                        assert mock_save.call_count == 2

    def test_crawl_district_skip_404(self, crawler):
        """404 에러 발생 시 건너뛰기 테스트"""
        district = {"regionCode": "11680", "name": "강남구"}

        with patch.object(crawler, "_fetch_apartments_in_district") as mock_fetch:
            with patch.object(crawler.hogangnono_client, "get_apartment_detail") as mock_detail:
                with patch.object(crawler, "_save_apartment_data") as mock_save:
                    # 단지 1개 반환
                    mock_fetch.return_value = [{"aptHash": "apt1", "aptName": "단지1"}]

                    # 404 에러 반환
                    mock_detail.return_value = APIResponse(
                        success=False, error="Not found", status_code=404
                    )

                    # 실행 - 예외 없이 처리되어야 함
                    crawler._crawl_district(district, full_period=False)

                    # save가 호출되지 않아야 함
                    mock_save.assert_not_called()

    def test_crawl_seoul_default(self, crawler):
        """기본값 서울 크롤링"""
        with patch.object(crawler.hogangnono_client, "get_regions") as mock_regions:
            with patch.object(crawler, "_filter_districts") as mock_filter:
                with patch.object(crawler, "_crawl_district") as mock_crawl:
                    with patch.object(crawler, "_save_checkpoint"):
                        # Mock 응답
                        mock_regions.return_value = APIResponse(
                            success=True, data={"regionList": []}
                        )
                        mock_filter.return_value = [{"regionCode": "11680", "name": "강남구"}]

                        # 실행
                        stats = crawler.crawl()

                        # 검증
                        mock_regions.assert_called_once()
                        mock_filter.assert_called_once()
                        mock_crawl.assert_called_once()
                        assert stats["dongs_processed"] == 1
                        assert stats["total_dongs"] == 1

    def test_checkpoint_manager_initialization(self, crawler):
        """체크포인트 매니저 초기화 테스트"""
        assert crawler.checkpoint_manager is not None
        assert crawler.checkpoint_manager.checkpoint is not None
        assert isinstance(crawler.checkpoint_manager, CheckpointManager)

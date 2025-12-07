import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture
def crawler_config() -> CrawlerConfig:
    return CrawlerConfig(timeout=30, headless=True, output_dir="output")


@pytest.fixture
def sample_api_response() -> dict[str, Any]:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "naver_api_response.json"
    with open(fixture_path) as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture
def sample_districts_data() -> dict[str, Any]:
    """테스트용 서울시 구 데이터"""
    return {
        "districts": [
            {
                "district_code": "11110",
                "district_name": "종로구",
                "dongs": [
                    {
                        "cortarNo": "1111010100",
                        "dong_name": "사직동",
                        "bounds": {
                            "leftLon": 126.97,
                            "rightLon": 126.99,
                            "topLat": 37.58,
                            "bottomLat": 37.56,
                        },
                    },
                    {
                        "cortarNo": "1111010300",
                        "dong_name": "삼청동",
                        "bounds": {
                            "leftLon": 126.98,
                            "rightLon": 127.00,
                            "topLat": 37.59,
                            "bottomLat": 37.57,
                        },
                    },
                ],
            },
            {
                "district_code": "11140",
                "district_name": "중구",
                "dongs": [
                    {
                        "cortarNo": "1114010100",
                        "dong_name": "소공동",
                        "bounds": {
                            "leftLon": 126.97,
                            "rightLon": 126.99,
                            "topLat": 37.56,
                            "bottomLat": 37.54,
                        },
                    },
                    {
                        "cortarNo": "1114010300",
                        "dong_name": "회현동",
                        "bounds": {
                            "leftLon": 126.98,
                            "rightLon": 127.00,
                            "topLat": 37.55,
                            "bottomLat": 37.53,
                        },
                    },
                ],
            },
            {
                "district_code": "11170",
                "district_name": "용산구",
                "dongs": [
                    {
                        "cortarNo": "1117010100",
                        "dong_name": "후암동",
                        "bounds": {
                            "leftLon": 126.96,
                            "rightLon": 126.98,
                            "topLat": 37.54,
                            "bottomLat": 37.52,
                        },
                    },
                ],
            },
        ]
    }


def test_get_url_returns_naver_real_estate_url(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    url = crawler.get_url()
    assert url == "https://new.land.naver.com/complexes"


def test_load_districts_data_returns_districts(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    districts = crawler._load_districts_data()

    assert "districts" in districts
    assert len(districts["districts"]) > 0
    assert "district_name" in districts["districts"][0]
    assert "dongs" in districts["districts"][0]


def test_parse_extracts_complex_data_from_api_response(
    crawler_config: CrawlerConfig, sample_api_response: dict[str, Any]
) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    results = crawler._parse_complex_list_api(sample_api_response)

    assert len(results) == 2
    assert results[0]["complex_name"] == "테스트아파트1"
    assert results[0]["complex_id"] == "149239"
    assert results[0]["real_estate_type"] == "아파트"
    assert results[0]["completion_year_month"] == "202403"
    assert results[0]["total_dong_count"] == 1
    assert results[0]["total_household_count"] == 151
    assert results[0]["min_area"] == "70.79"
    assert results[0]["max_area"] == "78.25"
    assert results[0]["deal_count"] == 5
    assert results[0]["lease_count"] == 3
    assert results[0]["total_article_count"] == 8


def test_parse_handles_empty_list(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    results = crawler._parse_complex_list_api({"totalCount": 0, "result": []})

    assert len(results) == 0


def test_fetch_dong_data_calls_api_with_correct_url(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page.evaluate
    mock_page = Mock()
    mock_page.evaluate.return_value = {
        "totalCount": 1,
        "result": [
            {
                "hscpNo": "123",
                "hscpNm": "테스트단지",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "202001",
                "totDongCnt": 1,
                "totHsehCnt": 100,
                "minSpc": "60",
                "maxSpc": "80",
                "dealCnt": 0,
                "leaseCnt": 0,
                "totalAtclCnt": 0,
            }
        ],
    }

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {
            "leftLon": 127.05,
            "rightLon": 127.07,
            "topLat": 37.52,
            "bottomLat": 37.50,
        },
    }

    results = crawler._fetch_dong_data(dong)

    assert len(results) == 1
    assert results[0]["complex_name"] == "테스트단지"
    mock_page.evaluate.assert_called_once()


def test_fetch_with_retry_retries_on_timeout(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    mock_page = Mock()
    mock_page.evaluate.side_effect = [
        TimeoutError("Timeout 1"),
        TimeoutError("Timeout 2"),
        {
            "totalCount": 1,
            "result": [
                {
                    "hscpNo": "123",
                    "hscpNm": "성공",
                    "hscpTypeNm": "아파트",
                    "useAprvYmd": "202001",
                    "totDongCnt": 1,
                    "totHsehCnt": 100,
                    "minSpc": "60",
                    "maxSpc": "80",
                    "dealCnt": 0,
                    "leaseCnt": 0,
                    "totalAtclCnt": 0,
                }
            ],
        },
    ]
    crawler.page = mock_page

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {
            "leftLon": 127.05,
            "rightLon": 127.07,
            "topLat": 37.52,
            "bottomLat": 37.50,
        },
    }

    with patch("time.sleep"):  # 테스트 속도를 위해 sleep mock
        results = crawler._fetch_with_retry(dong)

    assert len(results) == 1
    assert mock_page.evaluate.call_count == 3


def test_fetch_with_retry_records_failure_after_max_retries(
    crawler_config: CrawlerConfig,
) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    mock_page = Mock()
    mock_page.evaluate.side_effect = TimeoutError("Always timeout")
    crawler.page = mock_page

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {
            "leftLon": 127.05,
            "rightLon": 127.07,
            "topLat": 37.52,
            "bottomLat": 37.50,
        },
    }

    with patch("time.sleep"):
        results = crawler._fetch_with_retry(dong, max_retries=3)

    assert len(results) == 0
    assert mock_page.evaluate.call_count == 3
    assert len(crawler.checkpoint_manager.checkpoint["failed_dongs"]) == 1


def test_crawl_iterates_through_all_dongs(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock Playwright context
    mock_browser = Mock()
    mock_page = Mock()
    mock_page.evaluate.return_value = {
        "totalCount": 1,
        "result": [
            {
                "hscpNo": "123",
                "hscpNm": "단지1",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "202001",
                "totDongCnt": 1,
                "totHsehCnt": 100,
                "minSpc": "60",
                "maxSpc": "80",
                "dealCnt": 0,
                "leaseCnt": 0,
                "totalAtclCnt": 0,
            }
        ],
    }

    with patch("crawler.crawlers.naver.sync_playwright") as mock_playwright:
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
            mock_browser
        )
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        with patch("time.sleep"):  # 테스트 속도 향상
            results = crawler.crawl()

    # 실제 seoul_districts.json에는 467개 동이 있으므로 467개 동 처리 예상
    assert results["dongs_processed"] == 467
    # 각 동에 대해 최소 1번 이상의 API 호출이 있어야 함
    assert mock_page.evaluate.call_count >= 467


def test_crawl_with_district_filter(crawler_config: CrawlerConfig) -> None:
    """crawl() 메서드가 district_filter 파라미터로 특정 구만 필터링하여 처리하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # 강남구와 서초구만 필터링
    district_filter = ["강남구", "서초구"]

    # filter_districts 메서드를 직접 테스트하여 필터링 기능 확인
    filtered_districts = crawler.filter_districts(district_filter)

    # 필터링된 구 이름 확인
    filtered_district_names = [d["district_name"] for d in filtered_districts]
    assert "강남구" in filtered_district_names
    assert "서초구" in filtered_district_names
    assert len(filtered_districts) == 2

    # 전체 구가 아닌 필터링된 구만 포함되는지 확인
    assert len(filtered_districts) < len(crawler.districts_data["districts"])

    # Mock Playwright context (CrawlCoordinator 동작을 간단화하기 위해 mock)
    with patch("crawler.crawlers.naver.CrawlCoordinator") as mock_coordinator_class:
        mock_coordinator = Mock()
        mock_coordinator.crawl_multiple_dongs.return_value = {
            "dongs_processed": 24,  # 강남구(18) + 서초구(6) 동 수
            "total_complexes_processed": 0,
            "total_transactions_collected": 0,
            "duration_seconds": 0.1,
        }

        # Mock checkpoint_manager 설정
        mock_checkpoint_manager = Mock()
        mock_checkpoint_manager.checkpoint = {}  # 빈 checkpoint 딕셔너리
        mock_checkpoint_manager.should_skip_dong.return_value = False  # 모든 동을 처리하도록 설정
        mock_coordinator.checkpoint_manager = mock_checkpoint_manager

        mock_coordinator_class.return_value = mock_coordinator

        with patch("crawler.crawlers.naver.sync_playwright") as mock_playwright:
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.evaluate.return_value = {
                "result": [{"hscpNo": "123", "hscpNm": "단지1"}],
            }
            mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_page.return_value = mock_page
            mock_page.goto.return_value = None
            mock_page.wait_for_load_state.return_value = None

            with patch("time.sleep"):  # 테스트 속도 향상
                # district_filter 파라미터와 함께 호출
                results = crawler.crawl(district_filter=district_filter)

                # CrawlCoordinator가 필터링된 동들로 호출되었는지 확인
                mock_coordinator.crawl_multiple_dongs.assert_called_once()

                # 전달된 dong_complexes 확인
                call_args = mock_coordinator.crawl_multiple_dongs.call_args
                dong_complexes = call_args[1]["dong_complexes"]  # kwargs에서 dong_complexes 추출

                # 총 동 개수 확인 (강남구 18개 + 서초구 6개 = 24개)
                assert len(dong_complexes) == 24

                # 각 동이 필터링된 구에 속하는지 확인
                dong_districts = set()
                for dong_complex in dong_complexes:
                    # 각 동이 어느 구에 속하는지 확인
                    for district in filtered_districts:
                        district_dongs = {d["cortarNo"] for d in district["dongs"]}
                        if dong_complex["dong_code"] in district_dongs:
                            dong_districts.add(district["district_name"])
                            break

                # 오직 강남구와 서초구만 포함되어야 함
                assert dong_districts == {"강남구", "서초구"}

                # 최종 결과 확인
                assert results["dongs_processed"] == 24


def test_fetch_complex_listings_calls_api_correctly(crawler_config: CrawlerConfig) -> None:
    """fetch_complex_listings가 올바른 API URL과 파라미터로 호출하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None

    # Mock API 응답
    mock_response = {
        "result": [
            {
                "atclNo": "12345",
                "hscpNo": "112581",
                "hscpNm": "헬리오시티",
                "tradTpCd": "A1",
                "tradTpNm": "매매",
                "flrInfo": "15/25",
                "spc1": "84",
                "spc2": "113",
                "prcInfo": "12억 3,000",
                "direction": "남향",
                "roomCnt": "3",
                "bathCnt": "2",
                "heatTpNm": "중앙난방",
                "mvInDt": "즉시입주",
                "tagList": "[풀옵션,역세권]",
            }
        ]
    }
    mock_page.evaluate.return_value = mock_response
    crawler.page = mock_page

    # 테스트 실행
    listings = crawler.fetch_complex_listings("112581", "A1")

    # 결과 검증
    assert len(listings) == 1
    assert listings[0]["article_id"] == "12345"
    assert listings[0]["complex_id"] == "112581"
    assert listings[0]["complex_name"] == "헬리오시티"
    assert listings[0]["trade_type"] == "A1"
    assert listings[0]["floor"] == "15/25"
    assert listings[0]["area"] == "84"

    # API 호출 확인
    mock_page.evaluate.assert_called()
    call_args = mock_page.evaluate.call_args[0][1]  # 첫 번째 인자의 URL
    assert "complexNo=112581" in call_args
    assert "tradTpCd=A1" in call_args
    assert "page=1" in call_args


def test_fetch_complex_listings_handles_pagination(crawler_config: CrawlerConfig) -> None:
    """fetch_complex_listings가 페이지네이션을 올바르게 처리하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None

    # 페이지별 Mock API 응답
    def create_mock_listing(atcl_no):
        return {
            "atclNo": str(atcl_no),
            "hscpNo": "112581",
            "hscpNm": "헬리오시티",
            "tradTpCd": "A1",
            "tradTpNm": "매매",
            "flrInfo": f"{atcl_no}/25",
            "spc1": "84",
            "spc2": "113",
            "prcInfo": f"{atcl_no}억",
            "direction": "남향",
            "roomCnt": "3",
            "bathCnt": "2",
            "heatTpNm": "중앙난방",
            "mvInDt": "즉시입주",
            "tagList": "[풀옵션]",
            "atclUrl": f"https://m.land.naver.com/article/{atcl_no}",
            "imgCnt": 5,
            "manageCost": "15만",
            "manageCostIncld": "[수도권]",
            "prk": "1,352세대",
            "elv": "[전기]있음",
            "newHouse": "N",
            "directDeal": "N",
            "rltrNm": "공인중개사",
            "telNo": "02-1234-5678",
            "certYn": "Y",
            "atclYmd": "2024.01.15",
            "atclMdfYmd": "2024.01.20",
            "readCnt": 150,
            "intrCnt": 10,
            "cntnYn": "N",
            "cntnPrc": "",
            "cntnRentPrc": "",
            "rentFee": "",
            "deposit": "",
            "shortRentYn": "N",
            "spcPrv": "특약사항 없음",
        }

    first_page_response = {
        "result": [create_mock_listing(i) for i in range(1, 21)]  # 1-20
    }
    second_page_response = {
        "result": [create_mock_listing(i) for i in range(21, 41)]  # 21-40 (20개)
    }
    third_page_response = {"result": []}  # 빈 응답

    mock_page.evaluate.side_effect = [
        first_page_response,
        second_page_response,
        third_page_response,
    ]
    crawler.page = mock_page

    with patch("time.sleep"):  # 테스트 속도 향상
        listings = crawler.fetch_complex_listings("112581", "A1")

    # 결과 검증
    assert len(listings) == 40
    assert listings[0]["article_id"] == "1"
    assert listings[1]["article_id"] == "2"
    assert listings[19]["article_id"] == "20"
    assert listings[20]["article_id"] == "21"
    assert listings[39]["article_id"] == "40"

    # API 호출 확인 (3페이지 호출)
    assert mock_page.evaluate.call_count == 3


def test_fetch_complex_listings_handles_empty_response(crawler_config: CrawlerConfig) -> None:
    """fetch_complex_listings가 빈 응답을 올바르게 처리하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}
    crawler.page = mock_page

    # 테스트 실행
    listings = crawler.fetch_complex_listings("112581", "A1")

    # 결과 검증
    assert len(listings) == 0
    mock_page.evaluate.assert_called_once()


def test_fetch_complex_listings_handles_api_error(crawler_config: CrawlerConfig) -> None:
    """fetch_complex_listings가 API 에러를 올바르게 처리하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.side_effect = Exception("API Error")
    crawler.page = mock_page

    # 테스트 실행
    with patch("time.sleep"):
        listings = crawler.fetch_complex_listings("112581", "A1")

    # 결과 검증 (에러 시 빈 리스트 반환)
    assert len(listings) == 0


def test_parse_complex_listings_extracts_all_fields(crawler_config: CrawlerConfig) -> None:
    """_parse_complex_listings가 모든 필드를 올바르게 추출하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # 테스트 데이터
    response = {
        "result": [
            {
                "atclNo": "12345",
                "hscpNo": "112581",
                "hscpNm": "헬리오시티",
                "tradTpCd": "A1",
                "tradTpNm": "매매",
                "flrInfo": "15/25",
                "spc1": "84",
                "spc2": "113",
                "prcInfo": "12억 3,000",
                "prcDesc": "매매가",
                "direction": "남향",
                "roomCnt": "3",
                "bathCnt": "2",
                "heatTpNm": "중앙난방",
                "mvInDt": "즉시입주",
                "tagList": "[풀옵션,역세권]",
                "atclUrl": "https://m.land.naver.com/article/12345",
                "imgCnt": 5,
                "manageCost": "15만",
                "manageCostIncld": "[수도권,도시가사]비용 5만원별도",
                "prk": "1,352세대",
                "elv": "[전기]있음",
                "newHouse": "N",
                "directDeal": "N",
                "rltrNm": "공인중개사",
                "telNo": "02-1234-5678",
                "certYn": "Y",
                "atclYmd": "2024.01.15",
                "atclMdfYmd": "2024.01.20",
                "readCnt": 150,
                "intrCnt": 10,
                "cntnYn": "N",
                "cntnPrc": "",
                "cntnRentPrc": "",
                "rentFee": "",
                "deposit": "",
                "shortRentYn": "N",
                "spcPrv": "특약사항 없음",
            }
        ]
    }

    # 테스트 실행
    listings = crawler._parse_complex_listings(response)

    # 결과 검증
    assert len(listings) == 1
    listing = listings[0]

    # 주요 필드 확인
    assert listing["article_id"] == "12345"
    assert listing["complex_id"] == "112581"
    assert listing["complex_name"] == "헬리오시티"
    assert listing["trade_type"] == "A1"
    assert listing["trade_type_name"] == "매매"
    assert listing["floor"] == "15/25"
    assert listing["area"] == "84"
    assert listing["supply_area"] == "113"
    assert listing["price"] == "12억 3,000"
    assert listing["direction"] == "남향"
    assert listing["room_type"] == "3"
    assert listing["bathroom_count"] == "2"
    assert listing["heating_type"] == "중앙난방"
    assert listing["move_in_date"] == "즉시입주"
    assert listing["description"] == "[풀옵션,역세권]"
    assert listing["article_url"] == "https://m.land.naver.com/article/12345"
    assert listing["image_count"] == 5
    assert listing["manage_cost"] == "15만"
    assert listing["manage_cost_include"] == "[수도권,도시가사]비용 5만원별도"
    assert listing["parking"] == "1,352세대"
    assert listing["elevator"] == "[전기]있음"
    assert listing["is_new_building"] == "N"
    assert listing["is_direct_deal"] == "N"
    assert listing["real_estate_agent"] == "공인중개사"
    assert listing["real_estate_phone"] == "02-1234-5678"
    assert listing["service_report"] == "Y"
    assert listing["article_date"] == "2024.01.15"
    assert listing["article_modify_date"] == "2024.01.20"
    assert listing["view_count"] == 150
    assert listing["interest_count"] == 10
    assert listing["is_contract_renewal"] == "N"
    assert listing["short_term_rental_available"] == "N"
    assert listing["special_provision"] == "특약사항 없음"


# Tests for fetch_transaction_history method


def test_fetch_transaction_history_single_page(crawler_config: CrawlerConfig) -> None:
    """단일 페이지 거래내역 조회 테스트"""
    from pathlib import Path

    crawler = NaverRealEstateCrawler(crawler_config)

    # Load test fixture for last page (hasNextPage: false)
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"
    )
    with open(fixture_path) as f:
        mock_response = json.load(f)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = mock_response

    crawler.page = mock_page

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, "wait"):
        with patch.object(crawler.rate_limiter, "on_success"):
            # Call the method
            transactions = crawler.fetch_transaction_history(
                complex_id="111515", pyeong_type_number=1, trade_type="A1"
            )

    # Verify results - should only have 1 transaction from the last page fixture
    assert len(transactions) == 1
    assert transactions[0]["trade_date"] == "2023-12-01"
    assert transactions[0]["deal_price"] == 1550000000

    # Verify API call
    expected_url_contains = [
        "complexNumber=111515",
        "pyeongTypeNumber=1",
        "tradeType=A1",
        "page=1",
        "size=20",
    ]
    call_args = mock_page.evaluate.call_args[0][1]
    for expected_part in expected_url_contains:
        assert expected_part in call_args


def test_fetch_transaction_history_pagination(crawler_config: CrawlerConfig) -> None:
    """페이지네이션 처리 테스트"""
    from pathlib import Path

    crawler = NaverRealEstateCrawler(crawler_config)

    # Load test fixtures
    first_page_fixture = (
        Path(__file__).parent.parent / "fixtures" / "naver_transaction_response.json"
    )
    last_page_fixture = (
        Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"
    )

    with open(first_page_fixture) as f:
        first_page_response = json.load(f)
    with open(last_page_fixture) as f:
        last_page_response = json.load(f)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    # First call returns hasNextPage=true, second call returns hasNextPage=false
    mock_page.evaluate.side_effect = [first_page_response, last_page_response]

    crawler.page = mock_page

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, "wait"):
        with patch.object(crawler.rate_limiter, "on_success"):
            # Call the method
            transactions = crawler.fetch_transaction_history(
                complex_id="111515", pyeong_type_number=1, trade_type="A1"
            )

    # Verify results from both pages
    assert len(transactions) == 5  # 4 from first page + 1 from last page
    assert mock_page.evaluate.call_count == 2

    # Verify the correct transactions were retrieved
    assert transactions[0]["trade_date"] == "2025-11-14"  # From first page
    assert transactions[4]["trade_date"] == "2023-12-01"  # From second page

    # Verify second page call
    second_call_args = mock_page.evaluate.call_args_list[1][0][1]
    assert "page=2" in second_call_args


def test_fetch_transaction_history_rate_limit_error(crawler_config: CrawlerConfig) -> None:
    """Rate limit 에러 처리 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    # First call throws 429 error, second call succeeds
    mock_page.evaluate.side_effect = [
        Exception("HTTP 429: Too Many Requests"),
        {"isSuccess": True, "result": {"list": [], "hasNextPage": False}},
    ]

    crawler.page = mock_page

    # Mock rate limiter and sleep
    with patch.object(crawler.rate_limiter, "wait"):
        with patch.object(crawler.rate_limiter, "on_success"):
            with patch.object(crawler.rate_limiter, "on_rate_limit_error") as mock_429:
                with patch("time.sleep") as mock_sleep:
                    # Call the method
                    transactions = crawler.fetch_transaction_history(
                        complex_id="111515", pyeong_type_number=1, trade_type="A1"
                    )

    # Verify rate limiter was called on error
    mock_429.assert_called_once()
    mock_sleep.assert_called()  # Should sleep for retry delay
    assert len(transactions) == 0  # Empty result from successful retry


def test_parse_transaction_normalizes_data(crawler_config: CrawlerConfig) -> None:
    """거래내역 데이터 정규화 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Test data
    raw_transaction = {
        "tradeDate": "2025-11-14",
        "tradeYear": "2025",
        "floor": 21,
        "dealPrice": 1700000000,
        "deposit": 0,
        "monthlyRent": 0,
        "isDelete": False,
        "tradeCategory": "중개거래",
        "propertyType": "NORMAL",
        "isRenew": False,
    }

    # Call parse method
    parsed = crawler._parse_transaction(
        raw_transaction=raw_transaction,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="A1",
    )

    # Verify normalized data
    assert parsed["complex_id"] == "111515"
    assert parsed["complex_name"] == "헬리오시티"
    assert parsed["pyeong_type_number"] == 1
    assert parsed["pyeong_name"] == "84A"
    assert parsed["trade_type"] == "A1"
    assert parsed["trade_type_name"] == "매매"
    assert parsed["trade_date"] == "2025-11-14"
    assert parsed["trade_year"] == "2025"
    assert parsed["floor"] == 21
    assert parsed["deal_price"] == 1700000000
    assert parsed["deposit"] == 0
    assert parsed["monthly_rent"] == 0
    assert parsed["trade_category"] == "중개거래"
    assert parsed["is_delete"] is False
    assert parsed["is_renew"] is False


def test_parse_transaction_jeonse_wolse(crawler_config: CrawlerConfig) -> None:
    """전세/월세 거래내역 정규화 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Test 전세
    jeonse_raw = {
        "tradeDate": "2025-10-20",
        "tradeYear": "2025",
        "floor": 15,
        "dealPrice": 0,
        "deposit": 800000000,
        "monthlyRent": 0,
        "isDelete": False,
        "tradeCategory": "중개거래",
        "isRenew": False,
    }

    parsed = crawler._parse_transaction(
        raw_transaction=jeonse_raw,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="B1",
    )

    assert parsed["trade_type_name"] == "전세"
    assert parsed["deposit"] == 800000000
    assert parsed["monthly_rent"] == 0

    # Test 월세
    wolse_raw = {
        "tradeDate": "2025-09-10",
        "tradeYear": "2025",
        "floor": 12,
        "dealPrice": 0,
        "deposit": 100000000,
        "monthlyRent": 2000000,
        "isDelete": False,
        "tradeCategory": "중개거래",
        "isRenew": False,
    }

    parsed = crawler._parse_transaction(
        raw_transaction=wolse_raw,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="B2",
    )

    assert parsed["trade_type_name"] == "월세"
    assert parsed["deposit"] == 100000000
    assert parsed["monthly_rent"] == 2000000


def test_fetch_transaction_history_all_trade_types(crawler_config: CrawlerConfig) -> None:
    """모든 거래 유형(매매/전세/월세) 조회 테스트"""
    from pathlib import Path

    crawler = NaverRealEstateCrawler(crawler_config)

    # Load test fixture for last page (hasNextPage: false)
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"
    )
    with open(fixture_path) as f:
        mock_response = json.load(f)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = mock_response

    crawler.page = mock_page

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, "wait"):
        with patch.object(crawler.rate_limiter, "on_success"):
            # Test all trade types
            for trade_type in ["A1", "B1", "B2"]:
                transactions = crawler.fetch_transaction_history(
                    complex_id="111515", pyeong_type_number=1, trade_type=trade_type
                )

                # Should get some transactions
                assert isinstance(transactions, list)
                assert len(transactions) == 1  # From the last page fixture

                # Verify correct trade type in URL
                call_args = mock_page.evaluate.call_args[0][1]
                assert f"tradeType={trade_type}" in call_args


# Tests for filter_districts method


def test_filter_districts_none_returns_all(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """district_names이 None이면 전체 구를 반환하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with None
    result = crawler.filter_districts(None)

    # Should return all districts
    assert len(result) == 3
    assert result[0]["district_name"] == "종로구"
    assert result[1]["district_name"] == "중구"
    assert result[2]["district_name"] == "용산구"


def test_filter_districts_valid_single_district(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """유효한 단일 구 필터링 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with single district
    result = crawler.filter_districts(["중구"])

    # Should return only 중구
    assert len(result) == 1
    assert result[0]["district_name"] == "중구"
    assert result[0]["district_code"] == "11140"


def test_filter_districts_valid_multiple_districts(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """유효한 여러 구 필터링 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with multiple districts
    result = crawler.filter_districts(["종로구", "용산구"])

    # Should return only 종로구 and 용산구 (order preserved)
    assert len(result) == 2
    assert result[0]["district_name"] == "종로구"
    assert result[1]["district_name"] == "용산구"


def test_filter_districts_invalid_district_raises_error(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """유효하지 않은 구 이름으로 ValueError 발생 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with invalid district
    with pytest.raises(ValueError) as exc_info:
        crawler.filter_districts(["강남구"])  # Not in sample data

    # Verify error message
    error_msg = str(exc_info.value)
    assert "유효하지 않은 구 이름: 강남구" in error_msg
    assert "사용 가능한 구:" in error_msg
    assert "종로구" in error_msg
    assert "중구" in error_msg
    assert "용산구" in error_msg


def test_filter_districts_mixed_valid_invalid(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """유효한 구와 유효하지 않은 구가 섞여있을 때 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with mix of valid and invalid districts
    with pytest.raises(ValueError) as exc_info:
        crawler.filter_districts(["종로구", "강남구", "서초구"])

    # Verify error message includes all invalid districts
    error_msg = str(exc_info.value)
    assert "유효하지 않은 구 이름: 강남구, 서초구" in error_msg
    assert "사용 가능한 구:" in error_msg


def test_filter_districts_empty_list_returns_empty(
    crawler_config: CrawlerConfig, sample_districts_data: dict[str, Any]
) -> None:
    """빈 리스트 전달 시 빈 리스트 반환 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock districts data
    crawler.districts_data = sample_districts_data

    # Call with empty list
    result = crawler.filter_districts([])

    # Should return empty list
    assert len(result) == 0
    assert result == []


# Tests for fetch_complex_list method


def test_fetch_complex_list_calls_api_with_correct_parameters(
    crawler_config: CrawlerConfig,
) -> None:
    """fetch_complex_list가 올바른 API URL과 파라미터로 호출하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None

    # Mock API 응답
    mock_response = {
        "result": [
            {
                "complexNo": "1111010300001",
                "complexName": "테스트단지",
                "address": "서울 종로구 사직동",
                "lat": 37.5789,
                "lng": 126.9770,
                "hscpCnt": 100,
                "buildYear": "2000",
            }
        ]
    }
    mock_page.evaluate.return_value = mock_response

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # 테스트 파라미터
    cortar_no = "1111010300"  # 사직동 코드
    bounds = {"leftLon": 126.97, "rightLon": 126.99, "topLat": 37.58, "bottomLat": 37.56}

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, "wait"):
        # 메서드 호출
        complexes = crawler.fetch_complex_list(cortar_no, json.dumps(bounds))

    # 결과 검증
    assert len(complexes) == 1
    assert complexes[0]["complexNo"] == "1111010300001"
    assert complexes[0]["complexName"] == "테스트단지"

    # API 호출 파라미터 검증
    mock_page.evaluate.assert_called_once()
    call_args = mock_page.evaluate.call_args[0][1]  # URL 인자

    # URL에 필요한 파라미터들이 모두 포함되어 있는지 확인
    assert "cortarNo=1111010300" in call_args
    assert "rletTpCd=APT" in call_args
    assert "tradTpCd=A1" in call_args
    assert "z=17" in call_args
    assert "lat=37.57" in call_args  # 중심 위도
    assert "lon=126.98" in call_args  # 중심 경도
    assert "btm=37.56" in call_args
    assert "lft=126.97" in call_args
    assert "top=37.58" in call_args
    assert "rgt=126.99" in call_args


def test_fetch_complex_list_handles_missing_bounds(crawler_config: CrawlerConfig) -> None:
    """bounds가 없을 때 기본값을 사용하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # bounds 없이 호출
    with patch.object(crawler.rate_limiter, "wait"):
        crawler.fetch_complex_list("1111010300", None)

    # 기본 bounds 값이 사용되는지 확인
    mock_page.evaluate.assert_called_once()
    call_args = mock_page.evaluate.call_args[0][1]

    # 기본 bounds 값 (노량진동)
    assert "btm=37.5086" in call_args
    assert "lft=126.9422" in call_args
    assert "top=37.5160" in call_args
    assert "rgt=126.9541" in call_args


def test_fetch_complex_list_handles_invalid_bounds_json(crawler_config: CrawlerConfig) -> None:
    """bounds JSON 파싱 오류 시 기본값을 사용하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # 잘못된 JSON 형식의 bounds 전달
    with patch.object(crawler.rate_limiter, "wait"):
        crawler.fetch_complex_list("1111010300", "invalid_json")

    # 기본 bounds 값이 사용되는지 확인
    mock_page.evaluate.assert_called_once()
    call_args = mock_page.evaluate.call_args[0][1]

    # 기본 bounds 값 확인
    assert "btm=37.5086" in call_args
    assert "lft=126.9422" in call_args


def test_fetch_complex_list_alternative_bounds_format(crawler_config: CrawlerConfig) -> None:
    """min/max lng/lat 형식의 bounds를 처리하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # min/max 형식의 bounds
    bounds = {"min_lng": 126.97, "max_lng": 126.99, "min_lat": 37.56, "max_lat": 37.58}

    with patch.object(crawler.rate_limiter, "wait"):
        crawler.fetch_complex_list("1111010300", bounds)

    # 좌표 변환이 올바르게 되었는지 확인
    mock_page.evaluate.assert_called_once()
    call_args = mock_page.evaluate.call_args[0][1]

    # 변환된 좌표 확인
    assert "lft=126.97" in call_args
    assert "rgt=126.99" in call_args
    assert "btm=37.56" in call_args
    assert "top=37.58" in call_args


def test_fetch_complex_list_handles_api_error(crawler_config: CrawlerConfig) -> None:
    """API 에러 발생 시 빈 리스트를 반환하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"error": "HTTP 429: Too Many Requests"}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    with patch.object(crawler.rate_limiter, "wait"):
        complexes = crawler.fetch_complex_list("1111010300", None)

    # 에러 시 빈 리스트 반환
    assert len(complexes) == 0


def test_fetch_complex_list_returns_sample_data_when_no_data(crawler_config: CrawlerConfig) -> None:
    """API에서 데이터를 반환하지 않을 때 샘플 데이터를 반환하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = {"result": []}  # 빈 결과

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    with patch.object(crawler.rate_limiter, "wait"):
        complexes = crawler.fetch_complex_list("1111010300", None)

    # 샘플 데이터 반환 확인
    assert len(complexes) == 1
    assert complexes[0]["complexNo"] == "1111010300001"
    assert complexes[0]["complexName"] == "노량진테스트아파트"


def test_parse_complex_list_api(crawler_config: CrawlerConfig) -> None:
    """_parse_complex_list_api가 응답을 올바르게 파싱하는지 테스트"""
    crawler = NaverRealEstateCrawler(crawler_config)

    # 테스트 응답 데이터
    response = {
        "result": [
            {
                "hscpNo": "12345",
                "hscpNm": "테스트아파트",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "202001",
                "totDongCnt": 2,
                "totHsehCnt": 200,
                "minSpc": "59.99",
                "maxSpc": "84.99",
                "dealCnt": 5,
                "leaseCnt": 3,
                "rentCnt": 2,
                "dealPrcMin": "<em class='txt_unit'>5억</em>",
                "dealPrcMax": "<em class='txt_unit'>10억</em>",
                "leasePrcMin": "<em class='txt_unit'>3억</em>",
                "leasePrcMax": "<em class='txt_unit'>6억</em>",
            }
        ]
    }

    # 파싱 실행
    complexes = crawler._parse_complex_list_api(response)

    # 결과 검증
    assert len(complexes) == 1
    complex = complexes[0]

    assert complex["complex_id"] == "12345"
    assert complex["complex_name"] == "테스트아파트"
    assert complex["real_estate_type"] == "아파트"
    assert complex["completion_year_month"] == "202001"
    assert complex["total_dong_count"] == 2
    assert complex["total_household_count"] == 200
    assert complex["min_area"] == "59.99"
    assert complex["max_area"] == "84.99"
    assert complex["deal_count"] == 5
    assert complex["lease_count"] == 3
    assert complex["rent_count"] == 2

    # HTML 태그 제거 확인
    assert complex["deal_price_min"] == "5억"
    assert complex["deal_price_max"] == "10억"
    assert complex["lease_price_min"] == "3억"
    assert complex["lease_price_max"] == "6억"

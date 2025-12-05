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
    results = crawler._parse_api_response(sample_api_response)

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
    results = crawler._parse_api_response({"totalCount": 0, "list": []})

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

    # 실제 seoul_districts.json에는 467개 동이 있으므로 467개 단지 크롤링 예상
    assert len(results) == 467
    assert mock_page.evaluate.call_count == 467


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
                "tagList": "[풀옵션,역세권]"
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
            "spcPrv": "특약사항 없음"
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
        third_page_response
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
                "spcPrv": "특약사항 없음"
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
    fixture_path = Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"
    with open(fixture_path) as f:
        mock_response = json.load(f)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = mock_response

    crawler.page = mock_page

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, 'wait'):
        with patch.object(crawler.rate_limiter, 'on_success'):
            # Call the method
            transactions = crawler.fetch_transaction_history(
                complex_id="111515",
                pyeong_type_number=1,
                trade_type="A1"
            )

    # Verify results - should only have 1 transaction from the last page fixture
    assert len(transactions) == 1
    assert transactions[0]["tradeDate"] == "2023-12-01"
    assert transactions[0]["dealPrice"] == 1550000000

    # Verify API call
    expected_url_contains = [
        "complexNumber=111515",
        "pyeongTypeNumber=1",
        "tradeType=A1",
        "page=1",
        "size=20"
    ]
    call_args = mock_page.evaluate.call_args[0][1]
    for expected_part in expected_url_contains:
        assert expected_part in call_args


def test_fetch_transaction_history_pagination(crawler_config: CrawlerConfig) -> None:
    """페이지네이션 처리 테스트"""
    from pathlib import Path

    crawler = NaverRealEstateCrawler(crawler_config)

    # Load test fixtures
    first_page_fixture = Path(__file__).parent.parent / "fixtures" / "naver_transaction_response.json"
    last_page_fixture = Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"

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
    with patch.object(crawler.rate_limiter, 'wait'):
        with patch.object(crawler.rate_limiter, 'on_success'):
            # Call the method
            transactions = crawler.fetch_transaction_history(
                complex_id="111515",
                pyeong_type_number=1,
                trade_type="A1"
            )

    # Verify results from both pages
    assert len(transactions) == 5  # 4 from first page + 1 from last page
    assert mock_page.evaluate.call_count == 2

    # Verify the correct transactions were retrieved
    assert transactions[0]["tradeDate"] == "2025-11-14"  # From first page
    assert transactions[4]["tradeDate"] == "2023-12-01"  # From second page

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
        {"isSuccess": True, "result": {"list": [], "hasNextPage": False}}
    ]

    crawler.page = mock_page

    # Mock rate limiter and sleep
    with patch.object(crawler.rate_limiter, 'wait') as mock_wait:
        with patch.object(crawler.rate_limiter, 'on_success') as mock_success:
            with patch.object(crawler.rate_limiter, 'on_rate_limit_error') as mock_429:
                with patch('time.sleep') as mock_sleep:
                    # Call the method
                    transactions = crawler.fetch_transaction_history(
                        complex_id="111515",
                        pyeong_type_number=1,
                        trade_type="A1"
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
        "isRenew": False
    }

    # Call parse method
    parsed = crawler._parse_transaction(
        raw_transaction=raw_transaction,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="A1"
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
        "isRenew": False
    }

    parsed = crawler._parse_transaction(
        raw_transaction=jeonse_raw,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="B1"
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
        "isRenew": False
    }

    parsed = crawler._parse_transaction(
        raw_transaction=wolse_raw,
        complex_id="111515",
        complex_name="헬리오시티",
        pyeong_type_number=1,
        pyeong_name="84A",
        trade_type="B2"
    )

    assert parsed["trade_type_name"] == "월세"
    assert parsed["deposit"] == 100000000
    assert parsed["monthly_rent"] == 2000000


def test_fetch_transaction_history_all_trade_types(crawler_config: CrawlerConfig) -> None:
    """모든 거래 유형(매매/전세/월세) 조회 테스트"""
    from pathlib import Path

    crawler = NaverRealEstateCrawler(crawler_config)

    # Load test fixture for last page (hasNextPage: false)
    fixture_path = Path(__file__).parent.parent / "fixtures" / "naver_transaction_response_last_page.json"
    with open(fixture_path) as f:
        mock_response = json.load(f)

    # Mock page
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.evaluate.return_value = mock_response

    crawler.page = mock_page

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, 'wait'):
        with patch.object(crawler.rate_limiter, 'on_success'):
            # Test all trade types
            for trade_type in ["A1", "B1", "B2"]:
                transactions = crawler.fetch_transaction_history(
                    complex_id="111515",
                    pyeong_type_number=1,
                    trade_type=trade_type
                )

                # Should get some transactions
                assert isinstance(transactions, list)
                assert len(transactions) == 1  # From the last page fixture

                # Verify correct trade type in URL
                call_args = mock_page.evaluate.call_args[0][1]
                assert f"tradeType={trade_type}" in call_args

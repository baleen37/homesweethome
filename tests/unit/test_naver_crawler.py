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
    assert results[0]["marker_id"] == "149239"
    assert results[0]["latitude"] == 37.458919
    assert results[0]["longitude"] == 126.898166
    assert results[0]["real_estate_type"] == "아파트"
    assert results[0]["completion_year_month"] == "202403"
    assert results[0]["total_dong_count"] == 1
    assert results[0]["total_household_count"] == 151
    assert results[0]["floor_area_ratio"] == 499
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
        "list": [
            {
                "markerId": "123",
                "complexName": "테스트단지",
                "latitude": 37.5,
                "longitude": 127.0,
                "realEstateTypeName": "아파트",
                "completionYearMonth": "202001",
                "totalDongCount": 1,
                "totalHouseholdCount": 100,
                "floorAreaRatio": 200,
                "minArea": "60",
                "maxArea": "80",
                "dealCount": 0,
                "leaseCount": 0,
                "totalArticleCount": 0,
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
            "list": [
                {
                    "markerId": "123",
                    "complexName": "성공",
                    "latitude": 37.5,
                    "longitude": 127.0,
                    "realEstateTypeName": "아파트",
                    "completionYearMonth": "202001",
                    "totalDongCount": 1,
                    "totalHouseholdCount": 100,
                    "floorAreaRatio": 200,
                    "minArea": "60",
                    "maxArea": "80",
                    "dealCount": 0,
                    "leaseCount": 0,
                    "totalArticleCount": 0,
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
        "list": [
            {
                "markerId": "123",
                "complexName": "단지1",
                "latitude": 37.5,
                "longitude": 127.0,
                "realEstateTypeName": "아파트",
                "completionYearMonth": "202001",
                "totalDongCount": 1,
                "totalHouseholdCount": 100,
                "floorAreaRatio": 200,
                "minArea": "60",
                "maxArea": "80",
                "dealCount": 0,
                "leaseCount": 0,
                "totalArticleCount": 0,
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

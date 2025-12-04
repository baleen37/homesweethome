import json
from pathlib import Path
from typing import Any

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

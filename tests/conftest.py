# pytest 공통 fixture 및 설정

import pytest
from pathlib import Path
from crawler.config import CrawlerConfig
from typing import Any, Dict


def pytest_addoption(parser):
    """pytest 커맨드 라인 옵션 추가"""
    parser.addoption("--run-slow", action="store_true", default=False, help="run slow tests")
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests with real API calls",
    )


def pytest_configure(config):
    """pytest 설정 초기화"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


def pytest_collection_modifyitems(config, items):
    """테스트 컬렉션 수정"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def test_config(tmp_path: Path) -> CrawlerConfig:
    """테스트용 CrawlerConfig fixture"""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return CrawlerConfig(headless=True, timeout=30, output_dir=str(output_dir))


@pytest.fixture
def sample_districts_data() -> dict[str, Any]:
    """테스트용 서울시 구 데이터"""
    return {
        "districts": [
            {"district_code": "1168000000", "district_name": "강남구"},
            {"district_code": "1174000000", "district_name": "강동구"},
            {"district_code": "1130500000", "district_name": "강북구"},
            {"district_code": "1150000000", "district_name": "강서구"},
            {"district_code": "1165000000", "district_name": "관악구"},
            {"district_code": "1121500000", "district_name": "광진구"},
            {"district_code": "1154500000", "district_name": "구로구"},
            {"district_code": "1153000000", "district_name": "금천구"},
            {"district_code": "1135000000", "district_name": "노원구"},
            {"district_code": "1132000000", "district_name": "도봉구"},
            {"district_code": "1156000000", "district_name": "동대문구"},
            {"district_code": "1159000000", "district_name": "동작구"},
            {"district_code": "1144000000", "district_name": "마포구"},
            {"district_code": "1147000000", "district_name": "서대문구"},
            {"district_code": "1162000000", "district_name": "서초구"},
            {"district_code": "1120000000", "district_name": "성동구"},
            {"district_code": "1126000000", "district_name": "성북구"},
            {"district_code": "1171000000", "district_name": "송파구"},
            {"district_code": "1141000000", "district_name": "양천구"},
            {"district_code": "1151500000", "district_name": "영등포구"},
            {"district_code": "1111000000", "district_name": "용산구"},
            {"district_code": "1117000000", "district_name": "은평구"},
            {"district_code": "1114000000", "district_name": "종로구"},
            {"district_code": "1116500000", "district_name": "중구"},
            {"district_code": "1172000000", "district_name": "중랑구"},
        ]
    }


@pytest.fixture
def naver_config() -> Dict[str, str]:
    """네이버 부동산 API 테스트용 설정 fixture"""
    return {
        "base_url": "https://m.land.naver.com",
        "sample_cortar_no": "1168010500",  # 서울 강남구 개포동
        "sample_bounds": "37.478385,127.048329,37.513308,127.106925",  # 강남구 개포동 근처
        "default_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://m.land.naver.com/",
        },
    }

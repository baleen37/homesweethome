"""pytest 설정과 공통 fixture"""

import csv
from pathlib import Path

import pytest

from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.naver_listing import NaverAptDTO


def pytest_configure(config):
    """pytest 마커 등록"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "e2e: E2E 테스트 (실제 브라우저 필요)")
    config.addinivalue_line("markers", "slow: 느린 테스트 (연속 요청 등)")


# 서울 샘플 동 코드
SEOUL_DONG_CODES = {
    "1168010100": "역삼동",
    "1168010200": "청담동",
    "1168010300": "삼성동",
    "1150010700": "사직동",
    "1156010500": "행당동",
}


def crawl_multiple_dongs(
    dong_codes: dict[str, str] | None = None,
    max_count: int = 0,
) -> list:
    """여러 동에서 아파트 데이터 수집

    Args:
        dong_codes: 동 코드 딕셔너리 (None이면 기본 서울 동 코드 사용)
        max_count: 최대 수집 개수 (0 이하면 무제한)

    Returns:
        수집된 아파트 데이터 리스트 (dict 형태)
    """
    if dong_codes is None:
        dong_codes = SEOUL_DONG_CODES

    all_data = []
    for dong_code in dong_codes:
        if max_count > 0 and len(all_data) >= max_count:
            remaining = max_count - len(all_data)
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results = crawler.crawl()
            all_data.extend([apt.model_dump() for apt in results[:remaining]])
        else:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results = crawler.crawl()
            all_data.extend([apt.model_dump() for apt in results])

    return all_data


@pytest.fixture
def sample_dong_codes():
    """E2E 테스트용 샘플 동 코드 리스트"""
    return ["1150010100", "1150010200"]


@pytest.fixture
def apt_csv_path(tmp_path):
    """아파트 CSV 경로 fixture"""
    return tmp_path / "seoul_apt_list_e2e.csv"


@pytest.fixture
def trade_csv_path(tmp_path):
    """실거래가 CSV 경로 fixture"""
    return tmp_path / "seoul_trade_price_e2e.csv"


@pytest.fixture
def verify_csv_file():
    """CSV 파일 검증 헬퍼 함수 fixture"""

    def _verify(
        csv_path: Path,
        min_lines: int = 2,
        required_headers: list[str] | None = None,
    ):
        """CSV 파일 검증

        Args:
            csv_path: CSV 파일 경로
            min_lines: 최소 라인 수 (헤더 포함)
            required_headers: 필수 헤더 목록

        Returns:
            CSV 레코드 리스트
        """
        assert csv_path.exists(), f"CSV 파일이 생성되지 않음: {csv_path}"

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)
            assert len(records) >= min_lines - 1, f"CSV 레코드 수 부족: {len(records)}개"

            if required_headers:
                with open(csv_path, encoding="utf-8") as f2:
                    header_line = f2.readline().strip()
                    headers = header_line.split(",")
                    for required in required_headers:
                        assert required in headers, f"CSV 헤더에 '{required}' 필드 누락"

        return records

    return _verify


# =============================================================================
# ASIL-Naver 통합 테스트용 Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_asil_apts():
    """ASIL 아파트 목록 mock fixture"""
    return [
        AsilAptListDTO(
            seq="1",
            name="래미안",
            dong="1150010700",
            dongname="사직동",
            build_year="2005",
            household="100",
            lat="37.5138",
            lng="126.8826",
        ),
        AsilAptListDTO(
            seq="2",
            name="래미안 2차",
            dong="1150010700",
            dongname="사직동",
            build_year="2010",
            household="150",
            lat="37.5140",
            lng="126.8830",
        ),
    ]


@pytest.fixture
def mock_naver_search_results():
    """Naver 검색 결과 mock fixture"""
    return [
        NaverAptDTO(
            complex_no="3499",
            complex_name="래미안",
            article_count=10,
            build_year=2005,
            household_count=100,
            latitude=37.5138,
            longitude=126.8826,
            address="서울시 종로구 사직동",
            area_code="1",
        ),
        NaverAptDTO(
            complex_no="3500",
            complex_name="래미안 2차",
            article_count=5,
            build_year=2010,
            household_count=80,
            latitude=37.5140,
            longitude=126.8830,
            address="서울시 종로구 사직동",
            area_code="2",
        ),
    ]


@pytest.fixture
def mock_naver_listings():
    """Naver 매물 목록 mock fixture"""
    return [
        {
            "article_no": "12345",
            "complex_no": "3499",
            "floor": "15층",
            "area": "84.5㎡",
            "price": "15억",
        },
        {
            "article_no": "12346",
            "complex_no": "3499",
            "floor": "10층",
            "area": "84.5㎡",
            "price": "14억 5,000만",
        },
    ]

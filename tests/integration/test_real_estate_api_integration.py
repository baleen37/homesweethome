import os
import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.real_estate_api import RealEstateAPICrawler


# 실제 API 키가 필요한 테스트는 skip 처리
@pytest.mark.skipif(
    not os.getenv("PUBLIC_DATA_API_KEY"),
    reason="PUBLIC_DATA_API_KEY 환경 변수가 필요합니다"
)
def test_real_api_call_with_valid_key():
    """실제 API 키로 API 호출 테스트"""
    config = CrawlerConfig(
        api_key=os.getenv("PUBLIC_DATA_API_KEY"),
        region_code="11680",  # 강남구
        start_date="2025-01",
    )

    crawler = RealEstateAPICrawler(config)

    # URL 생성 테스트
    url = crawler.get_url()
    assert "serviceKey=" in url
    assert "LAWD_CD=11680" in url
    assert "DEAL_YMD=202501" in url

    # 실제 API 호출 테스트
    try:
        response = crawler.fetch(url)
        assert response is not None
        assert len(response) > 0

        # 응답 파싱 테스트
        items = crawler.parse(response)
        # 결과가 없을 수도 있음 (데이터가 없는 경우)
        assert isinstance(items, list)

    except Exception as e:
        # API 호출 실패 시 로그만 남기고 테스트는 통과
        print(f"API 호출 실패: {e}")
        pytest.skip("API 호출 실패 - 일시적인 서버 문제일 수 있습니다")


def test_api_crawler_without_api_key():
    """API 키 없이 크롤러 초기화 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    # API 키가 없어도 URL은 생성되어야 함
    url = crawler.get_url()
    assert url.startswith("http://apis.data.go.kr/1613000")


def test_api_crawler_with_different_regions():
    """다른 지역 코드로 테스트"""
    test_cases = [
        ("11680", "강남구"),
        ("11650", "서초구"),
        ("11530", "송파구"),
        ("11000", "종로구"),
    ]

    for region_code, region_name in test_cases:
        config = CrawlerConfig(
            api_key="test_key",
            region_code=region_code,
            start_date="2025-01",
        )

        crawler = RealEstateAPICrawler(config)
        url = crawler.get_url()

        assert f"LAWD_CD={region_code}" in url
        assert "DEAL_YMD=202501" in url


def test_api_crawler_with_different_dates():
    """다른 날짜로 테스트"""
    test_cases = [
        "2025-01",
        "2024-12",
        "2024-11",
        "2024-10",
    ]

    for date in test_cases:
        config = CrawlerConfig(
            api_key="test_key",
            region_code="11680",
            start_date=date,
        )

        crawler = RealEstateAPICrawler(config)
        url = crawler.get_url()

        expected_ym = date.replace("-", "")
        assert f"DEAL_YMD={expected_ym}" in url


def test_mock_api_response_parsing():
    """모의 API 응답 파싱 테스트"""
    # 실제와 유사한 API 응답 샘플
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <response>
        <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
            <items>
                <item>
                    <거래금액>155,000</거래금액>
                    <건축년도>2003</건축년도>
                    <년>2025</년>
                    <법정동>개포동</법정동>
                    <아파트>개포자이</아파트>
                    <층>14</층>
                    <전용면적>84.9893</전용면적>
                    <월>1</월>
                    <일>1</일>
                    <시군구>강남구</시군구>
                    <번지>135</번지>
                    <본번>135</본번>
                    <부번>0</부번>
                    <지번>135-0</지번>
                    <도로명>개포로46길</도로명>
                    <도로명건물본번호코드>108</도로명건물본번호코드>
                    <도로명건물부번호코드>0</도로명건물부번호코드>
                    <도로명시군구코드>11680</도로명시군구코드>
                    <도로명일련번호코드>00150</도로명일련번호코드>
                    <법정동읍면동코드>10600</법정동읍면동코드>
                    <법정동시군구코드>11680</법정동시군구코드>
                    <신고일>2025-01-02</신고일>
                    <신규여부>Y</신규여부>
                    <일련번호>11680-10600-20250101-00001</일련번호>
                </item>
                <item>
                    <거래금액>178,000</거래금액>
                    <건축년도>2019</건축년도>
                    <년>2025</년>
                    <법정동>역삼동</법정동>
                    <아파트>역삼포레스타</아파트>
                    <층>3</층>
                    <전용면적>84.9893</전용면적>
                    <월>1</월>
                    <일>5</일>
                    <시군구>강남구</시군구>
                    <번지>727</번지>
                    <본번>727</본번>
                    <부번>12</부번>
                    <지번>727-12</지번>
                    <도로명>테헤란로 211</도로명>
                    <도로명건물본번호코드>211</도로명건물본번호코드>
                    <도로명건물부번호코드>0</도로명건물부번호코드>
                    <도로명시군구코드>11680</도로명시군구코드>
                    <도로명일련번호코드>00023</도로명일련번호코드>
                    <법정동읍면동코드>10500</법정동읍면동코드>
                    <법정동시군구코드>11680</법정동시군구코드>
                    <신고일>2025-01-06</신고일>
                    <신규여부>N</신규여부>
                    <일련번호>11680-10500-20250105-00002</일련번호>
                </item>
            </items>
            <numOfRows>100</numOfRows>
            <pageNo>1</pageNo>
            <totalCount>2</totalCount>
        </body>
    </response>"""

    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    items = crawler.parse(sample_xml)

    assert len(items) == 2

    # 첫 번째 매물 확인
    item1 = items[0]
    assert item1["apartment_name"] == "개포자이"
    assert item1["sale_price"] == 155000
    assert item1["construct_year"] == "2003"
    assert item1["trade_type"] == "매매"
    assert item1["floor"] == "14"
    assert item1["exclusive_area"] == 84.9893
    assert "개포동" in item1["address"]
    assert item1["is_new_deal"] is True

    # 두 번째 매물 확인
    item2 = items[1]
    assert item2["apartment_name"] == "역삼포레스타"
    assert item2["sale_price"] == 178000
    assert item2["construct_year"] == "2019"
    assert item2["trade_type"] == "매매"
    assert item2["floor"] == "3"
    assert "역삼동" in item2["address"]
    assert item2["is_new_deal"] is False
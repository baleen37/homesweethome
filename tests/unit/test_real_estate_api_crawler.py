from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.real_estate_api import RealEstateAPICrawler


@pytest.fixture
def config() -> CrawlerConfig:
    return CrawlerConfig(
        api_key="test_api_key",
        region_code="11680",  # 강남구
        start_date="2025-01",
    )


@pytest.fixture
def crawler(config: CrawlerConfig) -> RealEstateAPICrawler:
    return RealEstateAPICrawler(config)


def test_get_url_with_config(crawler: RealEstateAPICrawler) -> None:
    """설정을 바탕으로 API URL이 올바르게 생성되는지 테스트"""
    url = crawler.get_url()

    assert url.startswith("http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev")
    assert "serviceKey=test_api_key" in url
    assert "LAWD_CD=11680" in url
    assert "DEAL_YMD=202501" in url


def test_get_url_without_region_code() -> None:
    """지역 코드가 없는 경우 URL 생성 테스트"""
    config = CrawlerConfig(api_key="test_key")
    crawler = RealEstateAPICrawler(config)

    url = crawler.get_url()

    assert "serviceKey=test_key" in url
    assert "LAWD_CD" not in url


def test_get_url_without_start_date() -> None:
    """시작일이 없는 경우 현재 월로 설정되는지 테스트"""
    config = CrawlerConfig(api_key="test_key")
    crawler = RealEstateAPICrawler(config)

    url = crawler.get_url()

    # 현재 년월이 포함되어 있는지 확인
    import datetime
    current_ym = datetime.datetime.now().strftime("%Y%m")
    assert f"DEAL_YMD={current_ym}" in url


@patch("crawler.crawlers.real_estate_api.requests.get")
def test_fetch_success(mock_get: Mock, crawler: RealEstateAPICrawler) -> None:
    """API 호출 성공 테스트"""
    mock_response = Mock()
    mock_response.text = "<response>test</response>"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    url = "http://test.com"
    result = crawler.fetch(url)

    assert result == "<response>test</response>"
    mock_get.assert_called_once_with(url, timeout=30)


@patch("crawler.crawlers.real_estate_api.requests.get")
def test_fetch_failure(mock_get: Mock, crawler: RealEstateAPICrawler) -> None:
    """API 호출 실패 시 예외 발생 테스트"""
    mock_get.side_effect = Exception("Network error")

    url = "http://test.com"

    with pytest.raises(Exception):
        crawler.fetch(url)


def test_parse_valid_xml() -> None:
    """유효한 XML 응답 파싱 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <response>
        <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
            <items>
                <item>
                    <일련번호>1</일련번호>
                    <아파트>테스트아파트</아파트>
                    <거래금액>100,000</거래금액>
                    <전용면적>84.52</전용면적>
                    <층>5</층>
                    <건축년도>2010</건축년도>
                    <년>2025</년>
                    <월>1</월>
                    <일>15</일>
                    <신규여부>Y</신규여부>
                    <법정동시군구코드>11680</법정동시군구코드>
                    <법정동읍면동명>개포동</법정동읍면동명>
                </item>
                <item>
                    <일련번호>2</일련번호>
                    <아파트>테스트아파트2</아파트>
                    <보증금액>50,000</보증금액>
                    <월세금액>50</월세금액>
                    <전용면적>75.32</전용면적>
                    <층>3</층>
                    <건축년도>2015</건축년도>
                    <년>2025</년>
                    <월>1</월>
                    <일>20</일>
                    <신규여부>N</신규여부>
                </item>
            </items>
        </body>
    </response>"""

    results = crawler.parse(xml_response)

    assert len(results) == 2

    # 첫 번째 아이템 확인 (매매)
    item1 = results[0]
    assert item1["apartment_name"] == "테스트아파트"
    assert item1["trade_type"] == "매매"
    assert item1["sale_price"] == 100000
    assert item1["jeonse_price"] is None
    assert item1["monthly_rent_fee"] is None
    assert item1["exclusive_area"] == 84.52
    assert item1["floor"] == "5"
    assert item1["construct_year"] == "2010"
    assert item1["is_new_deal"] is True
    assert "준신축" in item1["tags"]  # 2010년 건축은 2025년 기준 15년 차이로 준신축
    assert "신규거래" in item1["tags"]

    # 두 번째 아이템 확인 (월세)
    item2 = results[1]
    assert item2["apartment_name"] == "테스트아파트2"
    assert item2["trade_type"] == "월세"
    assert item2["jeonse_price"] == 50000
    assert item2["monthly_rent_fee"] == 50
    assert item2["sale_price"] is None
    assert item2["exclusive_area"] == 75.32
    assert item2["is_new_deal"] is False


def test_parse_empty_xml() -> None:
    """빈 XML 응답 파싱 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <response>
        <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
            <items>
            </items>
        </body>
    </response>"""

    results = crawler.parse(xml_response)

    assert len(results) == 0


def test_parse_invalid_xml() -> None:
    """잘못된 XML 응답 파싱 시 예외 발생 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    # 진짜 잘못된 XML
    invalid_xml = "<invalid><xml>"

    with pytest.raises(Exception):
        crawler.parse(invalid_xml)


def test_parse_price() -> None:
    """가격 파싱 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    # 정상 가격
    assert crawler._parse_price("100,000") == 100000
    assert crawler._parse_price("50000") == 50000
    assert crawler._parse_price("  1,234  ") == 1234

    # 빈 값이나 None
    assert crawler._parse_price("") is None
    assert crawler._parse_price(None) is None

    # 잘못된 형식
    assert crawler._parse_price("invalid") is None


def test_determine_trade_type() -> None:
    """거래 유형 결정 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    # 매매
    assert crawler._determine_trade_type({"거래금액": "100000"}) == "매매"

    # 월세
    assert crawler._determine_trade_type({
        "보증금액": "50000",
        "월세금액": "50"
    }) == "월세"

    # 전세
    assert crawler._determine_trade_type({"보증금액": "50000"}) == "전세"

    # 기타
    assert crawler._determine_trade_type({}) == "기타"


def test_build_address() -> None:
    """주소 조합 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    item_data = {
        "시도명": "서울특별시",
        "시군구명": "강남구",
        "법정동읍면동명": "개포동",
        "지번본번": "123",
        "지번부번": "1",
    }

    address = crawler._build_address(item_data)
    assert address == "서울특별시 강남구 개포동 123-1"  # 부번이 0이 아닌 경우 하이픈 추가

    # 일부 정보만 있는 경우
    partial_data = {
        "시도명": "서울특별시",
        "시군구명": "강남구",
    }

    address = crawler._build_address(partial_data)
    assert address == "서울특별시 강남구"


def test_extract_tags() -> None:
    """태그 추출 테스트"""
    config = CrawlerConfig()
    crawler = RealEstateAPICrawler(config)

    # 신축 건물
    current_year = 2025
    with patch("crawler.crawlers.real_estate_api.datetime") as mock_datetime:
        mock_datetime.now.return_value.year = current_year

        # 신축 (5년 이하)
        new_building = {"건축년도": "2023", "신규여부": "Y"}
        tags = crawler._extract_tags(new_building)
        assert "신축" in tags
        assert "신규거래" in tags

        # 준신축 (15년 이하)
        semi_new = {"건축년도": "2015", "신규여부": "N"}
        tags = crawler._extract_tags(semi_new)
        assert "준신축" in tags
        assert "신규거래" not in tags

        # 구축 (15년 초과)
        old_building = {"건축년도": "2005", "신규여부": "N"}
        tags = crawler._extract_tags(old_building)
        assert "구축" in tags


def test_crawl_integration(config: CrawlerConfig) -> None:
    """전체 크롤링 프로세스 통합 테스트"""
    crawler = RealEstateAPICrawler(config)

    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <response>
        <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
            <items>
                <item>
                    <일련번호>1</일련번호>
                    <아파트>통합테스트아파트</아파트>
                    <거래금액>200,000</거래금액>
                    <전용면적>95.45</전용면적>
                    <층>15</층>
                    <건축년도>2020</건축년도>
                </item>
            </items>
        </body>
    </response>"""

    with patch.object(crawler, 'fetch') as mock_fetch:
        mock_fetch.return_value = xml_response

        results = crawler.crawl()

        assert len(results) == 1
        assert results[0]["apartment_name"] == "통합테스트아파트"
        assert results[0]["sale_price"] == 200000
        assert results[0]["trade_type"] == "매매"
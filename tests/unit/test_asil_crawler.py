"""AsilCrawler 단위 테스트"""

import pytest

from crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_trade_price import AsilTradePriceDTO


def test_asil_apt_list_crawler_init():
    """AsilAptListCrawler 초기화 테스트"""
    crawler = AsilAptListCrawler(dong_code="1150010100")

    assert crawler.dong_code == "1150010100"
    assert crawler.building_type == ""
    assert crawler.min_household == 0
    assert crawler.order == 0
    assert crawler.order_type == 0


def test_asil_apt_list_crawler_get_url():
    """AsilAptListCrawler URL 생성 테스트"""
    crawler = AsilAptListCrawler(
        dong_code="1150010100",
        building_type="apt",
        min_household=100,
        order=1,
        order_type=1,
    )

    url = crawler.get_url()

    assert "https://asil.kr/app/data/data_apt_list.jsp" in url
    assert "dong=1150010100" in url
    assert "building=apt" in url
    assert "household=100" in url
    assert "order=1" in url
    assert "order_type=1" in url


def test_asil_apt_list_crawler_parse():
    """AsilAptListCrawler 파싱 테스트"""
    crawler = AsilAptListCrawler(dong_code="1150010100")

    # 유효한 JSON 배열
    content = '[{"seq":"1","name":"테스트아파트","dong":"1150010100","dongname":"역삼동"}]'

    result = crawler.parse(content)

    assert len(result) == 1
    assert isinstance(result[0], AsilAptListDTO)
    assert result[0].seq == "1"
    assert result[0].name == "테스트아파트"


def test_asil_apt_list_crawler_parse_invalid():
    """AsilAptListCrawler 잘못된 데이터 파싱 테스트"""
    import json

    crawler = AsilAptListCrawler(dong_code="1150010100")

    # 유효하지 않은 JSON - 예외 발생
    with pytest.raises(json.JSONDecodeError):
        crawler.parse("not json")
    # 유효하지만 리스트가 아님
    assert crawler.parse('{"key":"value"}') == []


def test_asil_trade_price_crawler_init():
    """AsilTradePriceCrawler 초기화 테스트"""
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
    )

    assert crawler.apt_code == "20340925"
    assert crawler.sido_code == "11"
    assert crawler.area_m2 == 114
    assert crawler.deal_mode == "123"
    assert crawler.building == "apt"
    assert crawler.year == "9999"
    assert crawler.start == 0
    assert crawler.count == 100


def test_asil_trade_price_crawler_get_url():
    """AsilTradePriceCrawler URL 생성 테스트"""
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
        deal_mode="1",
        year="2024",
        start=0,
        count=50,
    )

    url = crawler.get_url()

    assert "https://asil.kr/app/data/apt_price_m2_mjw_newver_6.jsp" in url
    assert "seq=20340925" in url
    assert "sido=11" in url
    assert "m2=114" in url
    assert "dealmode=1" in url
    assert "year=2024" in url
    assert "start=0" in url
    assert "count=50" in url


def test_asil_trade_price_crawler_parse():
    """AsilTradePriceCrawler 파싱 테스트"""
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
    )

    # 유효한 JSON 배열
    content = '[{"val":[]}]'

    result = crawler.parse(content)

    assert len(result) == 1
    assert isinstance(result[0], AsilTradePriceDTO)


def test_asil_trade_price_crawler_parse_invalid():
    """AsilTradePriceCrawler 잘못된 데이터 파싱 테스트"""
    import json

    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
    )

    # 유효하지 않은 JSON - 예외 발생
    with pytest.raises(json.JSONDecodeError):
        crawler.parse("not json")
    # 유효하지만 리스트가 아님
    assert crawler.parse('{"key":"value"}') == []


def test_asil_apt_list_crawler_encoding():
    """AsilAptListCrawler 인코딩 테스트"""
    crawler = AsilAptListCrawler(dong_code="1150010100")

    # UTF-8 인코딩 사용 (기본값)
    assert crawler.get_url() is not None


def test_asil_trade_price_crawler_encoding():
    """AsilTradePriceCrawler EUC-KR 인코딩 테스트"""
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
    )

    # EUC-KR 인코딩 사용
    assert crawler.ENCODING == "euc_kr"

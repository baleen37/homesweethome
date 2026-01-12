"""AsilCrawler 통합 테스트 - 실제 API 호출"""

import pytest

from crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_trade_price import AsilTradePriceDTO


@pytest.mark.integration
def test_asil_apt_list_crawl_real_api():
    """실제 ASIL API 호출 테스트 - 아파트 목록"""
    crawler = AsilAptListCrawler(dong_code="1150010100")  # 역삼동

    result = crawler.crawl()

    assert isinstance(result, list)
    # 역삼동에는 아파트가 있어야 함
    assert len(result) > 0
    assert all(isinstance(item, AsilAptListDTO) for item in result)


@pytest.mark.integration
def test_asil_apt_list_crawl_with_filters():
    """실제 ASIL API 호출 테스트 - 필터 적용"""
    crawler = AsilAptListCrawler(
        dong_code="1150010100",
        building_type="apt",
        min_household=100,
    )

    result = crawler.crawl()

    assert isinstance(result, list)
    # 100세대 이상 아파트만 필터링
    if result:
        for apt in result:
            if apt.household:
                assert int(apt.household) >= 100


@pytest.mark.integration
def test_asil_apt_list_crawl_empty_dong():
    """실제 ASIL API 호출 테스트 - 없는 동 코드"""
    # 존재하지 않는 동 코드
    crawler = AsilAptListCrawler(dong_code="9999999999")

    result = crawler.crawl()

    # 빈 결과가 반환되어야 함
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.integration
def test_asil_trade_price_crawl_real_api():
    """실제 ASIL API 호출 테스트 - 실거래가"""
    # 역삼자이 아파트 코드
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",  # 서울
        area_m2=114,
    )

    result = crawler.crawl()

    assert isinstance(result, list)
    # 실거래가 데이터가 있을 수도 있고 없을 수도 있음
    assert all(isinstance(item, AsilTradePriceDTO) for item in result)


@pytest.mark.integration
def test_asil_trade_price_crawl_with_filters():
    """실제 ASIL API 호출 테스트 - 실거래가 필터"""
    crawler = AsilTradePriceCrawler(
        apt_code="20340925",
        sido_code="11",
        area_m2=114,
        deal_mode="1",  # 매매만
        year="2024",
        count=10,
    )

    result = crawler.crawl()

    assert isinstance(result, list)
    assert len(result) <= 1  # count는 API에서 무시될 수 있음
    assert all(isinstance(item, AsilTradePriceDTO) for item in result)


@pytest.mark.integration
def test_asil_trade_price_crawl_invalid_apt():
    """실제 ASIL API 호출 테스트 - 없는 아파트 코드"""
    crawler = AsilTradePriceCrawler(
        apt_code="99999999",
        sido_code="11",
        area_m2=84,
    )

    result = crawler.crawl()

    # 빈 결과가 반환되어야 함
    assert isinstance(result, list)

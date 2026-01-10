"""AsilCrawler 통합 테스트 - 실제 API 호출"""

import pytest

from crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler


@pytest.mark.integration
class TestAsilAptListCrawlerIntegration:
    """AsilAptListCrawler 통합 테스트"""

    def test_fetch_real_apt_list_for_yeoksam(self):
        """역삼동(1168010100)의 아파트 목록을 실제로 가져옴"""
        crawler = AsilAptListCrawler(dong_code="1168010100")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 역삼동에는 적어도 1개 이상의 아파트가 있어야 함
        assert len(result) > 0

        # 각 아파트 정보에 필수 필드가 있어야 함
        apt = result[0]
        assert "seq" in apt
        assert "name" in apt

    def test_fetch_real_apt_list_with_min_household_filter(self):
        """세대수 필터가 적용된 아파트 목록을 가져옴"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert isinstance(result, list)
        # 100세대 이상인 아파트만 필터링되어야 함
        # 실제 API에서 필터링을 수행하는지 확인
        for apt in result:
            # 세대수 필드에 콤마가 포함된 경우 제거 (예: "1,050" → 1050)
            household_str = apt.get("household", "0")
            household = int(household_str.replace(",", ""))
            assert household >= 100

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilAptListCrawler(dong_code="1168010100")

        # crawl()은 get_url() -> fetch() -> parse() 순서로 호출해야 함
        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilTradePriceCrawlerIntegration:
    """AsilTradePriceCrawler 통합 테스트"""

    def test_fetch_real_trade_prices_for_yeoksam_jai(self):
        """역삼자이(20340925)의 실거래가를 실제로 가져옴"""
        crawler = AsilTradePriceCrawler(
            apt_code="20340925",
            sido_code="11",
            area_m2=114,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 역삼자이에는 적어도 1개 이상의 실거래가 데이터가 있어야 함
        assert len(result) > 0

        # 각 실거래가 정보에 필수 필드가 있어야 함
        trade = result[0]
        # 실제 API 응답 필드: date_j, date_m, max_j, max_m 등
        assert "date_j" in trade or "date_m" in trade

    def test_fetch_trade_prices_with_deal_mode_filter(self):
        """거래 유형 필터가 적용된 실거래가를 가져옴"""
        crawler = AsilTradePriceCrawler(
            apt_code="20340925",
            sido_code="11",
            area_m2=114,
            deal_mode="1",  # 매매만
        )
        result = crawler.crawl()

        assert isinstance(result, list)
        # 매매 데이터만 반환되어야 함 (API 응답 구조에 따름)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilTradePriceCrawler(
            apt_code="20340925",
            sido_code="11",
            area_m2=114,
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilCrawlerFullWorkflow:
    """asil.kr 크롤러 전체 워크플로우 테스트"""

    def test_full_workflow_apt_list_to_trade_prices(self):
        """아파트 목록 → 특정 아파트 선택 → 실거래가 조회 전체 흐름"""
        # 1. 아파트 목록 가져오기
        apt_crawler = AsilAptListCrawler(dong_code="1168010100")
        apt_list = apt_crawler.crawl()

        assert len(apt_list) > 0

        # 2. 첫 번째 아파트 선택
        first_apt = apt_list[0]
        apt_code = first_apt["seq"]

        # 3. 해당 아파트의 실거래가 가져오기
        # 역삼자이의 경우 114㎡ 타입이 있으므로 해당 면적으로 조회
        price_crawler = AsilTradePriceCrawler(
            apt_code=apt_code,
            sido_code="11",
            area_m2=114,
        )
        trade_prices = price_crawler.crawl()

        # 실거래가가 반환되어야 함 (해당 면적의 데이터가 없을 수도 있음)
        assert isinstance(trade_prices, list)

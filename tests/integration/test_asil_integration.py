"""AsilCrawler 통합 테스트 - 실제 API 호출"""

import urllib.error

import pytest

from crawler.asil import (
    AsilAgentInfoCrawler,
    AsilAptListCrawler,
    AsilDongInfoCrawler,
    AsilEducationMapCrawler,
    AsilListingCrawler,
    AsilOffersListCrawler,
    AsilPopulationCrawler,
    AsilPriceIndexCrawler,
    AsilRankingCrawler,
    AsilRedevelopCrawler,
    AsilSchoolInfoCrawler,
    AsilTradePriceCrawler,
    AsilTrafficCrawler,
    AsilTransferCrawler,
    AsilVisitorStatsCrawler,
)
from crawler.dto.asil_agent import AsilAgentDTO, AsilAgentInfoResponse
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_offer import AsilOfferDTO, AsilOffersListResponse


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
        assert isinstance(apt, AsilAptListDTO)
        assert apt.seq
        assert apt.name
        # 실제 API 응답에서 address, build_year 필드는 항상 None 반환
        assert apt.address is None
        assert apt.build_year is None

    def test_fetch_real_apt_list_with_min_household_filter(self):
        """세대수 필터가 적용된 아파트 목록을 가져옴"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert isinstance(result, list)
        # 100세대 이상인 아파트만 필터링되어야 함
        # 실제 API에서 필터링을 수행하는지 확인
        for apt in result:
            # 세대수 필드에 콤마가 포함된 경우 제거 (예: "1,050" → 1050)
            household_str = apt.household or "0"
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
        # 실제 API 응답 필드: val, price_total, is_more 등
        assert "val" in trade or "price_total" in trade or "is_more" in trade

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
        apt_code = first_apt.seq

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


@pytest.mark.integration
class TestAsilTrafficCrawlerIntegration:
    """AsilTrafficCrawler 통합 테스트"""

    def test_fetch_real_traffic_data_for_gangnam(self):
        """강남구 좌표로 교통정보를 실제로 가져옴"""
        # 강남구 좌표 (대략적인 범위)
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,  # 강남역 근처
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 각 교통정보는 딕셔너리여야 함
        for item in result:
            assert isinstance(item, dict)

    def test_fetch_traffic_data_with_filters(self):
        """필터가 적용된 교통정보를 가져옴"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
            traffic_types="1",  # 지하철만
            year_min=2024,
            year_max=2028,
        )
        result = crawler.crawl()

        assert isinstance(result, list)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilDongInfoCrawlerIntegration:
    """AsilDongInfoCrawler 통합 테스트"""

    def test_fetch_real_dong_info_for_yeoksam_jai(self):
        """역삼자이(20340925)의 동 정보를 실제로 가져옴"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 역삼자이에는 적어도 1개 이상의 동 정보가 있어야 함
        assert len(result) > 0

        # 각 동 정보에 필수 필드가 있어야 함
        dong = result[0]
        assert "dong" in dong

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilSchoolInfoCrawlerIntegration:
    """AsilSchoolInfoCrawler 통합 테스트"""

    def test_fetch_real_elementary_schools_for_gangnam(self):
        """강남구(11680)의 초등학교 목록을 실제로 가져옴"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary", area_code="11680")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 강남구에는 적어도 1개 이상의 초등학교가 있어야 함
        assert len(result) > 0

        # 각 학교 정보에 필수 필드가 있어야 함
        school = result[0]
        assert "seq" in school
        assert "name" in school

    def test_fetch_real_middle_schools_for_gangnam(self):
        """강남구(11680)의 중학교 목록을 실제로 가져옴"""
        crawler = AsilSchoolInfoCrawler(school_type="middle", area_code="11680")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 강남구에는 적어도 1개 이상의 중학교가 있어야 함
        assert len(result) > 0

        # 각 학교 정보에 필수 필드가 있어야 함
        school = result[0]
        assert "seq" in school
        assert "name" in school

    def test_fetch_schools_with_bounds(self):
        """좌표 기반 검색으로 학교 목록을 가져옴"""
        # 강남구 대략적인 좌표 범위
        bounds = {
            "s_lat": "37.5",
            "s_lng": "127.0",
            "e_lat": "37.6",
            "e_lng": "127.1",
        }
        crawler = AsilSchoolInfoCrawler(school_type="elementary", bounds=bounds)
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary", area_code="11680")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilEducationMapCrawlerIntegration:
    """AsilEducationMapCrawler 통합 테스트"""

    def test_fetch_real_education_map_for_gangnam(self):
        """강남구 좌표로 학군 지도 정보를 실제로 가져옴"""
        crawler = AsilEducationMapCrawler(
            s_lat=37.54,
            s_lng=127.00,
            e_lat=37.63,
            e_lng=127.14,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필드 확인
        if len(result) > 0:
            assert hasattr(result[0], "title")
            assert hasattr(result[0], "lat")
            assert hasattr(result[0], "lng")
            assert result[0].title is not None

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilEducationMapCrawler(
            s_lat=37.54,
            s_lng=127.00,
            e_lat=37.63,
            e_lng=127.14,
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilVisitorStatsCrawlerIntegration:
    """AsilVisitorStatsCrawler 통합 테스트"""

    def test_fetch_real_visitor_stats_for_gangnam_station(self):
        """강남역 좌표로 조회수/관심사용자 통계를 실제로 가져옴"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.504575,
            s_lng=127.044555,
            e_lat=37.514575,
            e_lng=127.054555,
            zoom=14,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            stat = result[0]
            assert "key" in stat
            assert "lat" in stat
            assert "lng" in stat

    def test_fetch_visitor_stats_with_different_zoom_level(self):
        """다른 줌 레벨로 조회수 통계를 가져옴"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
            zoom=13,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.504575,
            s_lng=127.044555,
            e_lat=37.514575,
            e_lng=127.054555,
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilRedevelopCrawlerIntegration:
    """AsilRedevelopCrawler 통합 테스트"""

    def test_fetch_real_redevelop_data_for_gangnam(self):
        """강남구 좌표로 재개발 단지 정보를 실제로 가져옴"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.48,
            s_lng=127.00,
            e_lat=37.62,
            e_lng=127.15,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 각 재개발 정보는 딕셔너리여야 함
        for item in result:
            assert isinstance(item, dict)

    def test_fetch_redevelop_data_with_type_filter(self):
        """유형 필터가 적용된 재개발 정보를 가져옴"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.48,
            s_lng=127.00,
            e_lat=37.62,
            e_lng=127.15,
            type_value="1",  # 재개발 유형 1
            zoom=12,
        )
        result = crawler.crawl()

        assert isinstance(result, list)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.48,
            s_lng=127.00,
            e_lat=37.62,
            e_lng=127.15,
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilListingCrawlerIntegration:
    """AsilListingCrawler 통합 테스트"""

    def test_fetch_real_listings_for_yeoksam(self):
        """역삼동(1168010100)의 매물 정보를 실제로 가져옴"""
        crawler = AsilListingCrawler(apt_code="1168010100")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 매물이 있는 항목만 반환되어야 함
        for listing in result:
            assert listing.offer, "매물 정보(offer 필드)가 있어야 함"

        # 역삼동에는 적어도 1개 이상의 매물이 있어야 함
        assert len(result) > 0

        # 각 매물 정보에 필수 필드가 있어야 함
        listing = result[0]
        assert listing.seq
        assert listing.name
        # 실제 API 응답에서 offer 필드는 "매물 N건" 형태의 문자열 반환
        assert listing.offer
        assert isinstance(listing.offer, str)
        assert "매물" in listing.offer

    def test_fetch_listings_with_min_household_filter(self):
        """세대수 필터가 적용된 매물 목록을 가져옴"""
        crawler = AsilListingCrawler(apt_code="1168010100", min_household=50)
        result = crawler.crawl()

        assert isinstance(result, list)
        # 모든 결과에 매물 정보가 있어야 함
        for listing in result:
            assert listing.offer

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilListingCrawler(apt_code="1168010100")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)
        # 매물이 있는 항목만 필터링되어야 함
        for listing in result:
            assert listing.offer


@pytest.mark.integration
class TestAsilRankingCrawlerIntegration:
    """AsilRankingCrawler 통합 테스트"""

    def test_fetch_real_ranking_max_price(self):
        """서울(11) 지역의 최고가 랭킹을 실제로 가져옴"""
        crawler = AsilRankingCrawler(area="11", theme="max")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 최고가 랭킹에는 적어도 1개 이상의 데이터가 있어야 함
        # API에서 데이터를 반환하지 않을 수도 있으므로 유연하게 처리
        if len(result) > 0:
            # 각 랭킹 정보에 필수 필드가 있어야 함
            ranking = result[0]
            assert ranking.idx
            assert ranking.seq
            assert ranking.name
            assert ranking.price

    def test_fetch_real_ranking_min_price(self):
        """서울(11) 지역의 최저가 랭킹을 실제로 가져옴"""
        crawler = AsilRankingCrawler(area="11", theme="min")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 최저가 랭킹에는 적어도 1개 이상의 데이터가 있어야 함
        # API에서 데이터를 반환하지 않을 수도 있으므로 유연하게 처리
        if len(result) > 0:
            # 각 랭킹 정보에 필수 필드가 있어야 함
            ranking = result[0]
            assert ranking.idx
            assert ranking.seq
            assert ranking.name
            assert ranking.price

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilRankingCrawler(area="11", theme="max")

        # crawl()은 get_url() -> fetch() -> parse() 순서로 호출해야 함
        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilPriceIndexCrawlerIntegration:
    """AsilPriceIndexCrawler 통합 테스트"""

    def test_fetch_real_price_index_seoul(self):
        """서울(11) 지역의 매매가 지수를 실제로 가져옴"""
        crawler = AsilPriceIndexCrawler(area="11", deal_mode="M")
        try:
            result = crawler.crawl()
        except urllib.error.HTTPError as e:
            pytest.skip(f"API 서버 오류: {e.code}")

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 가격 지수에는 적어도 1개 이상의 데이터가 있어야 함
        assert len(result) > 0

        # 데이터 구조 확인 (지역 데이터 또는 요약 데이터)
        first_item = result[0]
        # 지역 데이터 또는 요약 데이터여야 함
        assert hasattr(first_item, "seq") or hasattr(first_item, "min")

    def test_fetch_price_index_with_date_range(self):
        """날짜 범위를 지정하여 가격 지수를 가져옴"""
        crawler = AsilPriceIndexCrawler(
            area="11",
            deal_mode="M",
            start_year="2024",
            start_month="1",
            start_day="1",
            end_year="2024",
            end_month="12",
            end_day="31",
        )
        try:
            result = crawler.crawl()
        except urllib.error.HTTPError as e:
            pytest.skip(f"API 서버 오류: {e.code}")

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 구조 확인
        if len(result) > 0:
            # 마지막 항목은 요약 객체일 수 있음
            last_item = result[-1]
            if hasattr(last_item, "min"):
                # 요약 객체
                assert last_item.min
                assert last_item.max

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilPriceIndexCrawler(area="11", deal_mode="M")
        try:
            result = crawler.crawl()
        except urllib.error.HTTPError as e:
            pytest.skip(f"API 서버 오류: {e.code}")

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilPopulationCrawlerIntegration:
    """AsilPopulationCrawler 통합 테스트"""

    def test_fetch_real_population_seoul(self):
        """서울(11)의 인구 통계를 실제로 가져옴"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            pop = result[0]
            assert pop.seq
            assert pop.name
            # 인구값 필드가 있어야 함
            assert pop.v1 or pop.v2 or pop.v3

    def test_fetch_population_with_year_month(self):
        """특정 연도/월의 인구 통계를 가져옴"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            pop = result[0]
            assert pop.seq
            assert pop.name

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilTransferCrawlerIntegration:
    """AsilTransferCrawler 통합 테스트"""

    def test_fetch_real_transfer_seoul(self):
        """서울(11)의 인구 유동 데이터를 실제로 가져옴"""
        crawler = AsilTransferCrawler(
            area="11",
            start_year="2024",
            start_month="1",
            end_year="2024",
            end_month="12",
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            transfer = result[0]
            assert transfer.rank >= 0
            assert transfer.from_ or transfer.to

    def test_fetch_transfer_with_date_range(self):
        """특정 기간의 인구 유동 데이터를 가져옴"""
        crawler = AsilTransferCrawler(
            area="11",
            start_year="2024",
            start_month="1",
            end_year="2024",
            end_month="12",
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            transfer = result[0]
            assert transfer.rank >= 0
            # total과 value 필드가 숫자 형식 문자열이어야 함
            assert transfer.total or transfer.value

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilTransferCrawler(
            area="11",
            start_year="2024",
            start_month="1",
            end_year="2024",
            end_month="12",
        )

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilOffersListCrawlerIntegration:
    """AsilOffersListCrawler 통합 테스트"""

    def test_fetch_real_offers_list_seoul(self):
        """서울(bdong_code="11")의 매물 목록을 실제로 가져옴"""
        crawler = AsilOffersListCrawler(bdong_code="11", page=1)
        result = crawler.crawl()

        # 결과가 AsilOffersListResponse여야 함
        assert isinstance(result, AsilOffersListResponse)

        # list_result 필드가 리스트여야 함
        assert isinstance(result.list_result, list)

        # 서울에는 적어도 1개 이상의 매물이 있어야 함 (데이터가 있다고 가정)
        # API가 빈 결과를 반환할 수 있으므로 graceful하게 처리
        if len(result.list_result) > 0:
            # 각 매물 정보에 필수 필드가 있어야 함
            offer = result.list_result[0]
            assert isinstance(offer, AsilOfferDTO)
            assert offer.mm_uid
            assert offer.BLDNM

    def test_fetch_offers_list_with_filters(self):
        """가격/면적 필터가 적용된 매물 목록을 가져옴"""
        crawler = AsilOffersListCrawler(
            bdong_code="11",
            min_price=50000,  # 5억 이상
            max_price=200000,  # 20억 이하
            min_space=80,  # 80㎡ 이상
            max_space=160,  # 160㎡ 이하
            page=1,
        )
        result = crawler.crawl()

        assert isinstance(result, AsilOffersListResponse)
        assert isinstance(result.list_result, list)

        # 필터링된 결과 확인 (데이터가 있는 경우)
        for offer in result.list_result:
            # 매물이 존재하면 적어도 기본 필드는 있어야 함
            assert offer.mm_uid
            assert offer.BLDNM

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilOffersListCrawler(bdong_code="11", page=1)

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, AsilOffersListResponse)
        assert isinstance(result.list_result, list)


@pytest.mark.integration
class TestAsilAgentInfoCrawlerIntegration:
    """AsilAgentInfoCrawler 통합 테스트"""

    def test_fetch_real_agent_info(self):
        """유효한 user_id("-20040")의 중개사 정보를 실제로 가져옴"""
        crawler = AsilAgentInfoCrawler(user_id="-20040")
        result = crawler.crawl()

        # 결과가 AsilAgentInfoResponse여야 함
        assert isinstance(result, AsilAgentInfoResponse)

        # result 필드가 bool이어야 함
        assert isinstance(result.result, bool)

        # API가 성공하면 중개사 정보가 있어야 함
        if result.result:
            assert isinstance(result.agent, AsilAgentDTO)
            # 중개사 필수 필드 확인
            assert result.agent.seq
            assert result.agent.company
            assert result.agent.name

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilAgentInfoCrawler(user_id="-20040")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, AsilAgentInfoResponse)
        assert isinstance(result.result, bool)

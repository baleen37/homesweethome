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
        """역삼동(1168010100)의 아파트 목록을 실제로 가져옴

        API 동작 참고:
        - min_household=0으로 요청하면 API 응답의 household 필드가 '0'으로 에코됨
        - min_household>0으로 요청하면 API 응답에 실제 세대수가 반환됨
        """
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
        # 실제 API 응답에서 address 필드는 None 반환
        assert apt.address is None
        # build_year는 movein 필드로 매핑되어 있음 (alias 적용)
        assert apt.build_year is not None

        # API 동작 검증: min_household=0으로 요청하면 household가 '0'으로 에코됨
        # 이는 API의 설계상의 동작으로, 요청 파라미터의 household 값을 응답 필드에 그대로 반환함
        assert apt.household == "0", (
            f"min_household=0 요청 시 household 필드가 '0'으로 에코되어야 함. "
            f"실제 값: {repr(apt.household)}"
        )

    def test_fetch_real_apt_list_with_min_household_filter(self):
        """세대수 필터가 적용된 아파트 목록을 가져옴

        API 동작 참고:
        - min_household>0으로 요청하면 API 응답에 실제 세대수가 반환됨
        - API는 min_household 값 이상의 세대수를 가진 아파트만 필터링하여 반환
        """
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert isinstance(result, list)

        # min_household>0이므로 결과가 있어야 함
        assert len(result) > 0

        # 100세대 이상인 아파트만 필터링되어야 함
        # 실제 API에서 필터링을 수행하는지 확인
        for apt in result:
            # 세대수 필드에 콤마가 포함된 경우 제거 (예: "1,050" → 1050)
            household_str = apt.household or "0"
            household = int(household_str.replace(",", ""))
            assert household >= 100, (
                f"{apt.name}의 세대수 {household}가 min_household=100보다 작습니다"
            )

        # 첫 번째 아파트로 실제 세대수가 반환되는지 검증
        # min_household>0이면 household 필드에 실제 세대수가 반환됨
        first_apt = result[0]
        assert first_apt.household != "0", (
            f"min_household>0 요청 시 household 필드가 실제 세대수여야 함. "
            f"실제 값: {repr(first_apt.household)}"
        )

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

        # 2. 역삼자이 아파트 찾기 (114㎡ 타입이 있어 실거래가 조회에 적합)
        yeoksam_jai = None
        for apt in apt_list:
            if apt.seq == "20340925" or "역삼자이" in apt.name:
                yeoksam_jai = apt
                break

        # 역삼자이를 찾지 못하면 첫 번째 아파트 사용
        target_apt = yeoksam_jai if yeoksam_jai else apt_list[0]
        apt_code = target_apt.seq

        # 3. 해당 아파트의 실거래가 가져오기
        # 역삼자이의 경우 114㎡ 타입이 있으므로 해당 면적으로 조회
        price_crawler = AsilTradePriceCrawler(
            apt_code=apt_code,
            sido_code="11",
            area_m2=114,
        )
        trade_prices = price_crawler.crawl()

        # 실거래가가 리스트로 반환되어야 함
        assert isinstance(trade_prices, list)

        # 역삼자이인 경우 실거래가 데이터가 있어야 함
        if yeoksam_jai:
            assert len(trade_prices) > 0
            # 실거래가 데이터 구조 검증
            trade = trade_prices[0]
            assert hasattr(trade, "val")
            assert hasattr(trade, "price_total")
            assert hasattr(trade, "is_more")


@pytest.mark.integration
class TestAsilTrafficCrawlerIntegration:
    """AsilTrafficCrawler 통합 테스트"""

    def _validate_traffic_dto(self, traffic) -> None:
        """AsilTrafficInfoDTO 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_traffic import AsilTrafficInfoDTO

        # 1. 각 아이템이 AsilTrafficInfoDTO인지
        assert isinstance(traffic, AsilTrafficInfoDTO), "각 아이템은 AsilTrafficInfoDTO여야 함"

        # 2. key 필드가 존재하고 비어있지 않은지
        assert traffic.key, "key 필드는 비어있지 않아야 함"

        # 3. title 필드가 존재하고 비어있지 않은지
        assert traffic.title, "title 필드는 비어있지 않아야 함"

        # 4. lat, lng가 float로 변환 가능한지
        if traffic.lat:
            try:
                float(traffic.lat)
            except (ValueError, TypeError):
                raise AssertionError(f"lat '{traffic.lat}'는 float로 변환 가능해야 함")

        if traffic.lng:
            try:
                float(traffic.lng)
            except (ValueError, TypeError):
                raise AssertionError(f"lng '{traffic.lng}'는 float로 변환 가능해야 함")

        # 5. s_year, e_year가 있으면 "YYYY" 형식인지
        if traffic.s_year:
            msg = f"s_year은 4자리 연도여야 함: {traffic.s_year}"
            assert len(traffic.s_year) == 4, msg
            msg = f"s_year은 숫자로 구성되어야 함: {traffic.s_year}"
            assert traffic.s_year.isdigit(), msg

        if traffic.e_year:
            msg = f"e_year은 4자리 연도여야 함: {traffic.e_year}"
            assert len(traffic.e_year) == 4, msg
            msg = f"e_year은 숫자로 구성되어야 함: {traffic.e_year}"
            assert traffic.e_year.isdigit(), msg

    def test_fetch_real_traffic_data_for_gangnam(self):
        """강남구 좌표로 교통정보를 실제로 가져옴"""
        from crawler.dto.asil_traffic import AsilTrafficInfoDTO

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

        # 각 교통정보는 DTO여야 함
        for item in result:
            assert isinstance(item, AsilTrafficInfoDTO)

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

    def test_traffic_data_validation(self):
        """교통정보 데이터 필드 검증"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )
        result = crawler.crawl()

        assert isinstance(result, list)

        # 데이터가 있으면 상세 검증 수행
        if len(result) > 0:
            for traffic in result:
                self._validate_traffic_dto(traffic)

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

    def _validate_school_dict(self, school: dict) -> None:
        """학교 데이터(dict) 필드 검증 헬퍼 메서드"""
        # 1. 각 아이템이 dict인지
        assert isinstance(school, dict), "각 학교 정보는 dict 타입이어야 함"

        # 2. seq 필드가 존재하고 비어있지 않은지
        assert "seq" in school, "seq 필드가 존재해야 함"
        assert school["seq"], "seq 필드는 비어있지 않아야 함"

        # 3. name 필드가 존재하고 비어있지 않은지
        assert "name" in school, "name 필드가 존재해야 함"
        assert school["name"], "name 필드는 비어있지 않아야 함"

        # 4. addr 필드가 존재하고 비어있지 않은지
        assert "addr" in school, "addr 필드가 존재해야 함"
        assert school["addr"], "addr 필드는 비어있지 않아야 함"

    def test_fetch_real_elementary_schools_for_gangnam(self):
        """강남구(11680)의 초등학교 목록을 실제로 가져옴"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary", area_code="11680")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 강남구에는 적어도 1개 이상의 초등학교가 있어야 함
        assert len(result) > 0

        # 모든 학교 데이터 검증
        for school in result:
            self._validate_school_dict(school)

    def test_fetch_real_middle_schools_for_gangnam(self):
        """강남구(11680)의 중학교 목록을 실제로 가져옴"""
        crawler = AsilSchoolInfoCrawler(school_type="middle", area_code="11680")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 강남구에는 적어도 1개 이상의 중학교가 있어야 함
        assert len(result) > 0

        # 모든 학교 데이터 검증
        for school in result:
            self._validate_school_dict(school)

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

        # 데이터가 있으면 검증
        if len(result) > 0:
            for school in result:
                self._validate_school_dict(school)

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

    def test_education_map_data_validation(self):
        """학군 지도 데이터 필드 검증"""
        from crawler.dto.asil_education_map import AsilEducationMapDTO

        crawler = AsilEducationMapCrawler(
            s_lat=37.54,
            s_lng=127.00,
            e_lat=37.63,
            e_lng=127.14,
        )
        result = crawler.crawl()

        assert isinstance(result, list)

        # 데이터가 있는 경우에만 상세 검증 수행
        if len(result) > 0:
            edu_map = result[0]

            # 1. AsilEducationMapDTO 타입인지
            assert isinstance(edu_map, AsilEducationMapDTO), "AsilEducationMapDTO 타입이어야 함"

            # 2. title 필드가 존재하고 비어있지 않은지
            assert edu_map.title is not None, "title 필드가 존재해야 함"
            assert len(edu_map.title) > 0, "title 필드는 비어있지 않아야 함"

            # 3. lat, lng가 float로 변환 가능한지
            assert edu_map.lat is not None, "lat 필드가 존재해야 함"
            try:
                float(edu_map.lat)
            except ValueError:
                raise AssertionError(f"lat '{edu_map.lat}'는 float로 변환 가능해야 함")

            assert edu_map.lng is not None, "lng 필드가 존재해야 함"
            try:
                float(edu_map.lng)
            except ValueError:
                raise AssertionError(f"lng '{edu_map.lng}'는 float로 변환 가능해야 함")

            # 4. polygon 필드가 있는지 (GeoJSON 형식)
            # polygon은 옵션 필드이므로 있는 경우에만 검증
            if edu_map.polygon is not None:
                assert isinstance(edu_map.polygon, list), "polygon은 리스트여야 함"
                # polygon 데이터가 있으면 첫 번째 요소의 구조 확인
                if len(edu_map.polygon) > 0:
                    # GeoJSON Polygon 형식: coordinates 필드가 있어야 함
                    polygon_item = edu_map.polygon[0]
                    assert hasattr(polygon_item, "coordinates"), (
                        "polygon 항목은 coordinates 필드를 가져야 함"
                    )
                    # coordinates는 3중 리스트 구조: [[[lng, lat], ...]]
                    assert isinstance(polygon_item.coordinates, list), "coordinates는 리스트여야 함"
                    if len(polygon_item.coordinates) > 0:
                        # 최소한 한 좌표 쌍이 있어야 함
                        assert len(polygon_item.coordinates[0]) > 0, "최소한 한 좌표 쌍이 있어야 함"


@pytest.mark.integration
class TestAsilVisitorStatsCrawlerIntegration:
    """AsilVisitorStatsCrawler 통합 테스트"""

    def _validate_visitor_stats_dto(self, stat) -> None:
        """AsilVisitorStatsDTO 데이터 검증 헬퍼 메서드"""
        from crawler.dto.asil_visitor_stats import AsilVisitorStatsDTO

        # 1. AsilVisitorStatsDTO 타입인지
        assert isinstance(stat, AsilVisitorStatsDTO), "AsilVisitorStatsDTO 타입이어야 함"

        # 2. key 필드가 존재하고 비어있지 않은지
        assert stat.key is not None, "key 필드가 존재해야 함"
        assert len(stat.key) > 0, "key 필드는 비어있지 않아야 함"

        # 3. company 필드가 존재하고 비어있지 않은지
        assert stat.company is not None, "company 필드가 존재해야 함"
        assert len(stat.company) > 0, "company 필드는 비어있지 않아야 함"

        # 4. lat, lng가 float로 변환 가능한지
        assert stat.lat is not None, "lat 필드가 존재해야 함"
        try:
            float(stat.lat)
        except ValueError:
            raise AssertionError(f"lat '{stat.lat}'는 float로 변환 가능해야 함")

        assert stat.lng is not None, "lng 필드가 존재해야 함"
        try:
            float(stat.lng)
        except ValueError:
            raise AssertionError(f"lng '{stat.lng}'는 float로 변환 가능해야 함")

        # 5. photo 필드가 있는지 (옵션 필드이지만 있는 경우 검증)
        if stat.photo:
            assert isinstance(stat.photo, str), "photo 필드는 문자열이어야 함"

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
            self._validate_visitor_stats_dto(stat)

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

        # 데이터가 있으면 DTO 검증
        if len(result) > 0:
            for stat in result:
                self._validate_visitor_stats_dto(stat)

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

        # 데이터가 있으면 DTO 타입 검증
        if len(result) > 0:
            from crawler.dto.asil_visitor_stats import AsilVisitorStatsDTO

            assert isinstance(result[0], AsilVisitorStatsDTO), "DTO 타입이어야 함"


@pytest.mark.integration
class TestAsilRedevelopCrawlerIntegration:
    """AsilRedevelopCrawler 통합 테스트"""

    def test_fetch_real_redevelop_data_for_gangnam(self):
        """강남구 좌표로 재개발 단지 정보를 실제로 가져옴"""
        from crawler.dto.asil_redevelop import AsilRedevelopDTO

        crawler = AsilRedevelopCrawler(
            s_lat=37.48,
            s_lng=127.00,
            e_lat=37.62,
            e_lng=127.15,
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 각 재개발 정보는 DTO여야 함
        for item in result:
            assert isinstance(item, AsilRedevelopDTO)

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

    def _validate_transfer_dto(self, transfer) -> None:
        """AsilTransferDTO 데이터 검증 헬퍼 메서드"""
        # 1. rank 필드가 0 이상인지
        assert transfer.rank >= 0, f"rank 필드는 0 이상이어야 함: {transfer.rank}"

        # 2. from_ 또는 to 필드가 존재하고 비어있지 않은지
        assert transfer.from_ or transfer.to, "from_ 또는 to 필드 중 하나 이상이 비어있지 않아야 함"
        if transfer.from_:
            assert isinstance(transfer.from_, str), "from_ 필드는 문자열이어야 함"
            assert len(transfer.from_) > 0, "from_ 필드는 비어있지 않아야 함"
        if transfer.to:
            assert isinstance(transfer.to, str), "to 필드는 문자열이어야 함"
            assert len(transfer.to) > 0, "to 필드는 비어있지 않아야 함"

        # 3. total 필드가 콤마 제거 후 int로 변환 가능한지
        if transfer.total:
            assert isinstance(transfer.total, str), "total 필드는 문자열이어야 함"
            total_cleaned = transfer.total.replace(",", "")
            try:
                int(total_cleaned)
            except ValueError:
                raise AssertionError(
                    f"total '{transfer.total}'는 콤마 제거 후 int로 변환 가능해야 함"
                )

        # 4. value 필드가 콤마 제거 후 int로 변환 가능한지
        if transfer.value:
            assert isinstance(transfer.value, str), "value 필드는 문자열이어야 함"
            value_cleaned = transfer.value.replace(",", "")
            try:
                int(value_cleaned)
            except ValueError:
                raise AssertionError(
                    f"value '{transfer.value}'는 콤마 제거 후 int로 변환 가능해야 함"
                )

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

        # 데이터가 있으면 상세 검증
        if len(result) > 0:
            for transfer in result:
                self._validate_transfer_dto(transfer)

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

        # 데이터가 있으면 상세 검증
        if len(result) > 0:
            for transfer in result:
                self._validate_transfer_dto(transfer)

    def test_transfer_data_validation(self):
        """인구 유동 데이터 필드 검증"""
        crawler = AsilTransferCrawler(
            area="11",
            start_year="2024",
            start_month="1",
            end_year="2024",
            end_month="12",
        )
        result = crawler.crawl()

        assert isinstance(result, list)

        # 데이터가 있는 경우 상세 검증 수행
        if len(result) > 0:
            # 첫 번째 데이터로 상세 검증
            transfer = result[0]

            # 1. rank 필드가 0 이상인지
            assert transfer.rank >= 0, f"rank 필드는 0 이상이어야 함: {transfer.rank}"

            # 2. from_ 또는 to 필드가 존재하고 비어있지 않은지
            assert transfer.from_ or transfer.to, "from_ 또는 to 필드 중 하나 이상이 존재해야 함"

            if transfer.from_:
                assert isinstance(transfer.from_, str), "from_ 필드는 문자열이어야 함"
                assert len(transfer.from_) > 0, "from_ 필드는 비어있지 않아야 함"

            if transfer.to:
                assert isinstance(transfer.to, str), "to 필드는 문자열이어야 함"
                assert len(transfer.to) > 0, "to 필드는 비어있지 않아야 함"

            # 3. total 필드가 콤마 제거 후 int로 변환 가능한지
            if transfer.total:
                assert isinstance(transfer.total, str), "total 필드는 문자열이어야 함"
                total_cleaned = transfer.total.replace(",", "")
                try:
                    int(total_cleaned)
                except ValueError:
                    raise AssertionError(
                        f"total '{transfer.total}'는 콤마 제거 후 int로 변환 가능해야 함"
                    )

            # 4. value 필드가 콤마 제거 후 int로 변환 가능한지
            if transfer.value:
                assert isinstance(transfer.value, str), "value 필드는 문자열이어야 함"
                value_cleaned = transfer.value.replace(",", "")
                try:
                    int(value_cleaned)
                except ValueError:
                    raise AssertionError(
                        f"value '{transfer.value}'는 콤마 제거 후 int로 변환 가능해야 함"
                    )

            # 모든 데이터에 대해 기본 검증
            for transfer in result:
                self._validate_transfer_dto(transfer)

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

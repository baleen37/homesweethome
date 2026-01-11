"""AsilCrawler 통합 테스트 - 실제 API 호출"""

import urllib.error

import pytest

from crawler.asil import (
    AsilAgentInfoCrawler,
    AsilAptListCrawler,
    AsilBunyangListCrawler,
    AsilBunyangMapCrawler,
    AsilDongInfoCrawler,
    AsilEducationMapCrawler,
    AsilListingCrawler,
    AsilMapSearchCrawler,
    AsilMoveinCrawler,
    AsilOfferDetailCrawler,
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
from crawler.dto.asil_dong_info import AsilDongInfoDTO
from crawler.dto.asil_offer import AsilOfferDTO, AsilOffersListResponse
from crawler.dto.asil_offer_detail import AsilOfferDetailResponse


@pytest.mark.integration
class TestAsilMoveinCrawlerIntegration:
    """AsilMoveinCrawler 통합 테스트"""

    def _validate_movein_dto(self, movein) -> None:
        """AsilMoveinDTO 데이터 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_movein import AsilMoveinDTO

        # 1. AsilMoveinDTO 타입인지
        assert isinstance(movein, AsilMoveinDTO), "AsilMoveinDTO 타입이어야 함"

        # 2. seq 필드가 존재하고 비어있지 않은지
        assert movein.seq, "seq 필드는 비어있지 않아야 함"

        # 3. name 필드가 존재하고 비어있지 않은지
        assert movein.name, "name 필드는 비어있지 않아야 함"

        # 4. location 필드가 존재하고 비어있지 않은지
        assert movein.location, "location 필드는 비어있지 않아야 함"

        # 5. movein_yyyymm 필드가 존재하고 비어있지 않은지
        assert movein.movein_yyyymm, "movein_yyyymm 필드는 비어있지 않아야 함"

        # 6. household 필드가 존재하고 비어있지 않은지
        assert movein.household, "household 필드는 비어있지 않아야 함"

        # 7. lat, lng가 float로 변환 가능한지
        assert movein.lat is not None, "lat 필드가 존재해야 함"
        try:
            float(movein.lat)
        except ValueError:
            raise AssertionError(f"lat '{movein.lat}'는 float로 변환 가능해야 함")

        assert movein.lng is not None, "lng 필드가 존재해야 함"
        try:
            float(movein.lng)
        except ValueError:
            raise AssertionError(f"lng '{movein.lng}'는 float로 변환 가능해야 함")

    def test_fetch_real_movein_seoul(self):
        """서울(11) 지역의 입주 예정 물량을 실제로 가져옴"""
        crawler = AsilMoveinCrawler(area="11", sy="2025", sm="1", ey="2025", em="12")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            for movein in result:
                self._validate_movein_dto(movein)

    def test_fetch_movein_with_date_range(self):
        """특정 기간의 입주 예정 물량을 가져옴"""
        crawler = AsilMoveinCrawler(
            area="11",
            sy="2025",
            sm="1",
            ey="2026",
            em="12",
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 DTO 검증
        if len(result) > 0:
            for movein in result:
                self._validate_movein_dto(movein)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilMoveinCrawler(area="11", sy="2025", sm="1", ey="2025", em="12")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
@pytest.mark.integration
class TestAsilAptListCrawlerIntegration:
    """AsilAptListCrawler 통합 테스트"""

    def _validate_apt_list_dto(self, apt) -> None:
        """AsilAptListDTO 데이터 필드 검증 헬퍼 메서드"""
        # 1. AsilAptListDTO 타입인지
        assert isinstance(apt, AsilAptListDTO), "AsilAptListDTO 타입이어야 함"

        # 2. seq 필드가 존재하고 비어있지 않은지
        assert apt.seq, "seq 필드는 비어있지 않아야 함"

        # 3. name 필드가 존재하고 비어있지 않은지
        assert apt.name, "name 필드는 비어있지 않아야 함"

        # 4. dong 필드가 존재하고 비어있지 않은지
        assert apt.dong, "dong 필드는 비어있지 않아야 함"

        # 5. dongname 필드가 존재하고 비어있지 않은지
        assert apt.dongname, "dongname 필드는 비어있지 않아야 함"

        # 6. build_year (movein alias) 필드가 존재하는지
        assert apt.build_year is not None, "build_year 필드는 비어있지 않아야 함"

        # 7. lat, lng가 float로 변환 가능한지 (있는 경우)
        if apt.lat:
            try:
                float(apt.lat)
            except (ValueError, TypeError):
                raise AssertionError(f"lat '{apt.lat}'는 float로 변환 가능해야 함")

        if apt.lng:
            try:
                float(apt.lng)
            except (ValueError, TypeError):
                raise AssertionError(f"lng '{apt.lng}'는 float로 변환 가능해야 함")

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
        self._validate_apt_list_dto(apt)

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

        # 모든 DTO 검증
        for apt in result:
            self._validate_apt_list_dto(apt)

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
        assert isinstance(dong, AsilDongInfoDTO)
        assert dong.dong  # dong 필드가 비어있지 않아야 함

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilSchoolInfoCrawlerIntegration:
    """AsilSchoolInfoCrawler 통합 테스트"""

    def _validate_school_dict(self, school) -> None:
        """학교 데이터(AsilSchoolInfoDTO) 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_school import AsilSchoolInfoDTO

        # 1. 각 아이템이 AsilSchoolInfoDTO인지
        assert isinstance(school, AsilSchoolInfoDTO), (
            "각 학교 정보는 AsilSchoolInfoDTO 타입이어야 함"
        )

        # 2. seq 필드가 비어있지 않은지
        assert school.seq, "seq 필드는 비어있지 않아야 함"

        # 3. name 필드가 비어있지 않은지
        assert school.name, "name 필드는 비어있지 않아야 함"

        # 4. addr 필드가 비어있지 않은지
        assert school.addr, "addr 필드는 비어있지 않아야 함"

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

    def _validate_population_dto(self, pop) -> None:
        """AsilPopulationDTO 데이터 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_population import AsilPopulationDTO

        # 1. AsilPopulationDTO 타입인지
        assert isinstance(pop, AsilPopulationDTO), "AsilPopulationDTO 타입이어야 함"

        # 2. seq 필드가 존재하고 비어있지 않은지
        assert pop.seq, "seq 필드는 비어있지 않아야 함"

        # 3. name 필드가 존재하고 비어있지 않은지
        assert pop.name, "name 필드는 비어있지 않어야 함"

        # 4. v1, v2, v3 필드가 int 타입인지 (파싱되어야 함)
        assert isinstance(pop.v1, int), f"v1 필드는 int여야 함: {type(pop.v1)}"
        assert isinstance(pop.v2, int), f"v2 필드는 int여야 함: {type(pop.v2)}"
        assert isinstance(pop.v3, int), f"v3 필드는 int여야 함: {type(pop.v3)}"

        # 5. v2_gap, v3_gap 필드가 int 타입인지
        assert isinstance(pop.v2_gap, int), f"v2_gap 필드는 int여야 함: {type(pop.v2_gap)}"
        assert isinstance(pop.v3_gap, int), f"v3_gap 필드는 int여야 함: {type(pop.v3_gap)}"

        # 6. v2_icon, v3_icon 필드가 str 타입인지
        assert isinstance(pop.v2_icon, str), f"v2_icon 필드는 str여야 함: {type(pop.v2_icon)}"
        assert isinstance(pop.v3_icon, str), f"v3_icon 필드는 str여야 함: {type(pop.v3_icon)}"

    def test_fetch_real_population_seoul(self):
        """서울(11)의 인구 통계를 실제로 가져옴"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            for pop in result:
                self._validate_population_dto(pop)

    def test_fetch_population_with_year_month(self):
        """특정 연도/월의 인구 통계를 가져옴"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            for pop in result:
                self._validate_population_dto(pop)

    def test_population_data_validation(self):
        """인구 데이터 필드 상세 검증"""
        crawler = AsilPopulationCrawler(area="11", year="2024", month="1", mode=1)
        result = crawler.crawl()

        assert isinstance(result, list)

        # 데이터가 있는 경우 상세 검증 수행
        if len(result) > 0:
            # 첫 번째 데이터로 상세 검증
            pop = result[0]

            # 1. v1 (총인구)이 양수여야 함
            assert pop.v1 > 0, f"총인구(v1)는 양수여야 함: {pop.v1}"

            # 2. v2_icon이 "up", "down", 또는 빈 문자열인지
            assert pop.v2_icon in ("up", "down", ""), (
                f"v2_icon은 'up', 'down', 또는 빈 문자열이어야 함: {pop.v2_icon}"
            )

            # 3. v3_icon이 "up", "down", 또는 빈 문자열인지
            assert pop.v3_icon in ("up", "down", ""), (
                f"v3_icon은 'up', 'down', 또는 빈 문자열이어야 함: {pop.v3_icon}"
            )

            # 모든 데이터에 대해 기본 검증
            for pop in result:
                self._validate_population_dto(pop)

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


@pytest.mark.integration
class TestAsilRankingCrawlerIntegration:
    """AsilRankingCrawler 통합 테스트"""

    def _validate_ranking_dto(self, ranking) -> None:
        """AsilRankingDTO 데이터 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_ranking import AsilRankingDTO

        # 1. AsilRankingDTO 타입인지
        assert isinstance(ranking, AsilRankingDTO), "AsilRankingDTO 타입이어야 함"

        # 2. idx 필드가 존재하고 비어있지 않은지
        assert ranking.idx, "idx 필드는 비어있지 않아야 함"

        # 3. seq 필드가 존재하고 비어있지 않은지
        assert ranking.seq, "seq 필드는 비어있지 않아야 함"

        # 4. name 필드가 존재하고 비어있지 않은지
        assert ranking.name, "name 필드는 비어있지 않아야 함"

        # 5. movein 필드가 존재하는지
        assert ranking.movein, "movein 필드는 비어있지 않아야 함"

        # 6. lat, lng가 float로 변환 가능한지
        assert ranking.lat is not None, "lat 필드가 존재해야 함"
        try:
            float(ranking.lat)
        except ValueError:
            raise AssertionError(f"lat '{ranking.lat}'는 float로 변환 가능해야 함")

        assert ranking.lng is not None, "lng 필드가 존재해야 함"
        try:
            float(ranking.lng)
        except ValueError:
            raise AssertionError(f"lng '{ranking.lng}'는 float로 변환 가능해야 함")

        # 7. price 필드가 존재하고 비어있지 않은지
        assert ranking.price, "price 필드는 비어있지 않어야 함"

        # 8. yyyymm 필드가 존재하고 비어있지 않은지
        assert ranking.yyyymm, "yyyymm 필드는 비어있지 않어야 함"

        # 9. m2 필드가 존재하고 비어있지 않은지
        assert ranking.m2, "m2 필드는 비어있지 않어야 함"

        # 10. floor 필드가 존재하고 비어있지 않은지
        assert ranking.floor, "floor 필드는 비어있지 않어야 함"

        # 11. addr 필드가 존재하고 비어있지 않은지
        assert ranking.addr, "addr 필드는 비어있지 않어야 함"

    def test_fetch_real_ranking_seoul_max_price(self):
        """서울(11) 지역의 최고가 아파트 순위를 실제로 가져옴"""
        crawler = AsilRankingCrawler(area="11", theme="max", deal="1")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 필수 필드 확인
        if len(result) > 0:
            for ranking in result:
                self._validate_ranking_dto(ranking)

    def test_fetch_ranking_with_date_range(self):
        """날짜 범위를 지정하여 순위 데이터를 가져옴"""
        crawler = AsilRankingCrawler(
            area="11",
            theme="max",
            deal="1",
            start_year="2024",
            start_month="1",
            start_day="1",
            end_year="2024",
            end_month="12",
            end_day="31",
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 DTO 검증
        if len(result) > 0:
            for ranking in result:
                self._validate_ranking_dto(ranking)

    def test_fetch_ranking_with_apt_name_filter(self):
        """아파트 이름 필터가 적용된 순위 데이터를 가져옴"""
        crawler = AsilRankingCrawler(area="11", theme="max", deal="1", apt_name="역삼자이")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 DTO 검증
        if len(result) > 0:
            for ranking in result:
                self._validate_ranking_dto(ranking)

    def test_ranking_data_validation(self):
        """순위 데이터 필드 상세 검증"""
        crawler = AsilRankingCrawler(area="11", theme="max", deal="1")
        result = crawler.crawl()

        assert isinstance(result, list)

        # 데이터가 있는 경우 상세 검증 수행
        if len(result) > 0:
            # 첫 번째 데이터로 상세 검증
            ranking = result[0]

            # 1. idx 필드 타입 검증
            assert isinstance(ranking.idx, str), "idx 필드는 문자열이어야 함"

            # 2. seq 필드 타입 검증
            assert isinstance(ranking.seq, str), "seq 필드는 문자열이어야 함"

            # 3. name 필드 타입 검증
            assert isinstance(ranking.name, str), "name 필드는 문자열이어야 함"

            # 4. price 필드에 "억"이 포함되어 있는지 (예: "290억")
            assert "억" in ranking.price, f"price 필드에 '억'이 포함되어야 함: {ranking.price}"

            # 5. yyyymm 필드 형식 검증 (예: "25년6월")
            assert "년" in ranking.yyyymm, f"yyyymm 필드에 '년'이 포함되어야 함: {ranking.yyyymm}"
            assert "월" in ranking.yyyymm, f"yyyymm 필드에 '월'이 포함되어야 함: {ranking.yyyymm}"

            # 6. m2 필드에 "평"이 포함되어 있는지 (예: "104평")
            assert "평" in ranking.m2, f"m2 필드에 '평'이 포함되어야 함: {ranking.m2}"

            # 7. floor 필드에 "층"이 포함되어 있는지 (예: "47층")
            assert "층" in ranking.floor, f"floor 필드에 '층'이 포함되어야 함: {ranking.floor}"

            # 모든 데이터에 대해 기본 검증
            for ranking in result:
                self._validate_ranking_dto(ranking)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilRankingCrawler(area="11", theme="max", deal="1")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilBunyangListCrawlerIntegration:
    """AsilBunyangListCrawler 통합 테스트

    Note: 분양 목록 API는 현재 활성화된 분양이 없을 수 있어 빈 응답을 반환할 수 있습니다.
    """

    def test_fetch_real_bunyang_list_seoul(self):
        """서울(11) 지역의 분양 목록을 실제로 가져옴"""
        from crawler.dto.asil_bunyang import AsilBunyangListDTO

        crawler = AsilBunyangListCrawler(area="11")
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있는 경우 검증 (API가 빈 응답을 반환할 수 있음)
        if len(result) > 0:
            # 각 분양 정보는 DTO여야 함
            for item in result:
                assert isinstance(item, AsilBunyangListDTO)

            # 첫 번째 항목의 필수 필드 확인
            first = result[0]
            # seq와 name 중 하나는 있어야 함
            assert first.seq or first.name

    def test_fetch_bunyang_list_with_filters(self):
        """필터가 적용된 분양 목록을 가져옴"""
        crawler = AsilBunyangListCrawler(
            area="11",
            type_value="1",
            page="1",
            total="50",
        )
        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

        # 데이터가 있으면 DTO 검증
        if len(result) > 0:
            from crawler.dto.asil_bunyang import AsilBunyangListDTO

            for item in result:
                assert isinstance(item, AsilBunyangListDTO)

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilBunyangListCrawler(area="11")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilMapSearchCrawlerIntegration:
    """AsilMapSearchCrawler 통합 테스트

    Note: 이 API는 현재 500 에러를 반환하므로 실제 API 호출 테스트는 skip 합니다.
    API가 정상화된 후 테스트를 활성화해야 합니다.
    """

    def test_crawl_with_coordinates(self):
        """실제 API로 지도 검색 테스트 - 현재 skip됨"""
        pytest.skip("API가 현재 500 에러를 반환하여 테스트 skip")

        crawler = AsilMapSearchCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
            zoom=13,
        )

        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)

    def test_crawl_with_all_parameters(self):
        """모든 파라미터로 실제 API 호출 테스트 - 현재 skip됨"""
        pytest.skip("API가 현재 500 에러를 반환하여 테스트 skip")

        crawler = AsilMapSearchCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
            zoom=13,
            code="11",
            building="apt",
            deal="123",
            household=50,
        )

        result = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(result, list)


@pytest.mark.integration
class TestAsilOfferDetailCrawlerIntegration:
    """AsilOfferDetailCrawler 통합 테스트"""

    def _validate_offer_detail_dto(self, offer) -> None:
        """AsilOfferDetailDTO 데이터 필드 검증 헬퍼 메서드"""
        from crawler.dto.asil_offer_detail import AsilOfferDetailDTO

        # 1. AsilOfferDetailDTO 타입인지
        assert isinstance(offer, AsilOfferDetailDTO), "AsilOfferDetailDTO 타입이어야 함"

        # 2. mm_uid 필드가 존재하고 비어있지 않은지
        assert offer.mm_uid, "mm_uid 필드는 비어있지 않아야 함"

        # 3. BLDNM 필드가 존재하고 비어있지 않은지
        assert offer.BLDNM, "BLDNM 필드는 비어있지 않아야 함"

        # 4. DEALTYPE_NM 필드가 존재하고 비어있지 않은지
        assert offer.DEALTYPE_NM, "DEALTYPE_NM 필드는 비어있지 않아야 함"

        # 5. MAP_X, MAP_Y가 float로 변환 가능한지 (있는 경우)
        if offer.MAP_X:
            try:
                float(offer.MAP_X)
            except (ValueError, TypeError):
                raise AssertionError(f"MAP_X '{offer.MAP_X}'는 float로 변환 가능해야 함")

        if offer.MAP_Y:
            try:
                float(offer.MAP_Y)
            except (ValueError, TypeError):
                raise AssertionError(f"MAP_Y '{offer.MAP_Y}'는 float로 변환 가능해야 함")

    def test_fetch_real_offer_detail(self):
        """실제 매물(mm_uid="33534599")의 상세 정보를 가져옴"""
        from crawler.dto.asil_offer_detail import AsilOfferDetailResponse

        crawler = AsilOfferDetailCrawler(mm_uid="33534599")
        result = crawler.crawl()

        # 결과가 AsilOfferDetailResponse여야 함
        assert isinstance(result, AsilOfferDetailResponse)

        # mm_json 필드가 리스트여야 함
        assert isinstance(result.mm_json, list)

        # 매물 상세 정보가 있어야 함
        assert len(result.mm_json) > 0

        # 각 매물 상세 정보에 필수 필드가 있어야 함
        offer = result.mm_json[0]
        self._validate_offer_detail_dto(offer)

    def test_fetch_offer_detail_includes_admin_cost(self):
        """매물 상세 정보에 관리비 정보가 포함되어야 함"""
        crawler = AsilOfferDetailCrawler(mm_uid="33534599")
        result = crawler.crawl()

        assert isinstance(result, AsilOfferDetailResponse)

        # 관리비 정보가 있는지 확인 (있는 경우 검증)
        if result.administrationCostInfo:
            assert result.administrationCostInfo.chargeCodeType
            assert result.administrationCostInfo.chargeCriteriaCode

    def test_fetch_offer_detail_includes_related_listings(self):
        """매물 상세 정보에 관련 매물 리스트가 포함되어야 함"""
        crawler = AsilOfferDetailCrawler(mm_uid="33534599")
        result = crawler.crawl()

        assert isinstance(result, AsilOfferDetailResponse)

        # 관련 매물 리스트가 리스트인지 확인
        assert isinstance(result.mm_json_list, list)

        # 관련 매물이 있는 경우 검증
        if len(result.mm_json_list) > 0:
            related = result.mm_json_list[0]
            assert related.mm_uid
            assert related.BLDNM

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        crawler = AsilOfferDetailCrawler(mm_uid="33534599")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, AsilOfferDetailResponse)
        assert isinstance(result.mm_json, list)


@pytest.mark.integration
class TestAsilBunyangMapCrawlerIntegration:
    """AsilBunyangMapCrawler 통합 테스트"""

    def test_fetch_real_bunyang_map_seoul(self):
        """서울(11) 지역의 분양 지도 정보를 실제로 가져옴"""
        from crawler.dto.asil_bunyang_map import AsilBunyangMapResponse

        crawler = AsilBunyangMapCrawler(sido="11", code="11")
        result = crawler.crawl()

        # 결과가 AsilBunyangMapResponse여야 함
        assert isinstance(result, AsilBunyangMapResponse)

        # sigu 필드가 리스트여야 함
        assert isinstance(result.sigu, list)

        # 서울 지역 데이터가 있어야 함
        assert len(result.sigu) > 0

        # 첫 번째 시도 정보 검증
        sigu = result.sigu[0]
        assert sigu.seq
        assert sigu.name
        assert sigu.fullname
        assert sigu.lat
        assert sigu.lng

        # 통계 필드 확인
        assert result.schedule
        assert result.progress
        assert result.done

    def test_fetch_bunyang_map_with_coordinates(self):
        """좌표 범위를 지정하여 분양 지도 정보를 가져옴"""
        from crawler.dto.asil_bunyang_map import AsilBunyangMapResponse

        crawler = AsilBunyangMapCrawler(
            sido="11",
            code="11",
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        result = crawler.crawl()

        assert isinstance(result, AsilBunyangMapResponse)
        assert isinstance(result.sigu, list)

    def test_fetch_bunyang_map_with_type_filter(self):
        """분양 유형 필터가 적용된 분양 지도 정보를 가져옴"""
        from crawler.dto.asil_bunyang_map import AsilBunyangMapResponse

        crawler = AsilBunyangMapCrawler(
            sido="11",
            code="11",
            type_value="1",
        )
        result = crawler.crawl()

        assert isinstance(result, AsilBunyangMapResponse)
        assert isinstance(result.sigu, list)

    def test_bunyang_map_data_validation(self):
        """분양 지도 데이터 필드 검증"""
        from crawler.dto.asil_bunyang_map import AsilBunyangMapResponse

        crawler = AsilBunyangMapCrawler(sido="11", code="11")
        result = crawler.crawl()

        assert isinstance(result, AsilBunyangMapResponse)

        # 모든 시도 정보 검증
        for sigu in result.sigu:
            # seq 필드가 비어있지 않아야 함
            assert sigu.seq, "seq 필드는 비어있지 않아야 함"

            # name 필드가 비어있지 않아야 함
            assert sigu.name, "name 필드는 비어있지 않아야 함"

            # fullname 필드가 비어있지 않아야 함
            assert sigu.fullname, "fullname 필드는 비어있지 않아야 함"

            # lat, lng가 float로 변환 가능해야 함
            assert sigu.lat, "lat 필드가 존재해야 함"
            try:
                float(sigu.lat)
            except ValueError:
                raise AssertionError(f"lat '{sigu.lat}'는 float로 변환 가능해야 함")

            assert sigu.lng, "lng 필드가 존재해야 함"
            try:
                float(sigu.lng)
            except ValueError:
                raise AssertionError(f"lng '{sigu.lng}'는 float로 변환 가능해야 함")

            # zoom 필드가 존재해야 함
            assert sigu.zoom, "zoom 필드는 비어있지 않아야 함"

            # subtitle 필드는 옵션 (빈 문자열 가능)
            assert isinstance(sigu.subtitle, str), "subtitle 필드는 문자열이어야 함"

    def test_crawl_template_method_works(self):
        """crawl() 템플릿 메서드가 올바르게 작동하는지 확인"""
        from crawler.dto.asil_bunyang_map import AsilBunyangMapResponse

        crawler = AsilBunyangMapCrawler(sido="11", code="11")

        result = crawler.crawl()

        # 결과가 파싱된 데이터여야 함
        assert isinstance(result, AsilBunyangMapResponse)
        assert isinstance(result.sigu, list)

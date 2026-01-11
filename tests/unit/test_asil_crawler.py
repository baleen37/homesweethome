"""AsilCrawler 단위 테스트"""

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
from crawler.dto.asil_population import AsilPopulationDTO
from crawler.dto.asil_price_index import (
    AsilPriceIndexRegionDTO,
    AsilPriceIndexSummaryDTO,
)
from crawler.dto.asil_ranking import AsilRankingDTO
from crawler.dto.asil_transfer import AsilTransferDTO


class TestAsilAptListCrawler:
    """AsilAptListCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilAptListCrawler, BaseCrawler)

    def test_requires_dong_code_parameter(self):
        """dong_code 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilAptListCrawler()

    def test_accepts_dong_code_parameter(self):
        """dong_code 파라미터를 받을 수 있어야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100")
        assert crawler.dong_code == "1168010100"

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/data_apt_list.jsp")
        assert "dong=1168010100" in url

    def test_get_url_includes_optional_parameters(self):
        """선택적 파라미터를 URL에 포함해야 함"""
        crawler = AsilAptListCrawler(
            dong_code="1168010100",
            building_type="apt",
            min_household=50,
            order=0,
        )
        url = crawler.get_url()
        assert "dong=1168010100" in url
        assert "building=apt" in url
        assert "household=50" in url
        assert "order=0" in url

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilAptListDTO]를 반환해야 함"""
        from crawler.dto.asil_apt_list import AsilAptListDTO

        crawler = AsilAptListCrawler(dong_code="1168010100")

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "seq": "20340925",
                "name": "역삼자이",
                "dong": "1168010100",
                "dongname": "역삼동",
                "build_year": "2016",
                "household": "408",
                "dong_count": "3",
                "address": "서울시 강남구 역삼동",
                "maemul_count": "22"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilAptListDTO)
        assert result[0].seq == "20340925"
        assert result[0].name == "역삼자이"


class TestAsilTradePriceCrawler:
    """AsilTradePriceCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilTradePriceCrawler, BaseCrawler)

    def test_requires_apt_code_parameter(self):
        """apt_code 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilTradePriceCrawler()

    def test_accepts_required_parameters(self):
        """필수 파라미터를 받을 수 있어야 함"""
        crawler = AsilTradePriceCrawler(
            apt_code="20340925",
            sido_code="11",
            area_m2=114,
        )
        assert crawler.apt_code == "20340925"
        assert crawler.sido_code == "11"
        assert crawler.area_m2 == 114

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilTradePriceCrawler(
            apt_code="20340925",
            sido_code="11",
            area_m2=114,
        )
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/apt_price_m2_mjw_newver_6.jsp")
        assert "seq=20340925" in url
        assert "sido=11" in url
        assert "m2=114" in url


class TestAsilSchoolInfoCrawler:
    """AsilSchoolInfoCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilSchoolInfoCrawler, BaseCrawler)

    def test_requires_school_type_parameter(self):
        """school_type 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilSchoolInfoCrawler()

    def test_accepts_school_type_parameter(self):
        """school_type 파라미터를 받을 수 있어야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary")
        assert crawler.school_type == "elementary"

    def test_accepts_optional_area_code(self):
        """선택적 area_code 파라미터를 받을 수 있어야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary", area_code="11680")
        assert crawler.school_type == "elementary"
        assert crawler.area_code == "11680"

    def test_accepts_optional_bounds(self):
        """선택적 bounds 파라미터를 받을 수 있어야 함"""
        bounds = {"s_lat": "37.5", "s_lng": "127.0", "e_lat": "37.6", "e_lng": "127.1"}
        crawler = AsilSchoolInfoCrawler(school_type="middle", bounds=bounds)
        assert crawler.school_type == "middle"
        assert crawler.bounds == bounds

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/data_school_list_2024.jsp")
        assert "type1=2" in url

    def test_get_url_includes_area_code(self):
        """area_code 파라미터를 URL에 포함해야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary", area_code="11680")
        url = crawler.get_url()
        assert "type1=2" in url
        assert "area=11680" in url

    def test_get_url_includes_bounds(self):
        """bounds 파라미터를 URL에 포함해야 함"""
        bounds = {"s_lat": "37.5", "s_lng": "127.0", "e_lat": "37.6", "e_lng": "127.1"}
        crawler = AsilSchoolInfoCrawler(school_type="middle", bounds=bounds)
        url = crawler.get_url()
        assert "type1=3" in url
        assert "s_lat=37.5" in url
        assert "s_lng=127.0" in url
        assert "e_lat=37.6" in url
        assert "e_lng=127.1" in url

    def test_get_url_middle_school_type(self):
        """중학교 타입이 올바른 파라미터로 변환되어야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="middle")
        url = crawler.get_url()
        assert "type1=3" in url

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary")

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "seq": "B100001394",
                "name": "경희초등학교",
                "name2": "경희초",
                "addr": "서울시 강남구 ..."
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["seq"] == "B100001394"
        assert result[0]["name"] == "경희초등학교"

    def test_parse_handles_empty_response(self):
        """parse()는 빈 응답을 처리할 수 있어야 함"""
        crawler = AsilSchoolInfoCrawler(school_type="elementary")
        result = crawler.parse("[]")
        assert result == []

    def test_referer_header_included(self):
        """Referer 헤더가 포함되어야 함"""
        from unittest.mock import Mock, patch

        crawler = AsilSchoolInfoCrawler(school_type="elementary")

        # Request 객체 생성 검증을 위해 mock 사용
        with (
            patch("crawler.asil.Request") as mock_request,
            patch("crawler.asil.urlopen") as mock_urlopen,
        ):
            # mock_response 설정
            mock_response = Mock()
            mock_response.read.return_value = b"[]"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            crawler.fetch("https://example.com")

            # Request가 Referer 헤더와 함께 호출되었는지 확인
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            headers = call_args[1]["headers"]
            assert "Referer" in headers
            assert headers["Referer"] == "https://asil.kr/asil/index.jsp"


class TestAsilTrafficCrawler:
    """AsilTrafficCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilTrafficCrawler, BaseCrawler)

    def test_requires_coordinate_parameters(self):
        """좌표 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilTrafficCrawler()

    def test_accepts_required_parameters(self):
        """필수 파라미터를 받을 수 있어야 함"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )
        assert crawler.s_lat == 37.514575
        assert crawler.s_lng == 127.044555
        assert crawler.e_lat == 37.504575
        assert crawler.e_lng == 127.054555

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/json/data_traffic_naver.jsp")
        assert "s_lat=37.514575" in url
        assert "s_lng=127.044555" in url
        assert "e_lat=37.504575" in url
        assert "e_lng=127.054555" in url

    def test_get_url_includes_optional_parameters(self):
        """선택적 파라미터를 URL에 포함해야 함"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
            zoom=13,
            traffic_types="1,2,3,4",
            year_min=2021,
            year_max=2027,
        )
        url = crawler.get_url()
        assert "zoom=13" in url
        assert "traffic=1%2C2%2C3%2C4" in url
        assert "t_min=2021" in url
        assert "t_max=2027" in url

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
        crawler = AsilTrafficCrawler(
            s_lat=37.514575,
            s_lng=127.044555,
            e_lat=37.504575,
            e_lng=127.054555,
        )

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "key": "G000002",
                "title": "GTX B",
                "lat": "37.514575",
                "lng": "127.044555",
                "s_year": "2024",
                "e_year": "2028"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["key"] == "G000002"
        assert result[0]["title"] == "GTX B"


class TestAsilDongInfoCrawler:
    """AsilDongInfoCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilDongInfoCrawler, BaseCrawler)

    def test_requires_apt_code_parameter(self):
        """apt_code 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilDongInfoCrawler()

    def test_accepts_apt_code_parameter(self):
        """apt_code 파라미터를 받을 수 있어야 함"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")
        assert crawler.apt_code == "20340925"

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/data_apt_dong.jsp")
        assert "apt=20340925" in url

    def test_parse_handles_leading_newlines(self):
        """parse()는 앞의 \r\n을 제거하고 JSON을 파싱해야 함"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")

        # 실제 API 응답 형식: 앞에 \r\n 8개가 선행
        mock_response = (
            "\r\n\r\n\r\n\r\n\r\n\r\n\r\n"
            + '{"data": [{"dong": "101"}, {"dong": "102"}], "v": "1"}'
        )

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["dong"] == "101"
        assert result[1]["dong"] == "102"

    def test_parse_returns_data_field(self):
        """parse()는 응답의 data 필드를 반환해야 함"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")

        mock_response = "\r\n\r\n\r\n\r\n\r\n\r\n\r\n" + '{"data": [{"dong": "101"}], "v": "1"}'

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert result[0]["dong"] == "101"

    def test_parse_handles_empty_data(self):
        """parse()는 빈 데이터를 올바르게 처리해야 함"""
        crawler = AsilDongInfoCrawler(apt_code="20340925")

        mock_response = "\r\n\r\n\r\n\r\n\r\n\r\n\r\n" + '{"data": [], "v": "1"}'

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 0


class TestAsilEducationMapCrawler:
    """AsilEducationMapCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilEducationMapCrawler, BaseCrawler)

    def test_requires_coordinate_parameters(self):
        """좌표 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilEducationMapCrawler()

    def test_accepts_coordinate_parameters(self):
        """좌표 파라미터를 받을 수 있어야 함"""
        crawler = AsilEducationMapCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        assert crawler.s_lat == 37.5
        assert crawler.s_lng == 127.0
        assert crawler.e_lat == 37.6
        assert crawler.e_lng == 127.1

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilEducationMapCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/json/data_education.jsp")
        assert "s_lat=37.5" in url
        assert "s_lng=127.0" in url
        assert "e_lat=37.6" in url
        assert "e_lng=127.1" in url

    def test_get_url_includes_zoom_parameter(self):
        """get_url()에 zoom 파라미터가 포함되어야 함"""
        crawler = AsilEducationMapCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
            zoom=15,
        )
        url = crawler.get_url()
        assert "zoom=15" in url

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilEducationMapDTO]를 반환해야 함"""
        from crawler.dto.asil_education_map import AsilEducationMapDTO

        crawler = AsilEducationMapCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )

        # GeoJSON polygon 형식의 응답
        mock_response = """
        [
            {
                "title": "학원수 72개",
                "lat": "37.592237718",
                "lng": "127.01496888",
                "polygon": [
                    {
                        "coordinates": [
                            [
                                [127.00671704, 37.589269706],
                                [127.01486990, 37.592719761]
                            ]
                        ]
                    }
                ]
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilEducationMapDTO)
        assert result[0].title == "학원수 72개"
        assert result[0].polygon is not None


class TestAsilVisitorStatsCrawler:
    """AsilVisitorStatsCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilVisitorStatsCrawler, BaseCrawler)

    def test_requires_coordinate_parameters(self):
        """좌표 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilVisitorStatsCrawler()

    def test_accepts_required_parameters(self):
        """필수 파라미터를 받을 수 있어야 함"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        assert crawler.s_lat == 37.5
        assert crawler.s_lng == 127.0
        assert crawler.e_lat == 37.6
        assert crawler.e_lng == 127.1

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/json/data_member.jsp")
        assert "os=pc" in url
        assert "user=1" in url
        assert "s_lat=37.5" in url
        assert "s_lng=127.0" in url
        assert "e_lat=37.6" in url
        assert "e_lng=127.1" in url

    def test_get_url_includes_zoom_parameter(self):
        """get_url()에 zoom 파라미터가 포함되어야 함"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
            zoom=15,
        )
        url = crawler.get_url()
        assert "zoom=15" in url

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "key": "-19917",
                "company": "중개법인명",
                "lat": "37.512798",
                "lng": "127.050655",
                "photo": "/photo/member/-19917.png"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["key"] == "-19917"
        assert result[0]["lat"] == "37.512798"
        assert result[0]["lng"] == "127.050655"

    def test_parse_handles_empty_response(self):
        """parse()는 빈 응답을 처리할 수 있어야 함"""
        crawler = AsilVisitorStatsCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        result = crawler.parse("[]")
        assert result == []


class TestAsilRedevelopCrawler:
    """AsilRedevelopCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilRedevelopCrawler, BaseCrawler)

    def test_requires_coordinate_parameters(self):
        """좌표 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilRedevelopCrawler()

    def test_accepts_required_parameters(self):
        """필수 파라미터를 받을 수 있어야 함"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        assert crawler.s_lat == 37.5
        assert crawler.s_lng == 127.0
        assert crawler.e_lat == 37.6
        assert crawler.e_lng == 127.1

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/json/data_redevelop.jsp")
        assert "os=pc" in url
        assert "user=1" in url
        assert "s_lat=37.5" in url
        assert "s_lng=127.0" in url
        assert "e_lat=37.6" in url
        assert "e_lng=127.1" in url

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )

        # Mock JSON 응답 (재개발 구역 정보)
        mock_response = """
        [
            {
                "name": "역삼동 재개발 구역",
                "status": "진행 중",
                "s_lat": "37.5",
                "s_lng": "127.0"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["name"] == "역삼동 재개발 구역"

    def test_parse_handles_empty_response(self):
        """parse()는 빈 응답을 처리할 수 있어야 함"""
        crawler = AsilRedevelopCrawler(
            s_lat=37.5,
            s_lng=127.0,
            e_lat=37.6,
            e_lng=127.1,
        )
        result = crawler.parse("[]")
        assert result == []


class TestAsilListingCrawler:
    """AsilListingCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilListingCrawler, BaseCrawler)

    def test_requires_apt_code_parameter(self):
        """apt_code 파라미터가 필수여야 함"""
        with pytest.raises(TypeError):
            AsilListingCrawler()

    def test_accepts_apt_code_parameter(self):
        """apt_code 파라미터를 받을 수 있어야 함"""
        crawler = AsilListingCrawler(apt_code="20340925")
        assert crawler.apt_code == "20340925"

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilListingCrawler(apt_code="20340925")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/data_apt_list.jsp")

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilAptListDTO]를 반환해야 함"""
        crawler = AsilListingCrawler(apt_code="20340925")

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "seq": "20340925",
                "name": "역삼자이",
                "dong": "1168010100",
                "dongname": "역삼동",
                "offer": "매물 5건",
                "household": "408"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilAptListDTO)
        assert result[0].seq == "20340925"
        assert result[0].name == "역삼자이"

    def test_parse_handles_empty_response(self):
        """parse()는 빈 응답을 처리할 수 있어야 함"""
        crawler = AsilListingCrawler(apt_code="20340925")
        result = crawler.parse("[]")
        assert result == []

    def test_parse_filters_listings_with_offer(self):
        """parse()는 매물이 있는 항목만 필터링해야 함"""
        crawler = AsilListingCrawler(apt_code="20340925")

        # 매물 유무가 혼합된 응답
        mock_response = """
        [
            {"seq": "1", "name": "A", "dong": "123", "dongname": "test", "offer": "매물 2건"},
            {"seq": "2", "name": "B", "dong": "123", "dongname": "test", "offer": ""},
            {"seq": "3", "name": "C", "dong": "123", "dongname": "test", "offer": "매물 1건"},
            {"seq": "4", "name": "D", "dong": "123", "dongname": "test", "offer": ""}
        ]
        """

        result = crawler.parse(mock_response)
        # 매물이 있는 항목만 반환
        assert len(result) == 2
        assert result[0].seq == "1"
        assert result[1].seq == "3"


class TestAsilRankingCrawler:
    """AsilRankingCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilRankingCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilRankingCrawler(area="11", theme="max")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/app/data/data_ranking.jsp")
        assert "area=11" in url
        assert "theme=max" in url

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilRankingDTO]를 반환해야 함"""
        crawler = AsilRankingCrawler(area="11", theme="max")

        mock_response = """
        [
            {
                "idx": "1",
                "seq": "20414401",
                "name": "아크로서울포레스트",
                "movein": "2021",
                "lat": "37.544463790",
                "lng": "127.04384744",
                "price": "290억",
                "yyyymm": "25년6월",
                "m2": "104평",
                "floor": "47층",
                "addr": "서울 성동구 성수동"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilRankingDTO)
        assert result[0].idx == "1"
        assert result[0].name == "아크로서울포레스트"


class TestAsilPriceIndexCrawler:
    """AsilPriceIndexCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilPriceIndexCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilPriceIndexCrawler(area="11", deal_mode="M")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/rts_m/contents/inc/data_price.jsp")
        assert "area=11" in url
        assert "dealmode=M" in url

    def test_parse_returns_list_of_responses(self):
        """parse()는 지역 데이터와 요약 객체를 반환해야 함"""
        crawler = AsilPriceIndexCrawler(area="11", deal_mode="M")

        mock_response = """
        [
            {
                "seq": "11",
                "name": "서울",
                "v1": "104.0",
                "v2": "104.3",
                "v3": "104.5",
                "v2_gap": "0.3",
                "v3_gap": "0.2",
                "v2_icon": "up",
                "v3_icon": "up"
            },
            {
                "min": "-0.0",
                "max": "0.5"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], AsilPriceIndexRegionDTO)
        assert isinstance(result[1], AsilPriceIndexSummaryDTO)
        assert result[0].name == "서울"
        assert result[1].min == "-0.0"


class TestAsilOffersListCrawler:
    """AsilOffersListCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilOffersListCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilOffersListCrawler(bdong_code="11", page=1)
        url = crawler.get_url()
        assert url.startswith("https://realty.asil.kr/api_asil/offers_list.aspx")
        assert "bdong_cd=11" in url
        assert "now_page=1" in url

    def test_parse_returns_offers_list_response(self):
        """parse()는 AsilOffersListResponse를 반환해야 함"""
        crawler = AsilOffersListCrawler(bdong_code="11", page=1)

        mock_response = """
        {
            "list_result": [
                {
                    "mm_uid": "33534599",
                    "RLSTTYPE_CD": "A01",
                    "RLSTTYPE_NM": "아파트",
                    "MAP_X": "126.9973225",
                    "MAP_Y": "37.5068070",
                    "BLDNM": "래미안원베일리",
                    "DEALTYPE_CD": "B01",
                    "DEALTYPE_NM": "전세",
                    "WRRNT_AMT": "230,000",
                    "BRKG_NM": "중개사",
                    "BRKG_TEL": "02-1234-5678",
                    "CITY_NM": "서울특별시",
                    "GUN_NM": "서초구",
                    "BDONG_NM": "반포동",
                    "DONG_NM": "118",
                    "SPLY_SPC": "112.65",
                    "EXCLS_SPC": "84.98",
                    "CTRT_SPC": "112.65",
                    "TOT_FLR_CNT": "33",
                    "CORES_FLR_CNT": "0",
                    "spc_v1": "112.65",
                    "spc_v2": "84.98",
                    "DEAL_AMT": "0",
                    "LEASE_AMT": "0",
                    "FETR_DESC": "테스트",
                    "premium_price": "0",
                    "prcl_price": "0",
                    "grnd_spc": "",
                    "TOT_SPC": "",
                    "CNST_SPC": "",
                    "SUB_RLSTTYPE_CD": "아파트",
                    "SUB_RLSTTYPE_NM": "아파트",
                    "CORES_FLR_CNT_NM": "저",
                    "UNDER_FLR": "",
                    "flr_dp_mthd_cd": "2",
                    "PHTO_PATH": "",
                    "SVC_DATE_STRT": "26.01.11",
                    "MAP_LOC_YN": "",
                    "PRCS_CD": "4",
                    "PRTN_UID": "44902",
                    "pre_flag": "0",
                    "f_option": "0",
                    "f_push": "0",
                    "user_id": "-20040",
                    "now_page": "1",
                    "GU_NM": ""
                }
            ]
        }
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, AsilOffersListResponse)
        assert len(result.list_result) == 1
        assert isinstance(result.list_result[0], AsilOfferDTO)
        assert result.list_result[0].mm_uid == "33534599"
        assert result.list_result[0].BLDNM == "래미안원베일리"


class TestAsilAgentInfoCrawler:
    """AsilAgentInfoCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilAgentInfoCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilAgentInfoCrawler(user_id="-20040")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/json/agentInfo.jsp")
        assert "user=-20040" in url

    def test_parse_returns_agent_info_response(self):
        """parse()는 AsilAgentInfoResponse를 반환해야 함"""
        crawler = AsilAgentInfoCrawler(user_id="-20040")

        mock_response = """
        {
            "result": true,
            "agent": {
                "seq": "-20040",
                "company": "테스트중개사",
                "name": "홍길동",
                "tel": "010-1234-5678",
                "cel": "02-1234-5678",
                "addr": "서울시 강남구",
                "bizNo": "123-45-67890",
                "lat": "37.5",
                "lng": "127.0",
                "photo": "/photo/member/-20040.png"
            }
        }
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, AsilAgentInfoResponse)
        assert result.result is True
        assert isinstance(result.agent, AsilAgentDTO)
        assert result.agent.name == "홍길동"
        assert result.agent.company == "테스트중개사"


class TestAsilPopulationCrawler:
    """AsilPopulationCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilPopulationCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilPopulationCrawler(area="11")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/rts_m/contents/inc/data_population.jsp")
        assert "area=11" in url

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilPopulationDTO]를 반환해야 함"""
        crawler = AsilPopulationCrawler(area="11")

        mock_response = """
        [
            {
                "seq": "11",
                "name": "서울",
                "v1": "9390,925명",
                "v2": "9335,495명",
                "v3": "9305,678명",
                "v2_gap": "55,430명",
                "v3_gap": "29,817명",
                "v2_icon": "down",
                "v3_icon": "down"
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilPopulationDTO)
        assert result[0].name == "서울"
        assert result[0].v1 == "9390,925명"


class TestAsilTransferCrawler:
    """AsilTransferCrawler 단위 테스트"""

    def test_inherits_from_base_crawler(self):
        """BaseCrawler를 상속받아야 함"""
        from crawler.base import BaseCrawler

        assert issubclass(AsilTransferCrawler, BaseCrawler)

    def test_get_url_returns_correct_endpoint(self):
        """get_url()이 올바른 API 엔드포인트를 반환해야 함"""
        crawler = AsilTransferCrawler(area="11")
        url = crawler.get_url()
        assert url.startswith("https://asil.kr/rts_m/contents/inc/data_transfer.jsp")
        assert "area=11" in url

    def test_parse_returns_list_of_dtos(self):
        """parse()는 list[AsilTransferDTO]를 반환해야 함"""
        crawler = AsilTransferCrawler(area="11")

        mock_response = """
        [
            {
                "rank": 1,
                "from": "서울",
                "to": "경기 광명시",
                "total": "2,891",
                "value": "451",
                "color": ""
            }
        ]
        """

        result = crawler.parse(mock_response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], AsilTransferDTO)
        assert result[0].rank == 1
        assert result[0].from_ == "서울"
        assert result[0].to == "경기 광명시"

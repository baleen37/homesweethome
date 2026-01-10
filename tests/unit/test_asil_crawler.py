"""AsilCrawler 단위 테스트"""

import pytest

from crawler.asil import (
    AsilAptListCrawler,
    AsilDongInfoCrawler,
    AsilEducationMapCrawler,
    AsilSchoolInfoCrawler,
    AsilTradePriceCrawler,
    AsilTrafficCrawler,
)


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

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100")

        # Mock JSON 응답 (실제 API 응답 형식)
        mock_response = """
        [
            {
                "seq": "20340925",
                "name": "역삼자이",
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
        assert isinstance(result[0], dict)
        assert result[0]["seq"] == "20340925"
        assert result[0]["name"] == "역삼자이"


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

    def test_parse_returns_list_of_dicts(self):
        """parse()는 list[dict]를 반환해야 함"""
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
        assert isinstance(result[0], dict)
        assert result[0]["title"] == "학원수 72개"
        assert "polygon" in result[0]

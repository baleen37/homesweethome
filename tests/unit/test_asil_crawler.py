"""AsilCrawler 단위 테스트"""

import pytest

from crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler


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

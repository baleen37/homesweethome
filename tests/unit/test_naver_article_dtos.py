"""네이버 매물 Article DTO 유닛 테스트

jissp/naver-land-crawler ArticleItem 기반 DTO 모델 테스트입니다.
"""

import pytest

from crawler.dto.naver_article import (
    NaverArticleDetailDTO,
    NaverArticleItemDTO,
    NaverArticleKeyDTO,
    NaverComplexDTO,
)


class TestNaverArticleItemDTO:
    """NaverArticleItemDTO 테스트"""

    def test_article_item_dto_basic_fields(self):
        """기본 필드 생성 및 검증"""
        dto = NaverArticleItemDTO(
            atcl_no="12345",
            cortar_no="1156010100",
            atcl_nm="테스트 매물",
            atcl_stat_cd="A01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
        )

        assert dto.atcl_no == "12345"
        assert dto.cortar_no == "1156010100"
        assert dto.atcl_nm == "테스트 매물"
        assert dto.atcl_stat_cd == "A01"
        assert dto.rlet_tp_cd == "A01"
        assert dto.rlet_tp_nm == "아파트"
        assert dto.trad_tp_cd == "A1"
        assert dto.trad_tp_nm == "매매"

    def test_article_item_dto_optional_fields(self):
        """선택적 필드 None 허용"""
        dto = NaverArticleItemDTO(
            atcl_no="12345",
            cortar_no="1156010100",
            atcl_nm="테스트 매물",
            atcl_stat_cd="A01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
            prc=None,
            rent_prc=None,
            direction=None,
            atcl_cfm_ymd=None,
            lat=None,
            lng=None,
        )

        assert dto.prc is None
        assert dto.rent_prc is None
        assert dto.direction is None
        assert dto.atcl_cfm_ymd is None
        assert dto.lat is None
        assert dto.lng is None

    def test_article_item_dto_from_dict(self):
        """dict에서 DTO 생성"""
        data = {
            "atcl_no": "67890",
            "cortar_no": "1168010500",
            "atcl_nm": "강남 아파트",
            "atcl_stat_cd": "A02",
            "rlet_tp_cd": "A02",
            "rlet_tp_nm": "오피스텔",
            "trad_tp_cd": "B1",
            "trad_tp_nm": "전세",
            "prc": 50000,
            "rent_prc": None,
            "flr_info": "7/10",
            "spc1": "84.94",
            "spc2": "59.95",
            "direction": "남향",
            "atcl_cfm_ymd": "2024.01.15",
            "lat": 37.5142,
            "lng": 127.0628,
            "atcl_fetr_desc": "역세권",
            "tag_list": ["역세권", "신축"],
            "bild_nm": "101동",
        }

        dto = NaverArticleItemDTO(**data)

        assert dto.atcl_no == "67890"
        assert dto.prc == 50000
        assert dto.flr_info == "7/10"
        assert dto.spc1 == "84.94"
        assert dto.spc2 == "59.95"
        assert dto.direction == "남향"
        assert dto.lat == 37.5142
        assert dto.lng == 127.0628
        assert dto.atcl_fetr_desc == "역세권"
        assert dto.tag_list == ["역세권", "신축"]
        assert dto.bild_nm == "101동"

    def test_article_item_dto_defaults(self):
        """기본값 필드 확인"""
        dto = NaverArticleItemDTO(
            atcl_no="12345",
            cortar_no="1156010100",
            atcl_nm="테스트",
            atcl_stat_cd="A01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
        )

        assert dto.flr_info == ""
        assert dto.spc1 == ""
        assert dto.spc2 == ""
        assert dto.atcl_fetr_desc == ""
        assert dto.tag_list == []
        assert dto.bild_nm == ""

    def test_dto_validation_invalid_type_prc(self):
        """잘못된 데이터 타입으로 검증 - prc가 int가 아닌 경우"""
        with pytest.raises(ValueError):
            NaverArticleItemDTO(
                atcl_no="12345",
                cortar_no="1156010100",
                atcl_nm="테스트",
                atcl_stat_cd="A01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                prc="not_an_int",  # type: ignore
            )

    def test_dto_validation_invalid_type_lat(self):
        """잘못된 데이터 타입으로 검증 - lat가 float가 아닌 경우"""
        with pytest.raises(ValueError):
            NaverArticleItemDTO(
                atcl_no="12345",
                cortar_no="1156010100",
                atcl_nm="테스트",
                atcl_stat_cd="A01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                lat="not_a_float",  # type: ignore
            )

    def test_dto_validation_invalid_type_tag_list(self):
        """잘못된 데이터 타입으로 검증 - tag_list가 list가 아닌 경우"""
        with pytest.raises(ValueError):
            NaverArticleItemDTO(
                atcl_no="12345",
                cortar_no="1156010100",
                atcl_nm="테스트",
                atcl_stat_cd="A01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                tag_list="not_a_list",  # type: ignore
            )


class TestNaverArticleKeyDTO:
    """NaverArticleKeyDTO 테스트"""

    def test_article_key_dto_fields(self):
        """ArticleKey DTO 필드"""
        dto = NaverArticleKeyDTO(
            complex_number=12345,
            pyeong_type_number=1,
            building_number=101,
            ho_number=201,
            real_estate_type="아파트",
            trade_type="매매",
        )

        assert dto.complex_number == 12345
        assert dto.pyeong_type_number == 1
        assert dto.building_number == 101
        assert dto.ho_number == 201
        assert dto.real_estate_type == "아파트"
        assert dto.trade_type == "매매"

    def test_article_key_dto_all_optional(self):
        """모든 필드가 선택적"""
        dto = NaverArticleKeyDTO()

        assert dto.complex_number is None
        assert dto.pyeong_type_number is None
        assert dto.building_number is None
        assert dto.ho_number is None
        assert dto.real_estate_type == ""
        assert dto.trade_type == ""


class TestNaverArticleDetailDTO:
    """NaverArticleDetailDTO 테스트"""

    def test_article_detail_dto_fields(self):
        """ArticleDetail DTO 필드"""
        dto = NaverArticleDetailDTO(
            price_info={"deal_price": 50000, "jeonse_price": 30000},
            detail_info={"floor": "7층", "direction": "남향"},
            space_info={"supply_area": 84.94, "exclusive_area": 59.95},
            size_info={"total_pyeong": 25.5},
        )

        assert dto.price_info is not None
        assert dto.detail_info is not None
        assert dto.space_info is not None
        assert dto.size_info is not None
        assert dto.price_info["deal_price"] == 50000
        assert dto.detail_info["floor"] == "7층"

    def test_article_detail_dto_all_optional(self):
        """모든 필드가 선택적"""
        dto = NaverArticleDetailDTO()

        assert dto.price_info is None
        assert dto.detail_info is None
        assert dto.space_info is None
        assert dto.size_info is None


class TestNaverComplexDTO:
    """NaverComplexDTO 테스트"""

    def test_complex_dto_fields(self):
        """Complex DTO 필드"""
        dto = NaverComplexDTO(
            complex_number=12345,
            complex_name="테스트 단지",
            address="서울시 강남구",
            total_household_number=500,
            construction_company="현대건설",
        )

        assert dto.complex_number == 12345
        assert dto.complex_name == "테스트 단지"
        assert dto.address == "서울시 강남구"
        assert dto.total_household_number == 500
        assert dto.construction_company == "현대건설"

    def test_complex_dto_approval_elapsed_year_optional(self):
        """approval_elapsed_year 필드 선택적"""
        dto = NaverComplexDTO(
            complex_number=12345,
            complex_name="테스트 단지",
            address="서울시 강남구",
            total_household_number=500,
            construction_company="현대건설",
        )

        assert dto.approval_elapsed_year is None

    def test_complex_dto_with_approval_elapsed_year(self):
        """approval_elapsed_year 포함 생성"""
        dto = NaverComplexDTO(
            complex_number=12345,
            complex_name="테스트 단지",
            address="서울시 강남구",
            total_household_number=500,
            construction_company="현대건설",
            approval_elapsed_year=15,
        )

        assert dto.approval_elapsed_year == 15

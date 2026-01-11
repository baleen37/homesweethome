"""AsilAptListDTO 필드 검증 통합 테스트

실제 API 응답으로 DTO 파싱을 테스트합니다.
"""

import pytest

from crawler.asil import AsilAptListCrawler
from crawler.dto.asil_apt_list import AsilAptListDTO


@pytest.mark.integration
class TestAsilAptListDTOIntegration:
    """AsilAptListDTO 통합 테스트 - 실제 API 응답으로 파싱"""

    def test_parse_real_api_response(self):
        """실제 API 응답을 파싱하여 DTO 필드 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        # 실제 API 호출
        content = crawler.fetch(crawler.get_url())

        # JSON 파싱
        result = crawler.parse(content)

        # 최소 1개 이상의 데이터가 있어야 함
        assert len(result) > 0, "역삼동에는 아파트가 있어야 함"

        # 첫 번째 DTO 검증
        dto = result[0]
        self._validate_dto_fields(dto)

    def test_parse_all_fields_from_real_api(self):
        """실제 API 응답에서 모든 필드가 올바르게 파싱되는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        # 모든 DTO에 대해 필드 검증
        for dto in result:
            self._validate_dto_fields(dto)

    def test_alias_fields_work_in_real_response(self):
        """실제 API 응답에서 alias 필드가 올바르게 매핑되는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        # movein → build_year alias가 작동하는지 확인
        # 실제 API는 movein 필드를 반환함
        for dto in result:
            # build_year 필드가 접근 가능해야 함
            assert hasattr(dto, "build_year"), "build_year 필드가 존재해야 함"
            # build_year 또는 movein 중 하나는 값이 있어야 함
            # (API 응답에 따라 다를 수 있음)
            if dto.build_year:
                assert isinstance(dto.build_year, str), "build_year는 문자열이어야 함"

    def test_coordinate_fields_are_float_convertible(self):
        """실제 API 응답에서 좌표 필드가 float로 변환 가능한지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        # 좌표가 있는 데이터만 검증
        for dto in result:
            if dto.lat and dto.lat != "" and dto.lat != "0" and dto.lat != "0.0":
                try:
                    float(dto.lat)
                except ValueError:
                    raise AssertionError(f"lat '{dto.lat}'는 float로 변환 가능해야 함")

            if dto.lng and dto.lng != "" and dto.lng != "0" and dto.lng != "0.0":
                try:
                    float(dto.lng)
                except ValueError:
                    raise AssertionError(f"lng '{dto.lng}'는 float로 변환 가능해야 함")

    def test_household_field_is_numeric(self):
        """실제 API 응답에서 household 필드가 숫자 형식인지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        # household가 있는 데이터만 검증
        for dto in result:
            if dto.household and dto.household != "":
                # 콤마 제거 후 int로 변환 가능해야 함
                household_cleaned = dto.household.replace(",", "")
                try:
                    int(household_cleaned)
                except ValueError:
                    raise AssertionError(f"household '{dto.household}'는 숫자 형식이어야 함")

    def test_gu_name_property_works_with_real_data(self):
        """실제 API 응답에서 gu_name property가 올바르게 작동하는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        # 모든 DTO의 gu_name 검증
        for dto in result:
            # dong 코드가 11680으로 시작하면 강남구여야 함
            if dto.dong.startswith("11680"):
                assert dto.gu_name == "강남구", (
                    f"dong 코드 {dto.dong}는 강남구여야 함. 실제: {dto.gu_name}"
                )

    def test_model_dump_returns_correct_structure(self):
        """실제 API 응답에서 model_dump()가 올바른 구조를 반환하는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)

        content = crawler.fetch(crawler.get_url())
        result = crawler.parse(content)

        assert len(result) > 0

        dto = result[0]
        dumped = dto.model_dump()

        # dict 타입 검증
        assert isinstance(dumped, dict), "model_dump()는 dict를 반환해야 함"

        # 필수 필드 포함 검증
        assert "seq" in dumped, "seq 필드가 포함되어야 함"
        assert "name" in dumped, "name 필드가 포함되어야 함"
        assert "dong" in dumped, "dong 필드가 포함되어야 함"
        assert "dongname" in dumped, "dongname 필드가 포함되어야 함"

        # alias 필드 검증
        assert "build_year" in dumped, "build_year 필드가 포함되어야 함"
        assert "dong_count" in dumped, "dong_count 필드가 포함되어야 함"

    def _validate_dto_fields(self, dto: AsilAptListDTO) -> None:
        """DTO 필드 검증 헬퍼 메서드"""
        # 1. AsilAptListDTO 타입인지
        assert isinstance(dto, AsilAptListDTO), "AsilAptListDTO 타입이어야 함"

        # 2. 필수 필드가 존재하고 비어있지 않은지
        assert dto.seq, "seq 필드는 비어있지 않아야 함"
        assert dto.name, "name 필드는 비어있지 않아야 함"
        assert dto.dong, "dong 필드는 비어있지 않아야 함"
        assert dto.dongname, "dongname 필드는 비어있지 않아야 함"

        # 3. 필수 필드 타입 검증
        assert isinstance(dto.seq, str), "seq 필드는 문자열이어야 함"
        assert isinstance(dto.name, str), "name 필드는 문자열이어야 함"
        assert isinstance(dto.dong, str), "dong 필드는 문자열이어야 함"
        assert isinstance(dto.dongname, str), "dongname 필드는 문자열이어야 함"

        # 4. 옵션 필드 타입 검증 (값이 있는 경우)
        if dto.bungi is not None:
            assert isinstance(dto.bungi, str), "bungi 필드는 문자열이어야 함"

        if dto.build_year is not None:
            assert isinstance(dto.build_year, str), "build_year 필드는 문자열이어야 함"

        if dto.household is not None:
            assert isinstance(dto.household, str), "household 필드는 문자열이어야 함"

        if dto.dong_count is not None:
            assert isinstance(dto.dong_count, str), "dong_count 필드는 문자열이어야 함"

        if dto.offer is not None:
            assert isinstance(dto.offer, str), "offer 필드는 문자열이어야 함"

        if dto.lat is not None:
            assert isinstance(dto.lat, str), "lat 필드는 문자열이어야 함"

        if dto.lng is not None:
            assert isinstance(dto.lng, str), "lng 필드는 문자열이어야 함"

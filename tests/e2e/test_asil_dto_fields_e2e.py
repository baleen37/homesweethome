"""AsilAptListDTO 필드 검증 E2E 테스트

실제 크롤링 후 DTO 필드 완전도와 데이터 타입을 검증합니다.
"""

import pytest

from crawler.asil import AsilAptListCrawler
from crawler.dto.asil_apt_list import AsilAptListDTO


@pytest.mark.e2e
class TestAsilAptListDTOFieldsE2E:
    """AsilAptListDTO 필드 검증 E2E 테스트"""

    def test_all_required_fields_present_after_crawl(self):
        """크롤링 후 필수 필드가 모두 존재해야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0, "크롤링 결과가 있어야 함"

        # 모든 DTO의 필수 필드 검증
        for dto in result:
            assert isinstance(dto, AsilAptListDTO), "AsilAptListDTO 타입이어야 함"
            assert dto.seq, f"seq 필드는 비어있지 않아야 함 (name: {dto.name})"
            assert dto.name, f"name 필드는 비어있지 않아야 함 (seq: {dto.seq})"
            assert dto.dong, f"dong 필드는 비어있지 않아야 함 (name: {dto.name})"
            assert dto.dongname, f"dongname 필드는 비어있지 않아야 함 (name: {dto.name})"

    def test_alias_fields_mapped_correctly(self):
        """alias 필드가 올바르게 매핑되어야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        # movein → build_year alias 확인
        build_year_count = sum(1 for dto in result if dto.build_year is not None)
        assert build_year_count > 0, "최소한 하나의 DTO는 build_year 값을 가져야 함"

        # total_dong → dong_count alias 확인
        dong_count_count = sum(1 for dto in result if dto.dong_count is not None)
        assert dong_count_count > 0, "최소한 하나의 DTO는 dong_count 값을 가져야 함"

    def test_field_data_types_are_correct(self):
        """모든 필드의 데이터 타입이 올바른지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        for dto in result:
            # 필수 필드 타입 검증
            assert isinstance(dto.seq, str), f"seq는 str이어야 함 (실제: {type(dto.seq)})"
            assert isinstance(dto.name, str), f"name은 str이어야 함 (실제: {type(dto.name)})"
            assert isinstance(dto.dong, str), f"dong은 str이어야 함 (실제: {type(dto.dong)})"
            assert isinstance(dto.dongname, str), (
                f"dongname은 str이어야 함 (실제: {type(dto.dongname)})"
            )

            # 옵션 필드 타입 검증 (값이 있는 경우)
            if dto.bungi is not None:
                assert isinstance(dto.bungi, str), f"bungi는 str이어야 함 (실제: {type(dto.bungi)})"

            if dto.build_year is not None:
                assert isinstance(dto.build_year, str), (
                    f"build_year는 str이어야 함 (실제: {type(dto.build_year)})"
                )

            if dto.household is not None:
                assert isinstance(dto.household, str), (
                    f"household는 str이어야 함 (실제: {type(dto.household)})"
                )

            if dto.dong_count is not None:
                assert isinstance(dto.dong_count, str), (
                    f"dong_count는 str이어야 함 (실제: {type(dto.dong_count)})"
                )

            if dto.offer is not None:
                assert isinstance(dto.offer, str), f"offer는 str이어야 함 (실제: {type(dto.offer)})"

            if dto.lat is not None:
                assert isinstance(dto.lat, str), f"lat는 str이어야 함 (실제: {type(dto.lat)})"

            if dto.lng is not None:
                assert isinstance(dto.lng, str), f"lng는 str이어야 함 (실제: {type(dto.lng)})"

    def test_coordinate_fields_are_valid(self):
        """좌표 필드가 유효한 형식인지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        valid_coord_count = 0

        for dto in result:
            # 좌표가 있는 경우만 검증
            if dto.lat and dto.lat != "" and dto.lat != "0" and dto.lat != "0.0":
                try:
                    lat_float = float(dto.lat)
                    assert -90 <= lat_float <= 90, f"위도는 -90~90 범위여야 함 (실제: {lat_float})"
                    valid_coord_count += 1
                except ValueError:
                    raise AssertionError(f"lat '{dto.lat}'는 float로 변환 가능해야 함")

            if dto.lng and dto.lng != "" and dto.lng != "0" and dto.lng != "0.0":
                try:
                    lng_float = float(dto.lng)
                    assert -180 <= lng_float <= 180, (
                        f"경도는 -180~180 범위여야 함 (실제: {lng_float})"
                    )
                except ValueError:
                    raise AssertionError(f"lng '{dto.lng}'는 float로 변환 가능해야 함")

        # 최소한 몇 개의 데이터는 유효한 좌표를 가져야 함
        assert valid_coord_count > 0, "최소한 1개 이상의 DTO는 유효한 좌표를 가져야 함"

    def test_household_field_is_numeric_string(self):
        """household 필드가 숫자 형식의 문자열인지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        for dto in result:
            if dto.household and dto.household != "":
                # 콤마 제거 후 int로 변환 가능해야 함
                household_cleaned = dto.household.replace(",", "")
                try:
                    household_int = int(household_cleaned)
                    assert household_int >= 0, f"세대수는 0 이상이어야 함 (실제: {household_int})"
                except ValueError:
                    raise AssertionError(f"household '{dto.household}'는 숫자 형식이어야 함")

    def test_gu_name_property_consistency(self):
        """gu_name property가 dong 코드와 일치하는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        # 모든 DTO의 dong 코드는 11680으로 시작하므로 강남구여야 함
        for dto in result:
            assert dto.dong.startswith("11680"), (
                f"dong 코드는 11680으로 시작해야 함 (실제: {dto.dong})"
            )
            assert dto.gu_name == "강남구", (
                f"dong 코드 {dto.dong}는 강남구여야 함 (실제: {dto.gu_name})"
            )

    def test_field_completeness_across_multiple_dongs(self):
        """여러 동에서 크롤링했을 때 필드 완전도 검증

        참고: 일부 동 코드는 데이터가 없을 수 있으므로,
        데이터가 있는 동에 대해서만 검증합니다.
        """
        # 여러 동 코드로 크롤링 (역삼동, 청담동, 삼성동 등)
        dong_codes = ["1168010100", "1168010200", "1168010300"]

        data_found = False

        for dong_code in dong_codes:
            crawler = AsilAptListCrawler(dong_code=dong_code, min_household=100)
            result = crawler.crawl()

            # 데이터가 있는 동에 대해서만 검증
            if len(result) > 0:
                data_found = True

                # 필수 필드 검증
                for dto in result:
                    assert dto.seq, f"{dong_code}: seq 필드는 비어있지 않아야 함"
                    assert dto.name, f"{dong_code}: name 필드는 비어있지 않어야 함"
                    assert dto.dong == dong_code, f"{dong_code}: dong 코드가 일치해야 함"
                    assert dto.dongname, f"{dong_code}: dongname 필드는 비어있지 않어야 함"

        # 최소한 하나의 동에서는 데이터를 찾아야 함
        assert data_found, "적어도 하나의 동에서 데이터를 찾아야 함"

    def test_model_dump_consistency(self):
        """model_dump() 메서드가 일관된 결과를 반환하는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        for dto in result:
            dumped = dto.model_dump()

            # dict 타입 검증
            assert isinstance(dumped, dict), "model_dump()는 dict를 반환해야 함"

            # 필수 필드 포함 검증
            required_fields = ["seq", "name", "dong", "dongname"]
            for field in required_fields:
                assert field in dumped, f"{field} 필드가 model_dump() 결과에 포함되어야 함"

            # alias 필드 검증
            assert "build_year" in dumped, "build_year 필드가 포함되어야 함"
            assert "dong_count" in dumped, "dong_count 필드가 포함되어야 함"

            # 값 일치 검증
            assert dumped["seq"] == dto.seq, "seq 값이 일치해야 함"
            assert dumped["name"] == dto.name, "name 값이 일치해야 함"
            assert dumped["dong"] == dto.dong, "dong 값이 일치해야 함"
            assert dumped["dongname"] == dto.dongname, "dongname 값이 일치해야 함"

    def test_no_extra_fields_from_api(self):
        """API 응답에만 존재하고 DTO에 없는 필드가 없는지 검증"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        # DTO 필드 목록 가져오기
        dto_fields = set(AsilAptListDTO.model_fields.keys())

        # API 응답에만 존재한다고 알려진 필드들 (DTO에 없어야 함)
        api_only_fields = ["building", "type", "etc"]

        for field in api_only_fields:
            # DTO에 이 필드가 없어야 함
            assert field not in dto_fields, f"{field} 필드는 DTO에 없어야 함 (API 응답에만 존재)"

    def test_household_greater_than_zero_with_filter(self):
        """min_household 필터가 적용된 경우 household가 0보다 커야 함"""
        crawler = AsilAptListCrawler(dong_code="1168010100", min_household=100)
        result = crawler.crawl()

        assert len(result) > 0

        # min_household=100이면 모든 결과의 household가 100 이상이어야 함
        for dto in result:
            if dto.household and dto.household != "":
                household_cleaned = dto.household.replace(",", "")
                household_int = int(household_cleaned)
                assert household_int >= 100, (
                    f"min_household=100 요청 시 household는 100 이상이어야 함. "
                    f"실제: {household_int} (name: {dto.name})"
                )

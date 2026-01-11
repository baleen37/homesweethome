"""AsilAptListDTO 필드 검증 단위 테스트

API 응답 필드와 DTO 필드 매핑을 검증합니다.
"""

import types
from typing import Union, get_args, get_origin

from crawler.dto.asil_apt_list import AsilAptListDTO


class TestAsilAptListDTOFieldMapping:
    """AsilAptListDTO 필드 매핑 검증 테스트"""

    def test_all_required_fields_present(self):
        """필수 필드(seq, name, dong, dongname)가 존재하고 비어있지 않아야 함"""
        # DTO 생성에 필요한 최소 데이터
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        # 필수 필드 검증
        assert dto.seq == "20340925", "seq 필드가 올바르게 매핑되어야 함"
        assert dto.name == "역삼자이", "name 필드가 올바르게 매핑되어야 함"
        assert dto.dong == "1168010100", "dong 필드가 올바르게 매핑되어야 함"
        assert dto.dongname == "역삼동", "dongname 필드가 올바르게 매핑되어야 함"

    def test_optional_fields_with_none(self):
        """옵션 필드가 None으로 초기화되어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        # 옵션 필드 기본값 검증
        assert dto.bungi is None, "bungi 필드 기본값은 None이어야 함"
        assert dto.build_year is None, "build_year 필드 기본값은 None이어야 함"
        assert dto.household is None, "household 필드 기본값은 None이어야 함"
        assert dto.dong_count is None, "dong_count 필드 기본값은 None이어야 함"
        assert dto.offer is None, "offer 필드 기본값은 None이어야 함"
        assert dto.lat is None, "lat 필드 기본값은 None이어야 함"
        assert dto.lng is None, "lng 필드 기본값은 None이어야 함"

    def test_alias_movein_to_build_year(self):
        """movein 필드가 build_year로 alias 매핑되어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
            "movein": "2016",  # API 응답 필드명
        }

        dto = AsilAptListDTO(**data)

        # movein → build_year alias 검증
        assert dto.build_year == "2016", "movein 필드가 build_year로 매핑되어야 함"

    def test_alias_total_dong_to_dong_count(self):
        """total_dong 필드가 dong_count로 alias 매핑되어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
            "total_dong": "3",  # API 응답 필드명
        }

        dto = AsilAptListDTO(**data)

        # total_dong → dong_count alias 검증
        assert dto.dong_count == "3", "total_dong 필드가 dong_count로 매핑되어야 함"

    def test_all_optional_fields_with_values(self):
        """모든 옵션 필드에 값이 있을 때 올바르게 매핑되어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
            "bungi": "123",
            "movein": "2016",
            "household": "408",
            "total_dong": "3",
            "offer": "매물 5건",
            "lat": "37.514575",
            "lng": "127.044555",
        }

        dto = AsilAptListDTO(**data)

        # 모든 필드 검증
        assert dto.bungi == "123", "bungi 필드가 올바르게 매핑되어야 함"
        assert dto.build_year == "2016", "build_year 필드가 올바르게 매핑되어야 함"
        assert dto.household == "408", "household 필드가 올바르게 매핑되어야 함"
        assert dto.dong_count == "3", "dong_count 필드가 올바르게 매핑되어야 함"
        assert dto.offer == "매물 5건", "offer 필드가 올바르게 매핑되어야 함"
        assert dto.lat == "37.514575", "lat 필드가 올바르게 매핑되어야 함"
        assert dto.lng == "127.044555", "lng 필드가 올바르게 매핑되어야 함"

    def test_building_type_field_not_in_dto(self):
        """building 필드는 API 응답에 존재하지 않으므로 DTO에 없어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        # building 필드가 없는지 확인
        assert not hasattr(dto, "building") or not hasattr(
            AsilAptListDTO.model_fields, "building"
        ), "building 필드는 DTO에 없어야 함"

    def test_type_field_not_in_dto(self):
        """type 필드는 API 응답에 존재하지 않으므로 DTO에 없어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        # type 필드가 없는지 확인
        assert not hasattr(dto, "type") or not hasattr(AsilAptListDTO.model_fields, "type"), (
            "type 필드는 DTO에 없어야 함"
        )

    def test_etc_field_not_in_dto(self):
        """etc 필드는 API 응답에 존재하지 않으므로 DTO에 없어야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        # etc 필드가 없는지 확인
        assert not hasattr(dto, "etc") or not hasattr(AsilAptListDTO.model_fields, "etc"), (
            "etc 필드는 DTO에 없어야 함"
        )

    def test_field_types_are_string_or_optional_string(self):
        """모든 필드 타입이 str 또한 Optional[str]이어야 함"""

        model_fields = AsilAptListDTO.model_fields

        # 필수 필드 타입 검증 (str)
        required_fields = ["seq", "name", "dong", "dongname"]
        for field_name in required_fields:
            field_info = model_fields[field_name]
            # FieldInfo에서 타입 확인
            annotation = field_info.annotation
            assert annotation is str, f"{field_name} 필드 타입은 str이어야 함 (실제: {annotation})"

        # 옵션 필드 타입 검증 (str | None)
        optional_fields = [
            "bungi",
            "build_year",
            "household",
            "dong_count",
            "offer",
            "lat",
            "lng",
        ]
        for field_name in optional_fields:
            field_info = model_fields[field_name]
            annotation = field_info.annotation

            # Optional 필드인지 확인 (Union[str, None] 또는 str | None)
            origin = get_origin(annotation)
            args = get_args(annotation)

            # Optional은 Union[str, None]의 형태
            is_union = origin is types.UnionType or origin is Union
            has_str_in_args = str in args if args else False
            has_none_in_args = type(None) in args if args else False

            assert is_union and has_str_in_args and has_none_in_args, (
                f"{field_name} 필드는 Optional[str]이어야 함 (실제: {annotation})"
            )


class TestAsilAptListDTOGuName:
    """AsilAptListDTO.gu_name property 테스트"""

    def test_gu_name_property_from_dong_code(self):
        """dong 코드 앞 5자리에서 구 이름을 추출해야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",  # 강남구 역삼동
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)

        assert dto.gu_name == "강남구", "dong 코드 11680에서 강남구가 추출되어야 함"

    def test_gu_name_property_for_different_gu(self):
        """다른 구 코드에서 올바른 구 이름을 반환해야 함"""
        test_cases = [
            ("1168010100", "강남구"),  # 강남구 역삼동
            ("1165010100", "서초구"),  # 서초구
            ("1171010100", "송파구"),  # 송파구
            ("1174010100", "강동구"),  # 강동구
            ("1121510100", "광진구"),  # 광진구
            ("1123010100", "동대문구"),  # 동대문구
            ("1138010100", "은평구"),  # 은평구
            ("1141010100", "서대문구"),  # 서대문구
            ("1144010100", "마포구"),  # 마포구
            ("1156010100", "영등포구"),  # 영등포구
        ]

        for dong_code, expected_gu in test_cases:
            data = {
                "seq": "20340925",
                "name": "테스트아파트",
                "dong": dong_code,
                "dongname": "테스트동",
            }

            dto = AsilAptListDTO(**data)
            assert dto.gu_name == expected_gu, (
                f"dong 코드 {dong_code}에서 {expected_gu}가 추출되어야 함"
            )

    def test_gu_name_returns_none_for_invalid_code(self):
        """유효하지 않은 구 코드에 대해 None을 반환해야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "9999901000",  # 존재하지 않는 구 코드
            "dongname": "테스트동",
        }

        dto = AsilAptListDTO(**data)

        assert dto.gu_name is None, "유효하지 않은 구 코드에 대해 None을 반환해야 함"


class TestAsilAptListDTOModelDump:
    """AsilAptListDTO.model_dump() 메서드 테스트"""

    def test_model_dump_returns_dict(self):
        """model_dump()가 올바른 dict를 반환해야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
            "movein": "2016",
            "household": "408",
            "total_dong": "3",
        }

        dto = AsilAptListDTO(**data)
        dumped = dto.model_dump()

        assert isinstance(dumped, dict), "model_dump()는 dict를 반환해야 함"

        # alias 필드가 올바른 이름으로 변환되어야 함
        assert dumped["build_year"] == "2016", "build_year 필드가 dump에 포함되어야 함"
        assert dumped["dong_count"] == "3", "dong_count 필드가 dump에 포함되어야 함"
        assert dumped["household"] == "408", "household 필드가 dump에 포함되어야 함"

    def test_model_dump_exclude_none(self):
        """model_dump(exclude_none=True)가 None 필드를 제외해야 함"""
        data = {
            "seq": "20340925",
            "name": "역삼자이",
            "dong": "1168010100",
            "dongname": "역삼동",
        }

        dto = AsilAptListDTO(**data)
        dumped = dto.model_dump(exclude_none=True)

        # None 필드가 제외되어야 함
        assert "bungi" not in dumped, "None 필드는 제외되어야 함"
        assert "build_year" not in dumped, "None 필드는 제외되어야 함"
        assert "household" not in dumped, "None 필드는 제외되어야 함"
        assert "dong_count" not in dumped, "None 필드는 제외되어야 함"

        # 필수 필드는 포함되어야 함
        assert "seq" in dumped, "필수 필드는 포함되어야 함"
        assert "name" in dumped, "필수 필드는 포함되어야 함"

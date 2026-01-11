"""ASIL 인구 통계 DTO"""

from typing import Any

from pydantic import BaseModel, field_validator


def _parse_population_value(value: Any) -> int:
    """콤마와 단위가 포함된 인구값 문자열을 int로 변환

    Args:
        value: "9,390,925명" 형식의 문자열 또는 int

    Returns:
        파싱된 정수값

    Examples:
        _parse_population_value("9,390,925명") -> 9390925
        _parse_population_value("144,543명") -> 144543
        _parse_population_value(12345) -> 12345
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # 콤마 제거 후 "명" 접미사 제거
        return int(value.replace(",", "").replace("명", ""))
    return 0


class AsilPopulationDTO(BaseModel):
    """ASIL 인구 통계 데이터 모델"""

    seq: str  # 지역 코드 (11=서울, 5자리=구)
    name: str  # 지역명
    v1: int  # 인구값 1 (총인구)
    v2: int  # 인구값 2
    v3: int  # 인구값 3
    v2_gap: int  # v1-v2 차이
    v3_gap: int  # v2-v3 차이
    v2_icon: str  # v2 추세 아이콘 ("up", "down")
    v3_icon: str  # v3 추세 아이콘 ("up", "down")

    @field_validator("v1", "v2", "v3", "v2_gap", "v3_gap", mode="before")
    @classmethod
    def parse_population_fields(cls, value: Any) -> int:
        """인구값 필드를 int로 파싱"""
        return _parse_population_value(value)

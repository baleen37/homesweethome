"""아파트 데이터 필터링 유틸리티

데이터 유효성 검증 및 필터링 기능을 제공합니다.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class FilterOptions:
    """데이터 필터링 옵션

    Attributes:
        min_household: 최소 세대수 (0 이하면 필터링하지 않음)
        require_valid_coords: 유효한 좌표 요구 여부 (False면 (0, 0) 좌표도 허용)
        require_name: 이름 필드 요구 여부
        require_address: 주소 필드 요구 여부
    """

    min_household: int = 0
    require_valid_coords: bool = False
    require_name: bool = True
    require_address: bool = False

    @classmethod
    def strict(cls) -> "FilterOptions":
        """엄격한 필터링 옵션 (유효한 데이터만 유지)

        - household >= 1
        - 유효한 좌표 (0, 0 제외)
        - 이름 필수
        """
        return cls(min_household=1, require_valid_coords=True, require_name=True)

    @classmethod
    def moderate(cls) -> "FilterOptions":
        """중간 수준 필터링 옵션

        - household >= 1
        - 좌표는 (0, 0) 허용
        - 이름 필수
        """
        return cls(min_household=1, require_valid_coords=False, require_name=True)

    @classmethod
    def permissive(cls) -> "FilterOptions":
        """관대한 필터링 옵션 (대부분의 데이터 유지)

        - household 제한 없음
        - 좌표 (0, 0) 허용
        - 이름 필수
        """
        return cls(min_household=0, require_valid_coords=False, require_name=True)


def is_valid_household(household: str | None, min_household: int) -> bool:
    """세대수 유효성 검증

    Args:
        household: 세대수 문자열
        min_household: 최소 세대수

    Returns:
        유효하면 True
    """
    if min_household <= 0:
        return True

    if household is None or household == "":
        return False

    try:
        household_int = int(household)
        return household_int >= min_household
    except (ValueError, TypeError):
        return False


def is_valid_coordinate(lat: str | None, lng: str | None) -> bool:
    """좌표 유효성 검증

    Args:
        lat: 위도 문자열
        lng: 경도 문자열

    Returns:
        유효하면 True (둘 중 하나라도 0이 아니면 유효)
    """
    if lat is None or lng is None or lat == "" or lng == "":
        return False

    try:
        lat_float = float(lat)
        lng_float = float(lng)
        # 서울 좌표 범위 내에 있는지 확인 (대략적인 범위)
        # 위도: 37.4 ~ 37.7, 경도: 126.8 ~ 127.2
        seoul_lat_min = 37.4
        seoul_lat_max = 37.7
        seoul_lng_min = 126.8
        seoul_lng_max = 127.2

        return (
            seoul_lat_min <= lat_float <= seoul_lat_max
            and seoul_lng_min <= lng_float <= seoul_lng_max
        )
    except (ValueError, TypeError):
        return False


def is_valid_name(name: str | None) -> bool:
    """이름 유효성 검증

    Args:
        name: 이름 문자열

    Returns:
        유효하면 True
    """
    return name is not None and name.strip() != ""


def is_valid_address(address: str | None) -> bool:
    """주소 유효성 검증

    Args:
        address: 주소 문자열

    Returns:
        유효하면 True
    """
    return address is not None and address.strip() != ""


def should_filter_record(
    record: dict[str, Any] | Any,
    options: FilterOptions,
) -> bool:
    """레코드 필터링 여부 결정

    Args:
        record: 아파트 데이터 (dict 또는 DTO)
        options: 필터링 옵션

    Returns:
        True면 필터링 (제외), False면 유지
    """
    # dict 또는 DTO에서 데이터 추출
    if hasattr(record, "model_dump"):
        data = record.model_dump()
    elif isinstance(record, dict):
        data = record
    else:
        return True  # 알 수 없는 타입은 필터링

    # household 필터링
    if not is_valid_household(data.get("household"), options.min_household):
        return True

    # 좌표 필터링
    if options.require_valid_coords:
        lat = data.get("lat")
        lng = data.get("lng")
        if not is_valid_coordinate(lat, lng):
            return True

    # 이름 필터링
    if options.require_name and not is_valid_name(data.get("name")):
        return True

    # 주소 필터링
    if options.require_address and not is_valid_address(data.get("address")):
        return True

    return False


def filter_records(
    records: list[Any],
    options: FilterOptions,
) -> list[Any]:
    """레코드 리스트 필터링

    Args:
        records: 아파트 데이터 리스트
        options: 필터링 옵션

    Returns:
        필터링된 레코드 리스트
    """
    return [record for record in records if not should_filter_record(record, options)]


def get_filter_stats(
    original_count: int,
    filtered_count: int,
) -> dict[str, int | float]:
    """필터링 통계 계산

    Args:
        original_count: 원본 레코드 수
        filtered_count: 필터링 후 레코드 수

    Returns:
        필터링 통계 딕셔너리
    """
    removed_count = original_count - filtered_count
    removal_rate = (removed_count / original_count * 100) if original_count > 0 else 0

    return {
        "original_count": original_count,
        "filtered_count": filtered_count,
        "removed_count": removed_count,
        "removal_rate": removal_rate,
    }

"""데이터 품질 분석 유틸리티

아파트 데이터의 품질을 분석하고 리포트를 생성합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DataQualityStats:
    """데이터 품질 통계 정보

    Attributes:
        total_records: 총 레코드 수
        household_zero: household=0 또는 None인 레코드 수
        household_positive: household>=1인 레코드 수
        valid_coords: 유효한 좌표를 가진 레코드 수
        invalid_coords: 좌표가 (0,0)이거나 None인 레코드 수
        field_completeness: 각 필드의 채워진 비율 (필드명: 비율)
        duplicate_count: 중복된 seq 수
        duplicate_rate: 중복 비율 (0~1)
    """

    total_records: int = 0
    household_zero: int = 0
    household_positive: int = 0
    valid_coords: int = 0
    invalid_coords: int = 0
    field_completeness: dict[str, float] = field(default_factory=dict)
    duplicate_count: int = 0
    duplicate_rate: float = 0.0

    def __add__(self, other: "DataQualityStats") -> "DataQualityStats":
        """통계 합산

        Args:
            other: 더할 통계 객체

        Returns:
            합산된 통계 객체
        """
        # 필드 완전도는 가중 평균
        merged_completeness = {}
        for field_name in set(self.field_completeness) | set(other.field_completeness):
            val1 = self.field_completeness.get(field_name, 0)
            val2 = other.field_completeness.get(field_name, 0)
            count1 = self.total_records
            count2 = other.total_records
            total = count1 + count2
            if total > 0:
                merged_completeness[field_name] = (val1 * count1 + val2 * count2) / total

        return DataQualityStats(
            total_records=self.total_records + other.total_records,
            household_zero=self.household_zero + other.household_zero,
            household_positive=self.household_positive + other.household_positive,
            valid_coords=self.valid_coords + other.valid_coords,
            invalid_coords=self.invalid_coords + other.invalid_coords,
            field_completeness=merged_completeness,
            duplicate_count=self.duplicate_count + other.duplicate_count,
            duplicate_rate=(self.duplicate_count + other.duplicate_count)
            / (self.total_records + other.total_records)
            if (self.total_records + other.total_records) > 0
            else 0.0,
        )


def _is_zero_household(record: dict[str, Any]) -> bool:
    """household가 0 또는 None인지 확인

    Args:
        record: 아파트 데이터 딕셔너리

    Returns:
        household가 0 또는 None이면 True
    """
    household = record.get("household")
    if household is None or household == "":
        return True
    try:
        return int(household) == 0
    except (ValueError, TypeError):
        return True


def _has_valid_coords(record: dict[str, Any]) -> bool:
    """유효한 좌표를 가지고 있는지 확인

    Args:
        record: 아파트 데이터 딕셔너리

    Returns:
        유효한 좌표면 True (서울 좌표 범위 내)
    """
    lat = record.get("lat")
    lng = record.get("lng")

    if lat is None or lng is None or lat == "" or lng == "":
        return False

    try:
        lat_float = float(lat)
        lng_float = float(lng)
        # 서울 좌표 범위 (대략적)
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


def _calculate_field_completeness(
    records: list[dict[str, Any]],
    fields: list[str],
) -> dict[str, float]:
    """필드 완전도 계산

    Args:
        records: 아파트 데이터 리스트
        fields: 확인할 필드명 리스트

    Returns:
        필드명: 채워진 비율 (0~1)
    """
    if not records:
        return {}

    completeness = {}
    for field_name in fields:
        filled_count = sum(1 for record in records if record.get(field_name) not in (None, ""))
        completeness[field_name] = filled_count / len(records)

    return completeness


def analyze_data_quality(
    records: list[Any],
    unique_seqs: set[str],
    fields: list[str] | None = None,
) -> DataQualityStats:
    """아파트 데이터 품질 분석

    Args:
        records: 아파트 데이터 리스트 (DTO 또는 dict)
        unique_seqs: 중복 제거를 위한 고유 seq 집합
        fields: 완전도를 확인할 필드명 리스트 (None이면 기본 필드 사용)

    Returns:
        데이터 품질 통계
    """
    if fields is None:
        fields = [
            "seq",
            "name",
            "dong",
            "dongname",
            "bungi",
            "movein",
            "household",
            "total_dong",
            "type",
            "etc",
            "offer",
            "lat",
            "lng",
        ]

    # DTO를 딕셔너리로 변환
    dict_records = []
    for record in records:
        if hasattr(record, "model_dump"):
            dict_records.append(record.model_dump())
        elif isinstance(record, dict):
            dict_records.append(record)
        else:
            # 알 수 없는 타입은 건너뜀
            continue

    if not dict_records:
        return DataQualityStats()

    # household 분석
    household_zero = sum(1 for r in dict_records if _is_zero_household(r))
    household_positive = len(dict_records) - household_zero

    # 좌표 분석
    valid_coords = sum(1 for r in dict_records if _has_valid_coords(r))
    invalid_coords = len(dict_records) - valid_coords

    # 필드 완전도 분석
    field_completeness = _calculate_field_completeness(dict_records, fields)

    # 중복 분석
    total_records = len(dict_records)
    unique_count = len(unique_seqs)
    duplicate_count = total_records - unique_count
    duplicate_rate = duplicate_count / total_records if total_records > 0 else 0.0

    return DataQualityStats(
        total_records=total_records,
        household_zero=household_zero,
        household_positive=household_positive,
        valid_coords=valid_coords,
        invalid_coords=invalid_coords,
        field_completeness=field_completeness,
        duplicate_count=duplicate_count,
        duplicate_rate=duplicate_rate,
    )


def generate_quality_report(
    stats: DataQualityStats,
    include_field_details: bool = True,
) -> str:
    """데이터 품질 리포트 생성

    Args:
        stats: 데이터 품질 통계
        include_field_details: 필드별 완전도 포함 여부

    Returns:
        사람이 읽기 쉬운 리포트 문자열
    """
    # Calculate percentages first to handle division by zero
    household_positive_pct = (
        stats.household_positive / stats.total_records * 100 if stats.total_records > 0 else 0.0
    )
    household_zero_pct = (
        stats.household_zero / stats.total_records * 100 if stats.total_records > 0 else 0.0
    )
    valid_coords_pct = (
        stats.valid_coords / stats.total_records * 100 if stats.total_records > 0 else 0.0
    )
    invalid_coords_pct = (
        stats.invalid_coords / stats.total_records * 100 if stats.total_records > 0 else 0.0
    )

    lines = [
        "=" * 60,
        "데이터 품질 분석 리포트",
        "=" * 60,
        f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 기본 통계",
        f"총 레코드 수: {stats.total_records:,}건",
        "",
        "## 세대수 분포",
        f"  household >= 1: {stats.household_positive:,}건 ({household_positive_pct:.1f}%)",
        f"  household = 0 또는 None: {stats.household_zero:,}건 ({household_zero_pct:.1f}%)",
        "",
        "## 좌표 품질",
        f"  유효한 좌표: {stats.valid_coords:,}건 ({valid_coords_pct:.1f}%)",
        (
            f"  유효하지 않은 좌표 (0,0) 또는 None: "
            f"{stats.invalid_coords:,}건 ({invalid_coords_pct:.1f}%)"
        ),
        "",
        "## 중복 분석",
        f"  중복 레코드 수: {stats.duplicate_count:,}건",
        f"  중복 비율: {stats.duplicate_rate * 100:.1f}%",
        "",
    ]

    if include_field_details and stats.field_completeness:
        lines.extend(
            [
                "## 필드별 완전도",
                "  (필드가 채워진 비율)",
                "",
            ]
        )

        # 완전도 기준 내림차순 정렬
        sorted_fields = sorted(
            stats.field_completeness.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        for field_name, completeness in sorted_fields:
            percentage = completeness * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            lines.append(f"  {field_name:15s}: {percentage:5.1f}% [{bar}]")

    lines.extend(
        [
            "",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def save_quality_report(
    stats: DataQualityStats,
    filepath: str,
    include_field_details: bool = True,
) -> None:
    """데이터 품질 리포트를 파일로 저장

    Args:
        stats: 데이터 품질 통계
        filepath: 저장할 파일 경로
        include_field_details: 필드별 완전도 포함 여부
    """
    import os

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    report = generate_quality_report(stats, include_field_details)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)


def log_quality_summary(
    stats: DataQualityStats,
    log_func: callable,
) -> None:
    """데이터 품질 요약을 로그로 출력

    Args:
        stats: 데이터 품질 통계
        log_func: 로그 출력 함수 (예: log_message)
    """
    log_func(
        f"  [품질] 총 {stats.total_records:,}건 "
        f"(household>=1: {stats.household_positive:,}건, "
        f"유효좌표: {stats.valid_coords:,}건, "
        f"중복: {stats.duplicate_count:,}건/{stats.duplicate_rate * 100:.1f}%)"
    )

"""E2E 테스트 공통 fixture 및 헬퍼 함수"""

import csv
import os
from pathlib import Path
from typing import Any

# =============================================================================
# 상수: 샘플 동 코드
# =============================================================================

SEOUL_DONG_CODES = {
    "1168010100": "역삼동",
}


# =============================================================================
# 상수: 필수 필드
# =============================================================================

ASIL_REQUIRED_FIELDS = {"seq", "name", "dong", "dongname", "bungi"}


# =============================================================================
# Fixture: tmp_path (pytest 기본 fixture)
# =============================================================================

# pytest는 이미 tmp_path fixture를 제공하므로 별도 정의 불필요


# =============================================================================
# CSV 관련 헬퍼 함수
# =============================================================================


def export_to_csv(data: list[dict], filepath: str) -> None:
    """딕셔너리 리스트를 CSV로 내보내기

    Args:
        data: 내보낼 딕셔너리 리스트
        filepath: CSV 파일 경로

    Note:
        - 첫 번째 아이템의 키들을 헤더로 사용
        - output 디렉토리가 없으면 생성
        - UTF-8 인코딩
    """
    if not data:
        return

    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # 첫 번째 아이템의 키들을 헤더로 사용
    fieldnames = list(data[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def verify_csv_file(
    csv_path: str | Path,
    expected_count: int,
    required_fields: set[str] | None = None,
) -> list[dict]:
    """CSV 파일 검증

    Args:
        csv_path: CSV 파일 경로
        expected_count: 예상 레코드 수
        required_fields: 필수 필드 집합 (None이면 검증 생략)

    Returns:
        CSV 레코드 리스트

    Raises:
        AssertionError: 검증 실패 시
    """
    csv_path = Path(csv_path)

    # 파일 존재 확인
    assert csv_path.exists(), f"CSV 파일이 생성되지 않음: {csv_path}"

    # CSV 파싱
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    # 레코드 수 검증
    assert len(records) == expected_count, (
        f"CSV 레코드 수 불일치: 예상 {expected_count}, 실제 {len(records)}"
    )

    # 필수 필드 검증
    if required_fields:
        with open(csv_path, encoding="utf-8") as f:
            header = f.readline().strip()
            assert header, "CSV 헤더가 비어있음"
            headers = header.split(",")
            missing_fields = required_fields - set(headers)
            assert not missing_fields, f"CSV 헤더에 필수 필드 누락: {missing_fields}"

    return records


# =============================================================================
# 데이터 수집 헬퍼 함수
# =============================================================================


def collect_apartments_from_dongs(
    dong_codes: dict[str, str] | list[str],
    crawler_class: type,
    max_apartments: int | None = None,
) -> tuple[list[dict], set[str]]:
    """여러 동 코드에서 아파트 데이터 수집

    Args:
        dong_codes: 동 코드 딕셔너리 {코드: 이름} 또는 리스트
        crawler_class: 크롤러 클래스
        max_apartments: 최대 수집 개수 (None이면 무제한)

    Returns:
        (아파트 데이터 리스트, 수집된 동 이름 집합)
    """
    all_apartments = []
    crawled_dongs = set()

    # 딕셔너리면 리스트로 변환
    if isinstance(dong_codes, dict):
        dong_items = list(dong_codes.items())
    else:
        dong_items = [(code, "") for code in dong_codes]

    for dong_code, dong_name in dong_items:
        if max_apartments and len(all_apartments) >= max_apartments:
            break

        crawler = crawler_class(dong_code=dong_code)
        results = crawler.crawl()

        if results:
            crawled_dongs.add(dong_name or dong_code)

        # 남은 용량만큼만 추가
        remaining = max_apartments - len(all_apartments) if max_apartments else None
        if remaining is not None and remaining > 0:
            results = results[:remaining]

        # DTO를 dict로 변환하여 추가
        results_dicts = [apt.model_dump() for apt in results]
        all_apartments.extend(results_dicts)

    return all_apartments, crawled_dongs


# 별칭: 기존 테스트 코드와의 호환성을 위해
crawl_multiple_dongs = collect_apartments_from_dongs


# =============================================================================
# 데이터 검증 헬퍼 함수
# =============================================================================


def verify_apartment_record(
    apt: dict,
    index: int,
    required_fields: set[str] | None = None,
) -> None:
    """아파트 레코드 검증

    Args:
        apt: 아파트 데이터 딕셔너리
        index: 레코드 인덱스 (에러 메시지용)
        required_fields: 필수 필드 집합 (None이면 ASIL_REQUIRED_FIELDS 사용)
    """
    if required_fields is None:
        required_fields = ASIL_REQUIRED_FIELDS

    # 필수 필드 검증
    missing_fields = required_fields - set(apt.keys())
    assert not missing_fields, f"레코드 {index}: 필수 필드 누락: {missing_fields}"

    # 데이터 타입 검증
    assert isinstance(apt["seq"], str), f"레코드 {index}: seq는 문자열이어야 함"
    assert isinstance(apt["name"], str), f"레코드 {index}: name은 문자열이어야 함"
    assert isinstance(apt["dong"], str), f"레코드 {index}: dong은 문자열이어야 함"
    assert isinstance(apt["dongname"], str), f"레코드 {index}: dongname은 문자열이어야 함"

    # 필수 필드가 비어있지 않은지 검증
    assert apt["seq"].strip(), f"레코드 {index}: seq가 비어있음"
    assert apt["dong"].strip(), f"레코드 {index}: dong이 비어있음"


def verify_no_duplicate_seq(apartments: list[dict]) -> None:
    """중복된 seq가 없는지 검증

    Args:
        apartments: 아파트 데이터 리스트
    """
    seq_list = [apt["seq"] for apt in apartments]
    unique_seq_count = len(set(seq_list))
    assert unique_seq_count == len(seq_list), (
        f"중복된 seq 존재: {len(seq_list) - unique_seq_count}개"
    )


def verify_data_integrity(
    original_data: list[dict],
    csv_records: list[dict],
    key_field: str = "seq",
) -> None:
    """원본 데이터와 CSV 데이터의 무결성 검증

    Args:
        original_data: 원본 데이터 리스트
        csv_records: CSV에서 읽은 레코드 리스트
        key_field: 비교할 키 필드
    """
    original_keys = {record[key_field] for record in original_data}
    csv_keys = {record[key_field] for record in csv_records}

    assert original_keys == csv_keys, (
        f"CSV의 {key_field}가 원본 데이터와 불일치: "
        f"원본 {len(original_keys)}개, CSV {len(csv_keys)}개"
    )


def _verify_csv_integrity(csv_path: str, original_data: list[dict]) -> None:
    """CSV 무결성 검증 헬퍼 함수 (내부용)

    Args:
        csv_path: CSV 파일 경로
        original_data: 원본 데이터 리스트
    """
    # 파일 존재 확인
    assert Path(csv_path).exists(), f"CSV 파일이 생성되지 않음: {csv_path}"

    # CSV 파싱
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_records = list(reader)

    # 레코드 수 검증
    assert len(csv_records) == len(original_data), "CSV 레코드 수와 데이터 수 불일치"

    # 헤더 검증
    with open(csv_path, encoding="utf-8") as f:
        header = f.readline().strip()
        assert header, "CSV 헤더가 비어있음"
        headers = header.split(",")
        assert "seq" in headers, "CSV 헤더에 'seq' 필드 누락"
        assert "name" in headers, "CSV 헤더에 'name' 필드 누락"
        assert "dongname" in headers, "CSV 헤더에 'dongname' 필드 누락"

    # 데이터 무결성 검증
    verify_data_integrity(original_data, csv_records)


# =============================================================================
# 통계 헬퍼 함수
# =============================================================================


def calculate_quality_stats(apartments: list[dict]) -> dict[str, Any]:
    """데이터 품질 통계 계산

    Args:
        apartments: 아파트 데이터 리스트

    Returns:
        품질 통계 딕셔너리
    """
    total = len(apartments)

    # household 필드 분석
    household_zero = 0
    household_empty = 0
    household_valid = 0

    for apt in apartments:
        household = apt.get("household")
        if household is None or household == "":
            household_empty += 1
        elif household == "0":
            household_zero += 1
        else:
            household_valid += 1

    # 좌표 분석
    zero_coord = 0
    missing_coord = 0
    valid_coord = 0

    for apt in apartments:
        lat = apt.get("lat")
        lng = apt.get("lng")
        if lat is None or lng is None or lat == "" or lng == "":
            missing_coord += 1
        elif lat == "0" or lng == "0" or lat == "0.0" or lng == "0.0":
            zero_coord += 1
        else:
            valid_coord += 1

    return {
        "total": total,
        "household_zero": household_zero,
        "household_empty": household_empty,
        "household_valid": household_valid,
        "zero_coord": zero_coord,
        "missing_coord": missing_coord,
        "valid_coord": valid_coord,
    }


def print_quality_stats(stats: dict[str, Any], title: str = "데이터 품질 분석") -> None:
    """품질 통계 출력

    Args:
        stats: calculate_quality_stats 함수에서 반환된 통계
        title: 출력 제목
    """
    total = stats["total"]

    print(f"\n===== {title} (총 {total}개) =====")
    print("household:")
    valid_pct = stats["household_valid"] / total * 100
    print(f"  - 유효한 데이터: {stats['household_valid']} ({valid_pct:.1f}%)")
    zero_pct = stats["household_zero"] / total * 100
    print(f"  - 0인 데이터: {stats['household_zero']} ({zero_pct:.1f}%)")
    empty_pct = stats["household_empty"] / total * 100
    print(f"  - 빈 데이터: {stats['household_empty']} ({empty_pct:.1f}%)")
    print("좌표:")
    valid_coord_pct = stats["valid_coord"] / total * 100
    print(f"  - 유효한 좌표: {stats['valid_coord']} ({valid_coord_pct:.1f}%)")
    zero_coord_pct = stats["zero_coord"] / total * 100
    print(f"  - (0, 0) 좌표: {stats['zero_coord']} ({zero_coord_pct:.1f}%)")
    missing_coord_pct = stats["missing_coord"] / total * 100
    print(f"  - 누락된 좌표: {stats['missing_coord']} ({missing_coord_pct:.1f}%)")

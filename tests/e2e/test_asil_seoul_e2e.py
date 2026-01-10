"""ASIL 서울 아파트 E2E 테스트

서울 내 아파트 정보를 수집하고 CSV로 내보내는 E2E 테스트.
"""

import csv
import os

import pytest

from crawler.asil import AsilAptListCrawler

# 서울 샘플 동 코드 하드코딩
SEOUL_DONG_CODES = {
    "1168010100": "역삼동",
    "1168010200": "청담동",
    "1168010300": "삼성동",
    "1150010700": "사직동",
    "1156010500": "행당동",
}

MAX_APARTMENTS = 50

# ASIL API 필수 필드
REQUIRED_FIELDS = {"seq", "name", "dong", "dongname", "bungi"}


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


def _verify_apartment_record(apt: dict, index: int) -> None:
    """아파트 레코드 검증 헬퍼 함수

    Args:
        apt: 아파트 데이터 딕셔너리
        index: 레코드 인덱스 (에러 메시지용)
    """
    # 필수 필드 검증
    missing_fields = REQUIRED_FIELDS - set(apt.keys())
    assert not missing_fields, f"레코드 {index}: 필수 필드 누락: {missing_fields}"

    # 데이터 타입 검증
    assert isinstance(apt["seq"], str), f"레코드 {index}: seq는 문자열이어야 함"
    assert isinstance(apt["name"], str), f"레코드 {index}: name은 문자열이어야 함"
    assert isinstance(apt["dong"], str), f"레코드 {index}: dong은 문자열이어야 함"
    assert isinstance(apt["dongname"], str), f"레코드 {index}: dongname은 문자열이어야 함"

    # 필수 필드가 비어있지 않은지 검증
    assert apt["seq"].strip(), f"레코드 {index}: seq가 비어있음"
    assert apt["dong"].strip(), f"레코드 {index}: dong이 비어있음"


@pytest.mark.e2e
def test_crawl_seoul_apartments(tmp_path):
    """e2e: 서울 아파트 목록 크롤링 후 CSV 내보내기

    검증:
    1. ASIL API에서 성공적으로 데이터 가져옴
    2. 각 레코드가 필수 필드를 가짐
    3. 데이터 타입이 올바름
    4. 최대 50개 아파트로 제한됨
    5. CSV 파일이 생성됨
    6. CSV 내용이 파싱 가능함
    7. CSV 데이터 무결성 검증
    """
    all_apartments = []
    crawled_dongs = set()

    for dong_code, dong_name in SEOUL_DONG_CODES.items():
        if len(all_apartments) >= MAX_APARTMENTS:
            break

        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()

        # 결과가 있으면 동 이름 기록
        if results:
            crawled_dongs.add(dong_name)

        # 남은 용량만큼만 추가
        remaining = MAX_APARTMENTS - len(all_apartments)
        all_apartments.extend(results[:remaining])

    # 검증 1: 최소 1개 동에서 데이터를 가져왔는지
    assert len(crawled_dongs) > 0, "적어도 하나의 동에서 데이터를 가져와야 함"

    # 검증 2: 최소 1개 이상의 아파트 데이터
    assert len(all_apartments) > 0, "아파트 데이터가 없음"

    # 검증 3: 최대 50개 아파트로 제한됨
    assert len(all_apartments) <= 50, f"아파트 수가 50개를 초과: {len(all_apartments)}"

    # 검증 4: 각 레코드 필수 필드 및 데이터 타입 검증
    for idx, apt in enumerate(all_apartments):
        _verify_apartment_record(apt, idx)

    # 검증 5: 중복 없는 seq 확인 (seq는 아파트 고유 ID)
    seq_list = [apt["seq"] for apt in all_apartments]
    unique_seq_count = len(set(seq_list))
    assert unique_seq_count == len(seq_list), (
        f"중복된 seq 존재: {len(seq_list) - unique_seq_count}개"
    )

    # CSV 내보내기
    full_csv_path = tmp_path / "asil_seoul_apt.csv"
    export_to_csv(all_apartments, str(full_csv_path))

    # 검증 6: CSV 파일이 생성됨
    assert full_csv_path.exists(), f"CSV 파일이 생성되지 않음: {full_csv_path}"

    # 검증 7: CSV 내용이 파싱 가능함
    with open(full_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_records = list(reader)
        assert len(csv_records) == len(all_apartments), "CSV 레코드 수와 데이터 수 불일치"

    # 검증 8: CSV 헤더 검증
    with open(full_csv_path, encoding="utf-8") as f:
        header = f.readline().strip()
        assert header, "CSV 헤더가 비어있음"
        headers = header.split(",")
        assert "seq" in headers, "CSV 헤더에 'seq' 필드 누락"
        assert "name" in headers, "CSV 헤더에 'name' 필드 누락"
        assert "dongname" in headers, "CSV 헤더에 'dongname' 필드 누락"

    # 검증 9: CSV 데이터 무결성 - 모든 레코드의 seq가 원본과 일치
    csv_seq_list = [record["seq"] for record in csv_records]
    assert set(csv_seq_list) == set(seq_list), "CSV의 seq가 원본 데이터와 불일치"


@pytest.mark.unit
def test_export_to_csv_empty_data(tmp_path):
    """export_to_csv: 빈 데이터 처리 테스트"""
    filepath = tmp_path / "empty.csv"
    export_to_csv([], str(filepath))

    # 빈 데이터면 파일이 생성되지 않아야 함 (함수 내에서 early return)
    assert not filepath.exists(), "빈 데이터는 파일을 생성하지 않아야 함"


@pytest.mark.unit
def test_export_to_csv_single_record(tmp_path):
    """export_to_csv: 단일 레코드 내보내기 테스트"""
    data = [{"seq": "1", "name": "테스트", "dong": "1168010100", "dongname": "역삼동"}]
    filepath = tmp_path / "single.csv"
    export_to_csv(data, str(filepath))

    assert filepath.exists(), "CSV 파일이 생성되지 않음"

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        assert len(records) == 1, "단일 레코드만 있어야 함"
        assert records[0]["seq"] == "1", "seq 값 불일치"
        assert records[0]["name"] == "테스트", "name 값 불일치"


@pytest.mark.unit
def test_export_to_csv_multiple_records(tmp_path):
    """export_to_csv: 다중 레코드 내보내기 테스트"""
    data = [
        {"seq": "1", "name": "아파트1", "dong": "1168010100", "dongname": "역삼동"},
        {"seq": "2", "name": "아파트2", "dong": "1168010200", "dongname": "청담동"},
        {"seq": "3", "name": "아파트3", "dong": "1168010300", "dongname": "삼성동"},
    ]
    filepath = tmp_path / "multiple.csv"
    export_to_csv(data, str(filepath))

    assert filepath.exists(), "CSV 파일이 생성되지 않음"

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        assert len(records) == 3, "3개 레코드가 있어야 함"

        # 각 레코드 검증
        assert records[0]["seq"] == "1"
        assert records[1]["name"] == "아파트2"
        assert records[2]["dongname"] == "삼성동"


@pytest.mark.unit
def test_export_to_csv_creates_directory(tmp_path):
    """export_to_csv: 디렉토리 자동 생성 테스트"""
    data = [{"seq": "1", "name": "테스트"}]
    filepath = tmp_path / "subdir" / "nested" / "test.csv"

    # 디렉토리가 없는 상태
    assert not filepath.parent.exists(), "디렉토리가 존재하면 안 됨"

    export_to_csv(data, str(filepath))

    # 디렉토리가 생성되어야 함
    assert filepath.exists(), "파일이 생성되어야 함"
    assert filepath.parent.exists(), "부모 디렉토리가 생성되어야 함"


@pytest.mark.unit
def test_export_to_csv_utf8_encoding(tmp_path):
    """export_to_csv: UTF-8 인코딩 테스트 (한글 처리)"""
    data = [{"seq": "1", "name": "역삼동힐스테이트", "dongname": "서울시강남구역삼동"}]
    filepath = tmp_path / "korean.csv"
    export_to_csv(data, str(filepath))

    # UTF-8로 읽을 수 있어야 함
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
        assert "역삼동힐스테이트" in content, "한글이 제대로 인코딩되지 않음"
        assert "서울시강남구역삼동" in content, "한글이 제대로 인코딩되지 않음"

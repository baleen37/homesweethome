"""ASIL 서울 아파트 E2E 테스트

서울 내 아파트 정보를 수집하고 CSV로 내보내는 E2E 테스트.
"""

import pytest

from crawler.asil import AsilAptListCrawler
from tests.e2e.conftest import (
    SEOUL_DONG_CODES,
    _verify_csv_integrity,
    collect_apartments_from_dongs,
    export_to_csv,
    verify_apartment_record,
    verify_csv_file,
    verify_no_duplicate_seq,
)

MAX_APARTMENTS = 1


@pytest.mark.e2e
def test_crawl_seoul_apartments(tmp_path):
    """e2e: 서울 아파트 목록 크롤링 후 CSV 내보내기

    검증:
    1. ASIL API에서 성공적으로 데이터 가져옴
    2. 각 레코드가 필수 필드를 가짐
    3. 데이터 타입이 올바름
    4. 최대 1개 아파트로 제한됨
    5. CSV 파일이 생성됨
    6. CSV 내용이 파싱 가능함
    7. CSV 데이터 무결성 검증
    """
    # 데이터 수집
    all_apartments, crawled_dongs = collect_apartments_from_dongs(
        dong_codes=SEOUL_DONG_CODES,
        crawler_class=AsilAptListCrawler,
        max_apartments=MAX_APARTMENTS,
    )

    # 검증 1-3: 최소 데이터 및 레코드 검증
    assert len(crawled_dongs) > 0, "적어도 하나의 동에서 데이터를 가져와야 함"
    assert len(all_apartments) > 0, "아파트 데이터가 없음"
    assert len(all_apartments) <= 1, f"아파트 수가 1개를 초과: {len(all_apartments)}"

    for idx, apt in enumerate(all_apartments):
        verify_apartment_record(apt, idx)

    # 검증 4: 중복 없는 seq 확인
    verify_no_duplicate_seq(all_apartments)

    # CSV 내보내기 및 검증
    full_csv_path = tmp_path / "asil_seoul_apt.csv"
    export_to_csv(all_apartments, str(full_csv_path))
    _verify_csv_integrity(str(full_csv_path), all_apartments)


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

    csv_records = verify_csv_file(str(filepath), 1)
    assert csv_records[0]["seq"] == "1", "seq 값 불일치"
    assert csv_records[0]["name"] == "테스트", "name 값 불일치"


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

    csv_records = verify_csv_file(str(filepath), 3)
    assert csv_records[0]["seq"] == "1"
    assert csv_records[1]["name"] == "아파트2"
    assert csv_records[2]["dongname"] == "삼성동"


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

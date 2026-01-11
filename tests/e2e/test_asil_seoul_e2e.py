"""ASIL 서울 아파트 E2E 테스트

서울 내 아파트 정보를 수집하고 CSV로 내보내는 E2E 테스트.
"""

import pytest

from crawler.asil import AsilAptListCrawler
from crawler.utils.filter import FilterOptions, filter_records, get_filter_stats
from tests.e2e.conftest import (
    SEOUL_DONG_CODES,
    _verify_csv_integrity,
    calculate_quality_stats,
    collect_apartments_from_dongs,
    export_to_csv,
    print_quality_stats,
    verify_apartment_record,
    verify_csv_file,
    verify_no_duplicate_seq,
)

MAX_APARTMENTS = 50


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
    # 데이터 수집
    all_apartments, crawled_dongs = collect_apartments_from_dongs(
        dong_codes=SEOUL_DONG_CODES,
        crawler_class=AsilAptListCrawler,
        max_apartments=MAX_APARTMENTS,
    )

    # 검증 1-3: 최소 데이터 및 레코드 검증
    assert len(crawled_dongs) > 0, "적어도 하나의 동에서 데이터를 가져와야 함"
    assert len(all_apartments) > 0, "아파트 데이터가 없음"
    assert len(all_apartments) <= 50, f"아파트 수가 50개를 초과: {len(all_apartments)}"

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


@pytest.mark.e2e
def test_data_quality_analysis():
    """e2e: 실제 데이터 품질 분석

    ASIL API에서 실제로 받는 데이터의 품질을 분석합니다.
    - household=0인 데이터 비율
    - 좌표가 (0.0, 0.0)인 데이터 비율
    - 빈 문자열이나 None인 필드 패턴
    """
    all_data, _ = collect_apartments_from_dongs(
        dong_codes=SEOUL_DONG_CODES,
        crawler_class=AsilAptListCrawler,
    )

    # 최소 데이터 확보
    assert len(all_data) > 10, f"데이터 분석을 위해 최소 10개 이상 필요: {len(all_data)}개"

    # 통계 계산 및 출력
    stats = calculate_quality_stats(all_data)
    print_quality_stats(stats, "데이터 품질 분석 결과")

    # household=0인 데이터 샘플 출력
    if stats["household_zero"] > 0:
        print("\n[household=0인 데이터 샘플]")
        count = 0
        for apt in all_data:
            if apt.get("household") == "0":
                print(f"  - {apt.get('name')} (seq:{apt.get('seq')}, dong:{apt.get('dongname')})")
                count += 1
                if count >= 3:
                    break

    # 좌표가 (0, 0)인 데이터 샘플 출력
    if stats["zero_coord"] > 0:
        print("\n[좌표가 (0, 0)인 데이터 샘플]")
        count = 0
        for apt in all_data:
            lat = apt.get("lat")
            lng = apt.get("lng")
            if (lat == "0" or lat == "0.0") and (lng == "0" or lng == "0.0"):
                print(f"  - {apt.get('name')} (seq:{apt.get('seq')}, lat:{lat}, lng:{lng})")
                count += 1
                if count >= 3:
                    break


@pytest.mark.e2e
@pytest.mark.parametrize(
    "filter_option_name,filter_factory,check_household,check_coords",
    [
        ("Moderate", FilterOptions.moderate, True, False),
        ("Strict", FilterOptions.strict, True, True),
        ("Permissive", FilterOptions.permissive, False, False),
    ],
)
def test_filter_options(filter_option_name, filter_factory, check_household, check_coords):
    """e2e: 필터링 옵션으로 실제 데이터 필터링 테스트

    Parametrize:
    - moderate: household >= 1, 좌표 (0, 0) 허용
    - strict: household >= 1, 유효한 좌표만 (0, 0 제외)
    - permissive: 모든 데이터 유지 (household 제한 없음, 좌표 (0, 0) 허용)
    """
    all_data, _ = collect_apartments_from_dongs(
        dong_codes=SEOUL_DONG_CODES,
        crawler_class=AsilAptListCrawler,
    )

    # 최소 데이터 확보
    assert len(all_data) > 10, f"테스트를 위해 최소 10개 이상 필요: {len(all_data)}개"

    # 필터링
    filtered_data = filter_records(all_data, filter_factory())
    stats = get_filter_stats(len(all_data), len(filtered_data))

    # 결과 출력
    print(f"\n===== {filter_option_name} 필터링 결과 =====")
    print(f"원본 데이터: {stats['original_count']}개")
    print(f"필터링 후: {stats['filtered_count']}개")
    print(f"필터링 제외: {stats['removed_count']}개 ({stats['removal_rate']:.1f}%)")

    # household 검증
    if check_household:
        for apt in filtered_data:
            household = apt.get("household")
            assert household is not None and household != "" and household != "0", (
                f"필터링 후 household=0인 데이터 존재: {apt.get('name')}"
            )

    # 좌표 검증
    if check_coords:
        for apt in filtered_data:
            lat = apt.get("lat")
            lng = apt.get("lng")
            if lat is not None and lng is not None and lat != "" and lng != "":
                assert not (lat == "0" or lat == "0.0" or lng == "0" or lng == "0.0"), (
                    f"필터링 후 (0, 0) 좌표 데이터 존재: {apt.get('name')} (lat:{lat}, lng:{lng})"
                )

    # permissive는 이름이 없는 데이터만 필터링
    if filter_option_name == "Permissive":
        for apt in filtered_data:
            name = apt.get("name")
            assert name is not None and name.strip() != "", (
                f"필터링 후 이름이 없는 데이터 존재: seq={apt.get('seq')}"
            )

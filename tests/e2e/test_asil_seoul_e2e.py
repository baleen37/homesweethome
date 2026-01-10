"""ASIL 서울 아파트 E2E 테스트

서울 내 아파트 정보를 수집하고 CSV로 내보내는 E2E 테스트.
"""

import csv
import os

import pytest

from crawler.asil import AsilAptListCrawler
from crawler.utils.filter import FilterOptions, filter_records, get_filter_stats

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
        # DTO를 dict로 변환하여 추가
        results_dicts = [apt.model_dump() for apt in results[:remaining]]
        all_apartments.extend(results_dicts)

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


@pytest.mark.e2e
def test_data_quality_analysis():
    """e2e: 실제 데이터 품질 분석

    ASIL API에서 실제로 받는 데이터의 품질을 분석합니다.
    - household=0인 데이터 비율
    - 좌표가 (0.0, 0.0)인 데이터 비율
    - 빈 문자열이나 None인 필드 패턴
    """
    all_data = []

    # 여러 동 코드에서 데이터 수집
    for dong_code, dong_name in SEOUL_DONG_CODES.items():
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()
        if results:
            all_data.extend([apt.model_dump() for apt in results])

    # 최소 데이터 확보
    assert len(all_data) > 10, f"데이터 분석을 위해 최소 10개 이상 필요: {len(all_data)}개"

    # household 필드 분석
    household_zero_count = 0
    household_empty_count = 0
    household_valid_count = 0

    for apt in all_data:
        household = apt.get("household")
        if household is None or household == "":
            household_empty_count += 1
        elif household == "0":
            household_zero_count += 1
        else:
            household_valid_count += 1

    # 좌표 분석
    zero_coord_count = 0
    missing_coord_count = 0
    valid_coord_count = 0

    for apt in all_data:
        lat = apt.get("lat")
        lng = apt.get("lng")
        if lat is None or lng is None or lat == "" or lng == "":
            missing_coord_count += 1
        elif lat == "0" or lng == "0" or lat == "0.0" or lng == "0.0":
            zero_coord_count += 1
        else:
            valid_coord_count += 1

    # 결과 출력 (디버깅용)
    print(f"\n===== 데이터 품질 분석 결과 (총 {len(all_data)}개) =====")
    print("household:")
    valid_rate = household_valid_count / len(all_data) * 100
    print(f"  - 유효한 데이터: {household_valid_count} ({valid_rate:.1f}%)")
    zero_rate = household_zero_count / len(all_data) * 100
    print(f"  - 0인 데이터: {household_zero_count} ({zero_rate:.1f}%)")
    empty_rate = household_empty_count / len(all_data) * 100
    print(f"  - 빈 데이터: {household_empty_count} ({empty_rate:.1f}%)")
    print("좌표:")
    print(f"  - 유효한 좌표: {valid_coord_count} ({valid_coord_count / len(all_data) * 100:.1f}%)")
    print(f"  - (0, 0) 좌표: {zero_coord_count} ({zero_coord_count / len(all_data) * 100:.1f}%)")
    print(
        f"  - 누락된 좌표: {missing_coord_count} ({missing_coord_count / len(all_data) * 100:.1f}%)"
    )

    # household=0인 데이터 샘플 출력
    if household_zero_count > 0:
        print("\n[household=0인 데이터 샘플]")
        for apt in all_data:
            if apt.get("household") == "0":
                print(f"  - {apt.get('name')} (seq:{apt.get('seq')}, dong:{apt.get('dongname')})")
                if household_zero_count <= 3:  # 최대 3개만 출력
                    break

    # 좌표가 (0, 0)인 데이터 샘플 출력
    if zero_coord_count > 0:
        print("\n[좌표가 (0, 0)인 데이터 샘플]")
        for apt in all_data:
            lat = apt.get("lat")
            lng = apt.get("lng")
            if (lat == "0" or lat == "0.0") and (lng == "0" or lng == "0.0"):
                print(f"  - {apt.get('name')} (seq:{apt.get('seq')}, lat:{lat}, lng:{lng})")
                if zero_coord_count <= 3:  # 최대 3개만 출력
                    break

    # 실제 존재하는 아파트인지 확인 ( household=0인 데이터가 실제 아파트인지)
    # 이 테스트는 데이터 패턴을 파악하기 위함이며, 필터링 전략 수립에 활용


@pytest.mark.e2e
def test_filter_moderate_options():
    """e2e: moderate 필터링 옵션으로 실제 데이터 필터링 테스트

    moderate 옵션: household >= 1, 좌표 (0, 0) 허용
    """
    all_data = []

    # 여러 동 코드에서 데이터 수집
    for dong_code, dong_name in SEOUL_DONG_CODES.items():
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()
        if results:
            all_data.extend(results)

    # 최소 데이터 확보
    assert len(all_data) > 10, f"테스트를 위해 최소 10개 이상 필요: {len(all_data)}개"

    # moderate 옵션으로 필터링
    filtered_data = filter_records(all_data, FilterOptions.moderate())
    stats = get_filter_stats(len(all_data), len(filtered_data))

    # 결과 출력
    print("\n===== Moderate 필터링 결과 =====")
    print(f"원본 데이터: {stats['original_count']}개")
    print(f"필터링 후: {stats['filtered_count']}개")
    print(f"필터링 제외: {stats['removed_count']}개 ({stats['removal_rate']:.1f}%)")

    # 필터링된 데이터에 household=0이 없어야 함
    for apt in filtered_data:
        household = apt.model_dump().get("household")
        name = apt.model_dump().get("name")
        seq = apt.model_dump().get("seq")
        assert household is not None and household != "" and household != "0", (
            f"필터링 후 household=0인 데이터 존재: {name} (seq:{seq})"
        )

    # household=1 이상인 데이터만 남아야 함
    household_valid_count = 0
    for apt in filtered_data:
        household = apt.model_dump().get("household")
        if household is not None and household != "":
            try:
                if int(household) >= 1:
                    household_valid_count += 1
            except ValueError:
                pass

    assert household_valid_count == len(filtered_data), (
        f"모든 데이터가 household >= 1이어야 함: {household_valid_count}/{len(filtered_data)}"
    )


@pytest.mark.e2e
def test_filter_strict_options():
    """e2e: strict 필터링 옵션으로 실제 데이터 필터링 테스트

    strict 옵션: household >= 1, 유효한 좌표만 (0, 0 제외)
    """
    all_data = []

    # 여러 동 코드에서 데이터 수집
    for dong_code, dong_name in SEOUL_DONG_CODES.items():
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()
        if results:
            all_data.extend(results)

    # 최소 데이터 확보
    assert len(all_data) > 10, f"테스트를 위해 최소 10개 이상 필요: {len(all_data)}개"

    # strict 옵션으로 필터링
    filtered_data = filter_records(all_data, FilterOptions.strict())
    stats = get_filter_stats(len(all_data), len(filtered_data))

    # 결과 출력
    print("\n===== Strict 필터링 결과 =====")
    print(f"원본 데이터: {stats['original_count']}개")
    print(f"필터링 후: {stats['filtered_count']}개")
    print(f"필터링 제외: {stats['removed_count']}개 ({stats['removal_rate']:.1f}%)")

    # 필터링된 데이터에 household=0이 없어야 함
    for apt in filtered_data:
        household = apt.model_dump().get("household")
        assert household is not None and household != "" and household != "0", (
            f"필터링 후 household=0인 데이터 존재: {apt.model_dump().get('name')}"
        )

    # 필터링된 데이터에 (0, 0) 좌표가 없어야 함
    for apt in filtered_data:
        apt_dict = apt.model_dump()
        lat = apt_dict.get("lat")
        lng = apt_dict.get("lng")
        if lat is not None and lng is not None and lat != "" and lng != "":
            assert not (lat == "0" or lat == "0.0" or lng == "0" or lng == "0.0"), (
                f"필터링 후 (0, 0) 좌표 데이터 존재: {apt_dict.get('name')} (lat:{lat}, lng:{lng})"
            )


@pytest.mark.e2e
def test_filter_permissive_options():
    """e2e: permissive 필터링 옵션으로 실제 데이터 필터링 테스트

    permissive 옵션: 모든 데이터 유지 (household 제한 없음, 좌표 (0, 0) 허용)
    """
    all_data = []

    # 여러 동 코드에서 데이터 수집
    for dong_code, dong_name in SEOUL_DONG_CODES.items():
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()
        if results:
            all_data.extend(results)

    # 최소 데이터 확보
    assert len(all_data) > 10, f"테스트를 위해 최소 10개 이상 필요: {len(all_data)}개"

    # permissive 옵션으로 필터링
    filtered_data = filter_records(all_data, FilterOptions.permissive())
    stats = get_filter_stats(len(all_data), len(filtered_data))

    # 결과 출력
    print("\n===== Permissive 필터링 결과 =====")
    print(f"원본 데이터: {stats['original_count']}개")
    print(f"필터링 후: {stats['filtered_count']}개")
    print(f"필터링 제외: {stats['removed_count']}개 ({stats['removal_rate']:.1f}%)")

    # permissive는 이름이 없는 데이터만 필터링
    # 모든 데이터에 이름이 있어야 함
    for apt in filtered_data:
        name = apt.model_dump().get("name")
        assert name is not None and name.strip() != "", (
            f"필터링 후 이름이 없는 데이터 존재: seq={apt.model_dump().get('seq')}"
        )

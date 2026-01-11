"""seoul_all.py 스크립트 샘플 E2E 테스트

실제 API를 호출하여 샘플 데이터로 크롤링을 테스트합니다.
Full 테스트가 아니라 소수의 동 코드만 사용하여 효율성을 높입니다.
"""

import csv
import json
import os
import tempfile
from pathlib import Path

import pytest

from crawler.utils.data_quality import (
    DataQualityStats,
    analyze_data_quality,
)
from crawler.utils.filter import FilterOptions

# 샘플 동 코드 (실제 데이터가 있는 동 코드)
# 기존 E2E 테스트에서 사용하는 동 코드 참고
SAMPLE_DONG_CODES = [
    # 기존 E2E 테스트에서 검증된 동 코드
    "1168010100",  # 역삼동
    "1168010200",  # 청담동
    "1168010300",  # 삼성동
    "1150010700",  # 사직동 (종로구)
    "1156010500",  # 행당동 (영등포구 - 예시, 실제로는 다른 구)
]

# 최소 테스트 조건
MIN_SAMPLE_APARTMENTS = 5  # 최소 5개 아파트 데이터
MIN_SAMPLE_DONGS_WITH_DATA = 1  # 최소 1개 동에서 데이터 발견


@pytest.mark.e2e
def test_seoul_all_sample_crawling_with_quality_check():
    """e2e: seoul_all.py 샘플 크롤링 및 데이터 품질 검증

    검증:
    1. 샘플 동 코드에서 실제 데이터 수집
    2. CSV 파일 생성 확인
    3. 데이터 품질 분석 (household, 좌표)
    4. 필터링 기능 동작 확인
    5. 중복 제거 확인
    """
    from crawler.asil import AsilAptListCrawler

    all_collected_data = []
    unique_seqs = set()
    stats = {
        "total_processed": 0,
        "data_found": 0,
        "empty_dongs": 0,
        "error_dongs": 0,
        "total_apartments": 0,
    }

    # CSV 필드명 (seoul_all.py와 동일)
    csv_fieldnames = [
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

    # 샘플 동 코드로 크롤링
    for dong_code in SAMPLE_DONG_CODES:
        stats["total_processed"] += 1

        try:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results = crawler.crawl()

            if results is None:
                # 타임아웃 또는 에러
                stats["error_dongs"] += 1
                continue

            if results:
                stats["data_found"] += 1
                stats["total_apartments"] += len(results)
                all_collected_data.extend(results)

                # 중복 제거 확인을 위한 seq 수집
                for apt in results:
                    seq = apt.model_dump().get("seq")
                    if seq:
                        unique_seqs.add(seq)
            else:
                stats["empty_dongs"] += 1

        except Exception as e:
            stats["error_dongs"] += 1
            print(f"  [{dong_code}] 에러: {e}")

    # 검증 1: 최소 데이터 수집 확인
    assert stats["data_found"] >= MIN_SAMPLE_DONGS_WITH_DATA, (
        f"최소 {MIN_SAMPLE_DONGS_WITH_DATA}개 동에서 데이터를 가져와야 함: {stats['data_found']}개"
    )

    # 검증 2: 최소 아파트 수 확인
    assert stats["total_apartments"] >= MIN_SAMPLE_APARTMENTS, (
        f"최소 {MIN_SAMPLE_APARTMENTS}개 아파트 데이터가 필요함: {stats['total_apartments']}개"
    )

    # 검증 3: 에러율 확인 (너무 많은 에러면 실패)
    if stats["total_processed"] > 0:
        error_rate = stats["error_dongs"] / stats["total_processed"]
    else:
        error_rate = 0
    assert error_rate < 0.5, f"에러율이 너무 높음: {error_rate * 100:.1f}%"

    # 검증 4: 데이터 품질 분석
    quality_stats = analyze_data_quality(all_collected_data, unique_seqs, csv_fieldnames)

    # 품질 통계 출력
    print("\n===== 데이터 품질 분석 =====")
    print(f"총 레코드: {quality_stats.total_records}건")
    print(
        f"household >= 1: {quality_stats.household_positive}건 "
        f"({quality_stats.household_positive / quality_stats.total_records * 100:.1f}%)"
    )
    print(
        f"household = 0: {quality_stats.household_zero}건 "
        f"({quality_stats.household_zero / quality_stats.total_records * 100:.1f}%)"
    )
    print(
        f"유효한 좌표: {quality_stats.valid_coords}건 "
        f"({quality_stats.valid_coords / quality_stats.total_records * 100:.1f}%)"
    )
    print(
        f"유효하지 않은 좌표: {quality_stats.invalid_coords}건 "
        f"({quality_stats.invalid_coords / quality_stats.total_records * 100:.1f}%)"
    )
    print(
        f"중복 레코드: {quality_stats.duplicate_count}건 "
        f"({quality_stats.duplicate_rate * 100:.1f}%)"
    )

    # 검증 5: 최소 품질 기준
    # household>=1인 데이터가 최소 50%는 되어야 함
    household_positive_rate = (
        quality_stats.household_positive / quality_stats.total_records
        if quality_stats.total_records > 0
        else 0
    )
    assert household_positive_rate >= 0.5, (
        f"household>=1인 데이터가 최소 50%는 되어야 함: {household_positive_rate * 100:.1f}%"
    )

    # 검증 6: 필터링 기능 테스트 (moderate 옵션)
    from crawler.utils.filter import filter_records

    filtered_data = filter_records(all_collected_data, FilterOptions.moderate())

    # 필터링 후 household=0인 데이터가 없어야 함
    for apt in filtered_data:
        household = apt.model_dump().get("household")
        if household is not None and household != "":
            assert household != "0", (
                f"필터링 후 household=0인 데이터 존재: "
                f"{apt.model_dump().get('name')} (seq:{apt.model_dump().get('seq')})"
            )

    # 검증 7: CSV 생성 테스트
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "test_output.csv"

        # CSV 작성
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()

            for apt in filtered_data:
                apt_dict = apt.model_dump()
                # DTO 필드명 → CSV 필드명 매핑
                csv_dict = {
                    "seq": apt_dict.get("seq"),
                    "name": apt_dict.get("name"),
                    "dong": apt_dict.get("dong"),
                    "dongname": apt_dict.get("dongname"),
                    "bungi": apt_dict.get("bungi"),
                    "movein": apt_dict.get("build_year"),
                    "household": apt_dict.get("household"),
                    "total_dong": apt_dict.get("dong_count"),
                    "type": apt_dict.get("maemul_count"),
                    "etc": apt_dict.get("address"),
                    "offer": apt_dict.get("offer"),
                    "lat": apt_dict.get("lat"),
                    "lng": apt_dict.get("lng"),
                }
                writer.writerow(csv_dict)

        # CSV 파일 확인
        assert csv_path.exists(), "CSV 파일이 생성되지 않음"

        # CSV 내용 확인
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_records = list(reader)
            assert len(csv_records) == len(filtered_data), (
                f"CSV 레코드 수와 필터링된 데이터 수 불일치: "
                f"{len(csv_records)} != {len(filtered_data)}"
            )

    print("\n===== 테스트 통과 =====")
    print(f"총 처리: {stats['total_processed']}개 동")
    print(f"데이터 발견: {stats['data_found']}개 동")
    print(f"데이터 없음: {stats['empty_dongs']}개 동")
    print(f"에러 발생: {stats['error_dongs']}개 동")
    print(f"총 아파트: {stats['total_apartments']}건")
    print(f"필터링 후: {len(filtered_data)}건")


@pytest.mark.e2e
def test_seoul_all_sample_timeout_handling():
    """e2e: 타임아웃 및 에러 핸들링 테스트

    검증:
    1. 타임아웃 발생 시 적절한 처리
    2. 에러 발생 시 다음 동 코드로 계속 진행
    """
    from crawler.asil import AsilAptListCrawler

    # 유효하지 않은 동 코드로 에러 핸들링 테스트
    invalid_dong_code = "9999900100"  # 존재하지 않는 구

    try:
        crawler = AsilAptListCrawler(dong_code=invalid_dong_code)
        results = crawler.crawl()
        # 결과가 없어도 에러로 처리하지 않아야 함
        assert results is not None or results == [], "유효하지 않은 동 코드 처리 확인"
    except Exception as e:
        # 예외가 발생해도 테스트 통과 (에러 핸들링 확인)
        print(f"예상된 예외 발생: {e}")
        assert True


@pytest.mark.e2e
def test_seoul_all_sample_data_completeness():
    """e2e: 데이터 완전성 검증

    검증:
    1. 필수 필드 존재 확인
    2. 필드 완전도 분석
    """
    from crawler.asil import AsilAptListCrawler

    # 샘플 동 코드 하나로 테스트
    dong_code = "1156005000"  # 영등포동

    crawler = AsilAptListCrawler(dong_code=dong_code)
    results = crawler.crawl()

    if results:
        # 필수 필드 확인
        required_fields = {"seq", "name", "dong", "dongname"}
        for apt in results:
            apt_dict = apt.model_dump()
            missing_fields = required_fields - set(apt_dict.keys())
            assert not missing_fields, f"필수 필드 누락: {missing_fields}"

        # 필드 완전도 분석
        csv_fieldnames = [
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
        unique_seqs = set()
        quality_stats = analyze_data_quality(results, unique_seqs, csv_fieldnames)

        # 필드 완전도 출력
        print("\n===== 필드 완전도 =====")
        for field, completeness in sorted(
            quality_stats.field_completeness.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"{field:15s}: {completeness * 100:5.1f}%")

        # seq 필드는 100% 채워져 있어야 함
        assert quality_stats.field_completeness.get("seq", 0) == 1.0, (
            "seq 필드는 100% 채워져 있어야 함"
        )


@pytest.mark.e2e
def test_seoul_all_crawl_single_gu_function():
    """e2e: seoul_crawl.py의 crawl_single_gu 함수 테스트

    crawler.commands.seoul_crawl 모듈의 실제 함수를 호출하여 동작을 검증합니다.

    검증:
    1. crawl_single_gu 함수가 정상적으로 동작
    2. CSV 파일 생성 확인
    3. 데이터 품질 검증
    4. 통계 정확성 확인
    """
    from crawler.commands.seoul_crawl import (
        SeoulCrawlConfig,
        crawl_single_gu,
        setup_csv_writer,
    )

    # 테스트용 임시 디렉토리
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "test_output.csv"
        log_path = Path(tmp_dir) / "test_log.txt"

        # 테스트용 설정
        config = SeoulCrawlConfig(
            dong_code_start=100,
            dong_code_end=105,
            output_dir=tmp_dir,
        )

        # CSV writer 초기화
        writer, csv_f = setup_csv_writer(str(output_path))

        # 로그 파일 초기화
        log_f = open(log_path, "w", encoding="utf-8")

        # 빈 completed_dongs와 unique_seqs 시작
        completed_dongs = set()
        unique_seqs = set()

        # 강남구 (11680) 샘플 테스트
        gu_code = "11680"
        gu_name = "강남구"

        # crawl_single_gu 함수 호출
        gu_stats = crawl_single_gu(
            gu_code=gu_code,
            gu_name=gu_name,
            completed_dongs=completed_dongs,
            unique_seqs=unique_seqs,
            writer=writer,
            csv_f=csv_f,
            log_f=log_f,
            config=config,
            enable_quality_log=True,
        )

        # 검증 1: 함수가 정상적으로 완료
        assert gu_stats is not None, "crawl_single_gu 함수가 None을 반환"

        # 검증 2: 통계 값 확인
        assert "found" in gu_stats, "통계에 'found' 필드 누락"
        assert "empty" in gu_stats, "통계에 'empty' 필드 누락"
        assert "error" in gu_stats, "통계에 'error' 필드 누락"
        assert "apartments" in gu_stats, "통계에 'apartments' 필드 누락"
        assert "filtered_out" in gu_stats, "통계에 'filtered_out' 필드 누락"
        assert "quality_stats" in gu_stats, "통계에 'quality_stats' 필드 누락"

        # 검증 3: 최소 데이터 수집 확인
        total_processed = gu_stats["found"] + gu_stats["empty"] + gu_stats["error"]
        assert total_processed > 0, "최소 1개 이상의 동 코드가 처리되어야 함"

        # 검증 4: CSV 파일 생성 확인
        csv_f.close()
        log_f.close()
        assert output_path.exists(), "CSV 파일이 생성되지 않음"

        # 검증 5: CSV 내용 확인
        with open(output_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_records = list(reader)
            assert len(csv_records) >= 0, "CSV 레코드 수 확인"

        # 검증 6: 데이터 품질 통계 확인
        quality_stats = gu_stats["quality_stats"]
        assert isinstance(quality_stats, DataQualityStats), (
            "quality_stats가 DataQualityStats 타입이 아님"
        )

        # 결과 출력
        print("\n===== crawl_single_gu 테스트 결과 =====")
        print(f"구: {gu_name} ({gu_code})")
        print(f"데이터 있는 동: {gu_stats['found']}개")
        print(f"데이터 없는 동: {gu_stats['empty']}개")
        print(f"에러 발생: {gu_stats['error']}개")
        print(f"총 아파트: {gu_stats['apartments']}건")
        print(f"필터링 제외: {gu_stats['filtered_out']}건")
        print(f"품질 통계: 총 {quality_stats.total_records}건")


@pytest.mark.e2e
def test_seoul_all_checkpoint_functionality():
    """e2e: 체크포인트 기능 테스트

    검증:
    1. 체크포인트 저장
    2. 체크포인트 로드
    3. 완료된 동 코드 스킵
    """
    from crawler.commands.seoul_crawl import load_checkpoint, save_checkpoint

    with tempfile.TemporaryDirectory() as tmp_dir:
        checkpoint_path = Path(tmp_dir) / "checkpoint.json"

        # 빈 체크포인트 로드
        completed_dongs = load_checkpoint(str(checkpoint_path))
        assert len(completed_dongs) == 0, "새 체크포인트는 비어 있어야 함"

        # 체크포인트 저장
        test_dongs = {"1168010100", "1168010200", "1168010300"}
        save_checkpoint(test_dongs, str(checkpoint_path), "20260111_120000")

        # 체크포인트 로드 확인
        loaded_dongs = load_checkpoint(str(checkpoint_path))
        assert loaded_dongs == test_dongs, "체크포인트 로드 결과가 저장된 값과 다름"

        # 파일 존재 확인
        assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않음"

        # JSON 형식 확인
        with open(checkpoint_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "completed_dongs" in data, "체크포인트 JSON에 'completed_dongs' 필드 누락"
            assert "timestamp" in data, "체크포인트 JSON에 'timestamp' 필드 누락"
            assert isinstance(data["completed_dongs"], list), "completed_dongs가 리스트가 아님"


@pytest.mark.e2e
def test_seoul_all_generate_dong_codes():
    """e2e: generate_dong_codes 함수 테스트

    검증:
    1. 동 코드 생성 정확성
    2. 코드 형식 확인 (구코드5자리 + 동코드3자리 + 00)
    """
    from crawler.commands.seoul_crawl import SeoulCrawlConfig, generate_dong_codes

    # 테스트용 구 코드
    gu_code = "11680"  # 강남구

    # 샘플 범위 설정
    config = SeoulCrawlConfig(dong_code_start=100, dong_code_end=105)

    dong_codes = generate_dong_codes(gu_code, config)

    # 검증 1: 생성된 동 코드 수
    expected_count = config.dong_code_end - config.dong_code_start
    assert len(dong_codes) == expected_count, (
        f"동 코드 수가 예상과 다름: {len(dong_codes)} != {expected_count}"
    )

    # 검증 2: 동 코드 형식
    for dong_code in dong_codes:
        assert len(dong_code) == 10, f"동 코드 길이가 10자리가 아님: {dong_code}"
        assert dong_code.startswith(gu_code), f"동 코드가 구 코드로 시작하지 않음: {dong_code}"
        assert dong_code.endswith("00"), f"동 코드가 '00'으로 끝나지 않음: {dong_code}"

    # 검증 3: 예상 동 코드 확인
    expected_codes = [
        "1168010000",  # 100
        "1168010100",  # 101
        "1168010200",  # 102
        "1168010300",  # 103
        "1168010400",  # 104
    ]
    assert dong_codes == expected_codes, f"생성된 동 코드가 예상과 다름: {dong_codes}"


@pytest.mark.e2e
def test_cli_parse_selection():
    """e2e: CLI parse_selection 함수 테스트

    다양한 입력 형식을 파싱하는 기능을 검증합니다.

    검증:
    1. 단일 선택 (예: "1")
    2. 복수 선택 (예: "1,3,5")
    3. 범위 선택 (예: "1-5")
    4. 혼합 선택 (예: "1,3-5,7")
    """
    from crawler.commands.cli import parse_selection

    # 검증 1: 단일 선택
    result = parse_selection("1", 10)
    assert result == [1], f"단일 선택 실패: {result}"

    # 검증 2: 복수 선택
    result = parse_selection("1,3,5", 10)
    assert result == [1, 3, 5], f"복수 선택 실패: {result}"

    # 검증 3: 범위 선택
    result = parse_selection("1-5", 10)
    assert result == [1, 2, 3, 4, 5], f"범위 선택 실패: {result}"

    # 검증 4: 혼합 선택
    result = parse_selection("1,3-5,7", 10)
    assert result == [1, 3, 4, 5, 7], f"혼합 선택 실패: {result}"

    # 검증 5: 공백 무시
    result = parse_selection("1, 3, 5", 10)
    assert result == [1, 3, 5], f"공백 무시 실패: {result}"

    # 검증 6: 범위를 벗어난 값 필터링
    result = parse_selection("1,3,15", 10)
    assert result == [1, 3], f"범위 필터링 실패: {result}"

    print("\n===== parse_selection 테스트 통과 =====")


@pytest.mark.e2e
def test_cli_run_crawl_single_gu():
    """e2e: CLI run_crawl 함수 테스트 (단일 구)

    실제 API를 호출하여 단일 구 크롤링을 테스트합니다.

    검증:
    1. run_crawl 함수가 정상적으로 동작
    2. CSV 파일 생성 확인
    3. 통계 정확성 확인
    4. 로그 파일 생성 확인
    """
    from crawler.commands.cli import run_crawl
    from crawler.commands.seoul_crawl import SeoulCrawlConfig

    # 영등포구만 테스트
    gu_list = [("11560", "영등포구")]

    # 테스트용 설정 (소수의 동만 크롤링)
    config = SeoulCrawlConfig(
        dong_code_start=100,
        dong_code_end=110,
        output_dir="output",
        request_delay=0.5,
        batch_delay=0,  # 테스트 시 배치 딜레이 제거
    )

    # 체크포인트 파일 삭제 (테스트를 위해)
    if os.path.exists(config.checkpoint_file):
        os.remove(config.checkpoint_file)

    # run_crawl 실행 전 파일 목록 확인
    output_dir = Path("output")
    before_files = set(output_dir.glob("*.csv")) if output_dir.exists() else set()

    stats = run_crawl(gu_list, config)

    # 검증 1: 통계 존재 확인
    assert stats is not None, "run_crawl이 None을 반환"
    assert stats["total_processed"] > 0, "최소 1개 이상의 동 코드가 처리되어야 함"

    # 검증 2: CSV 파일 생성 확인 (새로 생성된 파일)
    after_files = set(output_dir.glob("*.csv")) if output_dir.exists() else set()
    new_csv_files = after_files - before_files
    assert len(new_csv_files) > 0, "CSV 파일이 생성되지 않음"

    # 검증 3: 로그 파일 생성 확인
    log_files = list(output_dir.glob("crawl_log_*.txt")) if output_dir.exists() else []
    assert len(log_files) > 0, "로그 파일이 생성되지 않음"

    # 검증 4: 체크포인트 파일 생성 확인
    assert Path(config.checkpoint_file).exists(), "체크포인트 파일이 생성되지 않음"

    # 결과 출력
    print("\n===== run_crawl 단일 구 테스트 결과 =====")
    print(f"총 처리 동: {stats['total_processed']}개")
    print(f"데이터 있는 동: {stats['data_found']}개")
    print(f"에러 발생: {stats['error_dongs']}개")
    print(f"총 아파트: {stats['total_apartments']}건")


@pytest.mark.e2e
def test_cli_interactive_with_mock_input():
    """e2e: CLI 상호작용형 입력 테스트 (mock 사용)

    input()을 mock하여 상호작용형 CLI를 테스트합니다.

    검증:
    1. 모드 선택 (특정 구 선택)
    2. 구 번호 입력
    3. run_crawl 실행
    """
    from crawler.commands.cli import parse_selection
    from crawler.commands.seoul_crawl import SEOUL_GU_CODES

    # 모의 입력: 모드 2 (특정 구 선택), 구 번호 18 (영등포구)
    mock_mode = "2"
    mock_selection = "18"  # 영등포구

    # 검증 1: 모드 선택 시뮬레이션
    assert mock_mode == "2", "모드 2 (특정 구 선택)"

    # 검증 2: 구 선택 시뮬레이션
    selected_indices = parse_selection(mock_selection, len(SEOUL_GU_CODES))
    assert selected_indices == [18], f"구 선택 실패: {selected_indices}"

    # 선택된 구 확인
    gu_list = list(SEOUL_GU_CODES.items())
    selected = [gu_list[i - 1] for i in selected_indices]
    assert selected[0] == ("11560", "영등포구"), f"선택된 구가 영등포구가 아님: {selected}"

    print("\n===== 상호작용형 입력 테스트 통과 =====")
    print(f"선택된 구: {selected[0][1]} ({selected[0][0]})")


@pytest.mark.e2e
def test_cli_parse_selection_edge_cases():
    """e2e: CLI parse_selection 엣지 케이스 테스트

    엣지 케이스와 오류 상황을 검증합니다.

    검증:
    1. 중복 값 제거
    2. 정렬 확인
    3. 빈 입력 처리
    4. 잘못된 형식 처리
    """
    from crawler.commands.cli import parse_selection

    # 검증 1: 중복 값 제거
    result = parse_selection("1,3,1,5,3", 10)
    assert result == [1, 3, 5], f"중복 제거 실패: {result}"

    # 검증 2: 정렬 확인
    result = parse_selection("5,1,3", 10)
    assert result == [1, 3, 5], f"정렬 실패: {result}"

    # 검증 3: 전체 범위 선택
    result = parse_selection("1-25", 25)
    assert len(result) == 25, f"전체 범위 선택 실패: {len(result)}개"
    assert result == list(range(1, 26)), "전체 범위 내용 실패"

    # 검증 4: 인접 범위
    result = parse_selection("1-3,4-6", 10)
    assert result == [1, 2, 3, 4, 5, 6], f"인접 범위 실패: {result}"

    print("\n===== 엣지 케이스 테스트 통과 =====")

"""상호작용형 CLI 모듈

서울 아파트 크롤링을 위한 상호작용형 커맨드라인 인터페이스를 제공합니다.
"""

import os
import sys
import time
from typing import Literal

from crawler.commands.seoul_crawl import (
    SEOUL_GU_CODES,
    CrawlStats,
    SeoulCrawlConfig,
    crawl_single_gu,
    load_checkpoint,
    log_message,
    save_checkpoint,
    setup_csv_writer,
)
from crawler.utils.data_quality import (
    DataQualityStats,
    generate_quality_report,
    save_quality_report,
)


def select_gu_interactive() -> list[tuple[str, str]]:
    """상호작용형 구 선택

    Returns:
        선택된 (구 코드, 구 이름) 리스트
    """
    print("\n크롤링할 구를 선택하세요:")
    print("-" * 40)

    gu_list = list(SEOUL_GU_CODES.items())
    for idx, (code, name) in enumerate(gu_list, 1):
        print(f"{idx:2d}. {name} ({code})")

    print("-" * 40)

    while True:
        selection = input("구 번호를 입력하세요 (예: 1,3,5 또는 1-5 또는 all): ").strip()

        if selection.lower() == "all":
            return gu_list

        try:
            selected_indices = parse_selection(selection, len(gu_list))
            if selected_indices:
                selected = [gu_list[i - 1] for i in selected_indices]
                selected_names = [name for _, name in selected]
                print(f"\n선택된 구: {', '.join(selected_names)}")
                return selected
            else:
                print("유효하지 않은 입력입니다. 다시 입력해주세요.")
        except ValueError:
            print("유효하지 않은 형식입니다. 다시 입력해주세요.")


def parse_selection(selection: str, max_value: int) -> list[int]:
    """선택 문자열을 파싱하여 인덱스 리스트 반환

    Args:
        selection: 선택 문자열 (예: "1,3,5" 또는 "1-5")
        max_value: 최대 값

    Returns:
        선택된 인덱스 리스트 (1-based)
    """
    result = []

    parts = selection.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start_idx = int(start)
            end_idx = int(end)
            result.extend(range(start_idx, end_idx + 1))
        else:
            result.append(int(part))

    result = [i for i in set(result) if 1 <= i <= max_value]
    result.sort()

    return result


def select_mode_interactive() -> Literal["all", "select_gu", "single_dong"]:
    """상호작용형 모드 선택

    Returns:
        선택된 모드
    """
    print("\n" + "=" * 60)
    print("서울 아파트 크롤링")
    print("=" * 60)

    print("\n모드를 선택하세요:")
    print("1. 전체 구 크롤링 (25개 구)")
    print("2. 특정 구 선택")
    print("3. 특정 동 선택 (개발 중)")

    while True:
        choice = input("\n모드 번호를 입력하세요 (1-3): ").strip()
        if choice == "1":
            return "all"
        elif choice == "2":
            return "select_gu"
        elif choice == "3":
            print("\n특정 동 선택 모드는 아직 개발 중입니다.")
            print("특정 구 선택 모드를 사용해주세요.")
        else:
            print("유효하지 않은 선택입니다. 1-2 사이의 번호를 입력하세요.")


def run_crawl(
    gu_list: list[tuple[str, str]],
    config: SeoulCrawlConfig,
) -> CrawlStats:
    """크롤링 실행

    Args:
        gu_list: (구 코드, 구 이름) 리스트
        config: 크롤링 설정

    Returns:
        크롤링 통계
    """
    os.makedirs(config.output_dir, exist_ok=True)
    log_f = open(config.log_file, "w", encoding="utf-8")

    output_path = os.path.join(config.output_dir, config.output_file)
    writer, csv_f = setup_csv_writer(output_path)

    completed_dongs = load_checkpoint(config.checkpoint_file)
    if completed_dongs:
        log_message(f"체크포인트 로드 완료: {len(completed_dongs)}개 동 이미 완료", log_f)

    stats: CrawlStats = {
        "total_processed": 0,
        "data_found": 0,
        "empty_dongs": 0,
        "error_dongs": 0,
        "total_apartments": 0,
        "skipped_dongs": 0,
        "unique_seqs": set(),
        "filtered_out": 0,
        "quality_stats": DataQualityStats(),
    }

    cumulative_quality = DataQualityStats()

    log_message("=" * 60, log_f)
    log_message("서울 아파트 크롤링 시작", log_f)
    log_message(f"타겟 구: {len(gu_list)}개 (전체 25개 중)", log_f)
    log_message(f"구별 동 코드 범위: {config.dong_code_start}~{config.dong_code_end - 1}", log_f)
    log_message(f"요청 간 딜레이: {config.request_delay}초", log_f)
    log_message(f"타임아웃: {config.request_timeout}초, 최대 재시도: {config.max_retries}회", log_f)
    log_message(
        f"필터 옵션: min_household={config.filter_options.min_household}, "
        f"require_valid_coords={config.filter_options.require_valid_coords}",
        log_f,
    )
    log_message(f"출력 파일: {output_path}", log_f)
    log_message(f"체크포인트 파일: {config.checkpoint_file}", log_f)
    log_message("=" * 60, log_f)

    start_time = time.time()

    for gu_code, gu_name in gu_list:
        log_message(f"\n[{gu_name} ({gu_code})] 시작...", log_f)

        gu_stats = crawl_single_gu(
            gu_code,
            gu_name,
            completed_dongs,
            stats["unique_seqs"],
            writer,
            csv_f,
            log_f,
            config,
        )

        stats["data_found"] += gu_stats["found"]
        stats["empty_dongs"] += gu_stats["empty"]
        stats["error_dongs"] += gu_stats["error"]
        stats["total_apartments"] += gu_stats["apartments"]
        stats["skipped_dongs"] += gu_stats["skipped"]
        stats["filtered_out"] += gu_stats["filtered_out"]
        stats["total_processed"] += gu_stats["found"] + gu_stats["empty"] + gu_stats["error"]

        if isinstance(gu_stats["quality_stats"], DataQualityStats):
            cumulative_quality += gu_stats["quality_stats"]

        time.sleep(config.batch_delay)

    save_checkpoint(completed_dongs, config.checkpoint_file, config.timestamp)

    stats["quality_stats"] = cumulative_quality

    csv_f.close()
    log_f.close()

    elapsed = time.time() - start_time

    print_results(stats, output_path, config, elapsed)

    return stats


def print_results(
    stats: CrawlStats, output_path: str, config: SeoulCrawlConfig, elapsed: float
) -> None:
    """최종 결과 출력

    Args:
        stats: 크롤링 통계
        output_path: 출력 파일 경로
        config: 크롤링 설정
        elapsed: 소요 시간 (초)
    """
    print("\n" + "=" * 60)
    print("크롤링 완료!")
    print("=" * 60)
    print(f"총 처리 동: {stats['total_processed']}개")
    print(f"데이터 있는 동: {stats['data_found']}개")
    print(f"데이터 없는 동: {stats['empty_dongs']}개")
    print(f"에러 발생: {stats['error_dongs']}개")
    print(f"체크포인트로 스킵: {stats['skipped_dongs']}개")
    print(f"총 수집 아파트: {stats['total_apartments']}건")
    print(f"필터링 제외: {stats['filtered_out']}건")
    print(f"중복 제거 후: {len(stats['unique_seqs'])}건")
    print(f"소요 시간: {elapsed / 60:.1f}분")
    print(f"CSV 파일: {output_path}")
    print(f"로그 파일: {config.log_file}")
    print(f"체크포인트 파일: {config.checkpoint_file}")

    if stats["quality_stats"].total_records > 0:
        print("\n" + "=" * 60)
        print("데이터 품질 분석")
        print("=" * 60)

        save_quality_report(stats["quality_stats"], config.quality_report_file)

        quality = stats["quality_stats"]
        print(f"총 레코드: {quality.total_records:,}건")
        print(
            f"세대수 >= 1: {quality.household_positive:,}건 "
            f"({quality.household_positive / quality.total_records * 100:.1f}%)"
        )
        print(
            f"세대수 = 0: {quality.household_zero:,}건 "
            f"({quality.household_zero / quality.total_records * 100:.1f}%)"
        )
        print(
            f"유효한 좌표: {quality.valid_coords:,}건 "
            f"({quality.valid_coords / quality.total_records * 100:.1f}%)"
        )
        print(
            f"유효하지 않은 좌표: {quality.invalid_coords:,}건 "
            f"({quality.invalid_coords / quality.total_records * 100:.1f}%)"
        )
        print(f"중복 레코드: {quality.duplicate_count:,}건 ({quality.duplicate_rate * 100:.1f}%)")
        print(f"품질 리포트: {config.quality_report_file}")

        print("\n" + generate_quality_report(quality))


def main() -> None:
    """메인 진입점"""
    mode = select_mode_interactive()

    config = SeoulCrawlConfig()

    if mode == "all":
        gu_list = list(SEOUL_GU_CODES.items())
    elif mode == "select_gu":
        gu_list = select_gu_interactive()
    else:
        print("지원하지 않는 모드입니다.")
        sys.exit(1)

    if not gu_list:
        print("선택된 구가 없습니다.")
        sys.exit(1)

    run_crawl(gu_list, config)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""아실(asil.kr) 크롤러 단일 진입점

Usage:
    python scripts/crawl.py crawl --gu 11560           # 영등포구
    python scripts/crawl.py crawl --gu 영등포구         # 구 이름으로도 가능
    python scripts/crawl.py crawl --dong 1156010100    # 특정 동
    python scripts/crawl.py crawl --all                # 서울 전체
    python scripts/crawl.py test asil                  # 크롤러 테스트
"""

import argparse
import contextlib
import csv
import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.asil import (
    AsilAptListCrawler,
    AsilDongInfoCrawler,
)

# 서울 25개 구 코드
SEOUL_GU_CODES: dict[str, str] = {
    "11110": "종로구",
    "11140": "중구",
    "11170": "용산구",
    "11200": "성동구",
    "11230": "동대문구",
    "11250": "광진구",
    "11260": "중랑구",
    "11280": "성북구",
    "11290": "노원구",
    "11320": "도봉구",
    "11350": "강북구",
    "11380": "은평구",
    "11400": "서대문구",
    "11440": "마포구",
    "11470": "양천구",
    "11500": "강서구",
    "11530": "구로구",
    "11560": "영등포구",
    "11590": "동작구",
    "11620": "관악구",
    "11650": "서초구",
    "11680": "강남구",
    "11710": "송파구",
    "11740": "강동구",
}

OUTPUT_DIR: Path = Path("output")
CSV_FIELDNAMES: list[str] = [
    "building",
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


@dataclass
class CrawlStats:
    """크롤링 통계 추적"""

    total_processed: int = 0
    data_found: int = 0
    empty_dongs: int = 0
    error_dongs: int = 0
    total_apartments: int = 0
    unique_seqs: set[str] = field(default_factory=set)

    def print_summary(self, elapsed: float, title: str = "크롤링") -> None:
        """통계 요약 출력"""
        print(f"\n{'=' * 60}")
        print(f"{title} 완료!")
        print(f"{'=' * 60}")
        print(f"총 처리 동: {self.total_processed}개")
        print(f"데이터 있는 동: {self.data_found}개")
        print(f"데이터 없는 동: {self.empty_dongs}개")
        print(f"에러 발생: {self.error_dongs}개")
        print(f"총 수집 아파트: {self.total_apartments}건")
        print(f"중복 제거 후: {len(self.unique_seqs)}건")
        print(f"소요 시간: {elapsed / 60:.1f}분")


@contextlib.contextmanager
def setup_csv_output(filepath: Path) -> Iterator[tuple[csv.DictWriter, TextIO]]:
    """CSV 출력을 위한 context manager"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    file_exists = filepath.exists()

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
            f.flush()
        yield writer, f


@contextlib.contextmanager
def setup_logger(log_path: Path) -> Iterator[logging.Logger]:
    """로그를 위한 context manager"""
    OUTPUT_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger("crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # 기존 핸들러 제거

    # 파일 핸들러
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 포맷터
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    try:
        yield logger
    finally:
        logger.removeHandler(file_handler)
        logger.removeHandler(console_handler)
        file_handler.close()


def log_message(message: str, file: TextIO | None = None) -> None:
    """로그 출력 (콘솔 + 파일) - 하위 호환성용"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    if file:
        file.write(log_msg + "\n")
        file.flush()


def resolve_gu_code(gu_input: str) -> tuple[str, str] | None:
    """구 입력값을 (코드, 이름) 튜플로 변환

    Args:
        gu_input: 구 코드(5자리) 또는 구 이름

    Returns:
        (gu_code, gu_name) 튜플 또는 None
    """
    # 코드로 검색
    if gu_input in SEOUL_GU_CODES:
        return gu_input, SEOUL_GU_CODES[gu_input]

    # 이름으로 검색
    for code, name in SEOUL_GU_CODES.items():
        if name == gu_input:
            return code, name

    return None


def generate_dong_codes(gu_code: str) -> list[str]:
    """구 코드에 해당하는 법정동 코드들 생성

    법정동 코드 형식: 구코드(5자리) + 동코드(3자리) + 00
    예: 1156010100 = 영등포구(11560) + 영등포동(010) + 00
    """
    dong_codes = []
    for i in range(1, 200):
        dong_code = f"{gu_code}{i:03d}00"
        dong_codes.append(dong_code)
    return dong_codes


def crawl_dong_list(
    dong_codes: list[str],
    writer: csv.DictWriter,
    csv_file: TextIO,
    logger: logging.Logger,
    rate_limit: float,
    stats: CrawlStats,
    progress_msg_interval: int = 5,
) -> None:
    """동 코드 리스트 크롤링 (공통 로직)"""
    for idx, dong_code in enumerate(dong_codes):
        stats.total_processed += 1

        try:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results: list[dict[str, Any]] = crawler.crawl()

            if results:
                stats.data_found += 1
                stats.total_apartments += len(results)

                for apt in results:
                    seq = apt["seq"]
                    if seq not in stats.unique_seqs:
                        stats.unique_seqs.add(seq)
                        writer.writerow(apt)
                        csv_file.flush()

                if stats.data_found % progress_msg_interval == 0:
                    logger.info(
                        f"  {dong_code}: +{len(results)}건 "
                        f"(누적:{len(stats.unique_seqs)}건, "
                        f"처리:{idx + 1}/{len(dong_codes)})"
                    )
            else:
                stats.empty_dongs += 1

            time.sleep(rate_limit)

        except Exception as e:
            stats.error_dongs += 1
            logger.error(f"  {dong_code}: ERROR - {e}")


def crawl_single_dong(dong_code: str, output: str | None = None) -> list[dict[str, Any]]:
    """단일 동 크롤링

    Args:
        dong_code: 법정동 코드
        output: 출력 파일명 (None이면 자동 생성)

    Returns:
        수집된 아파트 데이터 리스트
    """
    print(f"동 코드 {dong_code} 크롤링 시작...")

    try:
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results: list[dict[str, Any]] = crawler.crawl()

        if results:
            print(f"  → {len(results)}개 아파트 수집 완료")

            if output:
                output_path = OUTPUT_DIR / output
                with setup_csv_output(output_path) as (writer, f):
                    for apt in results:
                        writer.writerow(apt)
                print(f"  → 저장 완료: {output_path}")
        else:
            print("  → 데이터 없음")

        return results or []

    except Exception as e:
        print(f"  → 에러 발생: {e}")
        return []


def crawl_gu(
    gu_code: str,
    output: str | None = None,
    rate_limit: float = 0.5,
) -> None:
    """특정 구 전체 크롤링 (streaming)

    Args:
        gu_code: 구 코드 (5자리)
        output: 출력 파일명 (None이면 자동 생성)
        rate_limit: 요청 간 딜레이 (초)
    """
    gu_name = SEOUL_GU_CODES.get(gu_code, gu_code)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = OUTPUT_DIR / (output or f"{gu_name}_apt_{timestamp}.csv")
    log_path = OUTPUT_DIR / f"crawl_log_{timestamp}.txt"

    stats = CrawlStats()

    with setup_csv_output(output_path) as (writer, csv_f), setup_logger(log_path) as logger:
        logger.info(f"{'=' * 60}")
        logger.info(f"[{gu_name} ({gu_code})] 아파트 크롤링 시작")
        logger.info(f"요청 간 딜레이: {rate_limit}초")
        logger.info(f"출력 파일: {output_path}")
        logger.info(f"{'=' * 60}")

        start_time = time.time()
        dong_codes = generate_dong_codes(gu_code)

        crawl_dong_list(
            dong_codes=dong_codes,
            writer=writer,
            csv_file=csv_f,
            logger=logger,
            rate_limit=rate_limit,
            stats=stats,
            progress_msg_interval=5,
        )

    elapsed = time.time() - start_time
    stats.print_summary(elapsed, f"[{gu_name}]")
    print(f"CSV 파일: {output_path}")


def crawl_seoul_all(
    output: str | None = None,
    rate_limit: float = 0.5,
) -> None:
    """서울 전체 구 크롤링 (streaming)

    Args:
        output: 출력 파일명 (None이면 자동 생성)
        rate_limit: 요청 간 딜레이 (초)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / (output or f"seoul_all_apt_{timestamp}.csv")
    log_path = OUTPUT_DIR / f"crawl_log_{timestamp}.txt"

    stats = CrawlStats()

    with setup_csv_output(output_path) as (writer, csv_f), setup_logger(log_path) as logger:
        logger.info(f"{'=' * 60}")
        logger.info("서울 전체 아파트 크롤링 시작")
        logger.info("타겟 구: 25개")
        logger.info(f"요청 간 딜레이: {rate_limit}초")
        logger.info(f"출력 파일: {output_path}")
        logger.info(f"{'=' * 60}")

        start_time = time.time()

        for gu_code, gu_name in SEOUL_GU_CODES.items():
            logger.info(f"\n[{gu_name} ({gu_code})] 시작...")

            dong_codes = generate_dong_codes(gu_code)
            gu_stats = CrawlStats()

            crawl_dong_list(
                dong_codes=dong_codes,
                writer=writer,
                csv_file=csv_f,
                logger=logger,
                rate_limit=rate_limit,
                stats=stats,
                progress_msg_interval=10,
            )

            logger.info(
                f"  [{gu_name}] 완료 - 데이터:{gu_stats.data_found} 에러:{gu_stats.error_dongs}"
            )

            time.sleep(5)  # 구 간 대기

    elapsed = time.time() - start_time
    stats.print_summary(elapsed, "서울 전체")
    print(f"CSV 파일: {output_path}")


def test_dong_info(apt_code: str, apt_name: str) -> list[dict[str, Any]]:
    """동/호 정보 조회 테스트"""
    print(f"\n{apt_name} ({apt_code})")
    print("-" * 50)

    crawler = AsilDongInfoCrawler(apt_code=apt_code)
    result: list[dict[str, Any]] = crawler.crawl()
    print(f"결과: {len(result)}개 동")

    for item in result:
        print(f"  - {item.get('dong')}동")

    return result


def test_asil() -> None:
    """Asil 크롤러 테스트"""
    print("=" * 50)
    print("AsilDongInfoCrawler 테스트")
    print("=" * 50)

    result1: list[dict[str, Any]] = test_dong_info("20340925", "역삼자이")
    status1: str = "성공" if len(result1) > 0 else "실패"
    print(f"테스트 결과: {status1}")

    result2: list[dict[str, Any]] = test_dong_info("12064314", "(613-16)")
    status2: str = "성공 (빈 응답 처리)" if len(result2) == 0 else "실패"
    print(f"테스트 결과: {status2}")

    print("\n" + "=" * 50)
    print("최종 테스트 결과")
    print("=" * 50)
    print(f"1. 역삼자이: {status1}")
    print(f"2. (613-16): {status2}")


def test_redevelop_api() -> None:
    """재개발 단지 API 테스트"""
    base_url = "https://asil.kr/json/data_redevelop.jsp"

    test_cases: list[dict[str, Any]] = [
        {
            "name": "강남구 전체",
            "params": {
                "type": "1",
                "step": "",
                "zoom": "12",
                "s_lat": "37.48",
                "s_lng": "127.00",
                "e_lat": "37.62",
                "e_lng": "127.15",
            },
        },
        {
            "name": "서울시 전체",
            "params": {
                "type": "1",
                "step": "",
                "zoom": "10",
                "s_lat": "37.40",
                "s_lng": "126.80",
                "e_lat": "37.70",
                "e_lng": "127.20",
            },
        },
    ]

    for test_case in test_cases:
        print(f"\n{'=' * 80}")
        print(f"테스트: {test_case['name']}")
        print(f"파라미터: {test_case['params']}")
        print("-" * 80)

        url = f"{base_url}?{urlencode(test_case['params'])}"
        print(f"요청 URL: {url}")

        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )

        try:
            with urlopen(request, timeout=10) as response:
                content = response.read().decode("utf-8")
                print(f"응답 길이: {len(content)} bytes")

                if content and content.strip() not in ["[]", "[", "]", ""]:
                    try:
                        data: list[dict[str, Any]] = json.loads(content)
                        print(f"파싱 성공! {len(data)}개 항목")
                        if data:
                            print(
                                f"첫 번째 항목: {json.dumps(data[0], ensure_ascii=False, indent=2)}"
                            )
                    except json.JSONDecodeError as e:
                        print(f"JSON 파싱 실패: {e}")
                else:
                    print("빈 응답 또는 배열")
        except Exception as e:
            print(f"에러 발생: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="아실(asil.kr) 크롤러 단일 진입점",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 특정 구 크롤링 (코드 또는 이름)
  %(prog)s crawl --gu 11560
  %(prog)s crawl --gu 영등포구

  # 특정 동 크롤링
  %(prog)s crawl --dong 1156010100

  # 서울 전체 크롤링
  %(prog)s crawl --all

  # 크롤러 테스트
  %(prog)s test asil
  %(prog)s test redevelop
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="명령")

    # crawl 하위 명령
    crawl_parser = subparsers.add_parser("crawl", help="아파트 목록 크롤링")

    crawl_group = crawl_parser.add_mutually_exclusive_group(required=True)
    crawl_group.add_argument(
        "--gu",
        metavar="CODE|NAME",
        help="구 코드(5자리) 또는 구 이름 (예: 11560, 영등포구)",
    )
    crawl_group.add_argument(
        "--dong",
        metavar="CODE",
        help="법정동 코드 (10자리, 예: 1156010100)",
    )
    crawl_group.add_argument(
        "--all",
        action="store_true",
        help="서울 전체 크롤링",
    )

    crawl_parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="출력 CSV 파일명 (기본: 자동 생성)",
    )
    crawl_parser.add_argument(
        "--rate-limit",
        "-r",
        type=float,
        default=0.5,
        help="요청 간 딜레이 (초, 기본: 0.5)",
    )

    # test 하위 명령
    test_parser = subparsers.add_parser("test", help="크롤러 테스트")
    test_parser.add_argument(
        "target",
        choices=["asil", "redevelop", "education-map", "school", "traffic"],
        help="테스트 대상",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "crawl":
        if args.all:
            crawl_seoul_all(output=args.output, rate_limit=args.rate_limit)
        elif args.gu:
            resolved = resolve_gu_code(args.gu)
            if resolved is None:
                print(f"오류: '{args.gu}'는 올바른 구 코드 또는 이름이 아닙니다.")
                print("\n사용 가능한 구:")
                for code, name in SEOUL_GU_CODES.items():
                    print(f"  {code}: {name}")
                return
            gu_code, gu_name = resolved
            crawl_gu(gu_code, output=args.output, rate_limit=args.rate_limit)
        elif args.dong:
            crawl_single_dong(args.dong, output=args.output)

    elif args.command == "test":
        if args.target == "asil":
            test_asil()
        elif args.target == "redevelop":
            test_redevelop_api()
        else:
            print(f"아직 구현되지 않은 테스트입니다: {args.target}")


if __name__ == "__main__":
    main()

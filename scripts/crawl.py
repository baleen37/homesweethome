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
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.asil import (
    AsilAptListCrawler,
    AsilDongInfoCrawler,
)

# 서울 25개 구 코드
SEOUL_GU_CODES = {
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

OUTPUT_DIR = "output"


def setup_csv_writer(filepath: str) -> tuple[csv.DictWriter, Any]:
    """CSV 파일 생성 및 writer 초기화 (streaming용)

    Returns:
        (writer, file_object) 튜플
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    file_exists = os.path.exists(filepath)
    f = open(filepath, "a", newline="", encoding="utf-8")
    writer = None

    fieldnames = [
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

    if not file_exists:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        f.flush()
    else:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

    return writer, f


def log_message(message: str, file=None) -> None:
    """로그 출력 (콘솔 + 파일)"""
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


def crawl_single_dong(dong_code: str, output: str | None = None) -> list[dict]:
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
        results = crawler.crawl()

        if results:
            print(f"  → {len(results)}개 아파트 수집 완료")

            if output:
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                output_path = os.path.join(OUTPUT_DIR, output)
                writer, f = setup_csv_writer(output_path)
                for apt in results:
                    writer.writerow(apt)
                f.close()
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
    """特定 구 전체 크롤링 (streaming)

    Args:
        gu_code: 구 코드 (5자리)
        output: 출력 파일명 (None이면 자동 생성)
        rate_limit: 요청 간 딜레이 (초)
    """
    gu_name = SEOUL_GU_CODES.get(gu_code, gu_code)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"{gu_name}_apt_{timestamp}.csv"

    output_path = os.path.join(OUTPUT_DIR, output)
    log_path = os.path.join(OUTPUT_DIR, f"crawl_log_{timestamp}.txt")

    writer, csv_f = setup_csv_writer(output_path)
    log_f = open(log_path, "w", encoding="utf-8")

    stats = {
        "total_processed": 0,
        "data_found": 0,
        "empty_dongs": 0,
        "error_dongs": 0,
        "total_apartments": 0,
        "unique_seqs": set(),
    }

    log_message("=" * 60, log_f)
    log_message(f"[{gu_name} ({gu_code})] 아파트 크롤링 시작", log_f)
    log_message(f"요청 간 딜레이: {rate_limit}초", log_f)
    log_message(f"출력 파일: {output_path}", log_f)
    log_message("=" * 60, log_f)

    start_time = time.time()
    dong_codes = generate_dong_codes(gu_code)

    for idx, dong_code in enumerate(dong_codes):
        stats["total_processed"] += 1

        try:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results = crawler.crawl()

            if results:
                stats["data_found"] += 1
                stats["total_apartments"] += len(results)

                for apt in results:
                    seq = apt["seq"]
                    if seq not in stats["unique_seqs"]:
                        stats["unique_seqs"].add(seq)
                        writer.writerow(apt)
                        csv_f.flush()

                if stats["data_found"] % 5 == 0:
                    log_message(
                        f"  {dong_code}: +{len(results)}건 "
                        f"(누적:{len(stats['unique_seqs'])}건, "
                        f"처리:{idx + 1}/{len(dong_codes)})",
                        log_f,
                    )
            else:
                stats["empty_dongs"] += 1

            time.sleep(rate_limit)

        except Exception as e:
            stats["error_dongs"] += 1
            log_message(f"  {dong_code}: ERROR - {e}", log_f)

    csv_f.close()
    log_f.close()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"[{gu_name}] 크롤링 완료!")
    print("=" * 60)
    print(f"총 처리 동: {stats['total_processed']}개")
    print(f"데이터 있는 동: {stats['data_found']}개")
    print(f"데이터 없는 동: {stats['empty_dongs']}개")
    print(f"에러 발생: {stats['error_dongs']}개")
    print(f"총 수집 아파트: {stats['total_apartments']}건")
    print(f"중복 제거 후: {len(stats['unique_seqs'])}건")
    print(f"소요 시간: {elapsed / 60:.1f}분")
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output is None:
        output = f"seoul_all_apt_{timestamp}.csv"

    output_path = os.path.join(OUTPUT_DIR, output)
    log_path = os.path.join(OUTPUT_DIR, f"crawl_log_{timestamp}.txt")

    writer, csv_f = setup_csv_writer(output_path)
    log_f = open(log_path, "w", encoding="utf-8")

    stats = {
        "total_processed": 0,
        "data_found": 0,
        "empty_dongs": 0,
        "error_dongs": 0,
        "total_apartments": 0,
        "unique_seqs": set(),
    }

    log_message("=" * 60, log_f)
    log_message("서울 전체 아파트 크롤링 시작", log_f)
    log_message(f"타겟 구: 25개", log_f)
    log_message(f"요청 간 딜레이: {rate_limit}초", log_f)
    log_message(f"출력 파일: {output_path}", log_f)
    log_message("=" * 60, log_f)

    start_time = time.time()

    for gu_code, gu_name in SEOUL_GU_CODES.items():
        log_message(f"\n[{gu_name} ({gu_code})] 시작...", log_f)

        dong_codes = generate_dong_codes(gu_code)
        gu_stats = {"found": 0, "empty": 0, "error": 0, "apartments": 0}

        for idx, dong_code in enumerate(dong_codes):
            stats["total_processed"] += 1

            try:
                crawler = AsilAptListCrawler(dong_code=dong_code)
                results = crawler.crawl()

                if results:
                    stats["data_found"] += 1
                    gu_stats["found"] += 1
                    stats["total_apartments"] += len(results)
                    gu_stats["apartments"] += len(results)

                    for apt in results:
                        seq = apt["seq"]
                        if seq not in stats["unique_seqs"]:
                            stats["unique_seqs"].add(seq)
                            writer.writerow(apt)
                            csv_f.flush()

                    if stats["data_found"] % 10 == 0:
                        log_message(
                            f"  [{gu_name}] {dong_code}: +{len(results)}건 "
                            f"(누적:{len(stats['unique_seqs'])}건, "
                            f"처리:{idx + 1}/{len(dong_codes)})",
                            log_f,
                        )
                else:
                    stats["empty_dongs"] += 1
                    gu_stats["empty"] += 1

                time.sleep(rate_limit)

            except Exception as e:
                stats["error_dongs"] += 1
                gu_stats["error"] += 1
                log_message(f"  [{gu_name}] {dong_code}: ERROR - {e}", log_f)

        log_message(
            f"  [{gu_name}] 완료 - "
            f"데이터:{gu_stats['found']} 공백:{gu_stats['empty']} "
            f"에러:{gu_stats['error']} 아파트:{gu_stats['apartments']}건",
            log_f,
        )

        time.sleep(5)

    csv_f.close()
    log_f.close()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("서울 전체 크롤링 완료!")
    print("=" * 60)
    print(f"총 처리 동: {stats['total_processed']}개")
    print(f"데이터 있는 동: {stats['data_found']}개")
    print(f"데이터 없는 동: {stats['empty_dongs']}개")
    print(f"에러 발생: {stats['error_dongs']}개")
    print(f"총 수집 아파트: {stats['total_apartments']}건")
    print(f"중복 제거 후: {len(stats['unique_seqs'])}건")
    print(f"소요 시간: {elapsed / 60:.1f}분")
    print(f"CSV 파일: {output_path}")


def test_dong_info(apt_code: str, apt_name: str) -> list[dict]:
    """동/호 정보 조회 테스트"""
    print(f"\n{apt_name} ({apt_code})")
    print("-" * 50)

    crawler = AsilDongInfoCrawler(apt_code=apt_code)
    result = crawler.crawl()
    print(f"결과: {len(result)}개 동")

    for item in result:
        print(f"  - {item.get('dong')}동")

    return result


def test_asil() -> None:
    """Asil 크롤러 테스트"""
    print("=" * 50)
    print("AsilDongInfoCrawler 테스트")
    print("=" * 50)

    result1 = test_dong_info("20340925", "역삼자이")
    status1 = "성공" if len(result1) > 0 else "실패"
    print(f"테스트 결과: {status1}")

    result2 = test_dong_info("12064314", "(613-16)")
    status2 = "성공 (빈 응답 처리)" if len(result2) == 0 else "실패"
    print(f"테스트 결과: {status2}")

    print("\n" + "=" * 50)
    print("최종 테스트 결과")
    print("=" * 50)
    print(f"1. 역삼자이: {status1}")
    print(f"2. (613-16): {status2}")


def test_redevelop_api() -> None:
    """재개발 단지 API 테스트"""
    BASE_URL = "https://asil.kr/json/data_redevelop.jsp"

    test_cases = [
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

        url = f"{BASE_URL}?{urlencode(test_case['params'])}"
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
                        data = json.loads(content)
                        print(f"파싱 성공! {len(data)}개 항목")
                        if data:
                            print(
                                f"첫 번째 항목: "
                                f"{json.dumps(data[0], ensure_ascii=False, indent=2)}"
                            )
                    except json.JSONDecodeError as e:
                        print(f"JSON 파싱 실패: {e}")
                else:
                    print("빈 응답 또는 배열")
        except Exception as e:
            print(f"에러 발생: {e}")


def main():
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

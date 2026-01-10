"""서울 전체 아파트 크롤링 스크립트

Features:
- 실시간 스트리밍으로 CSV 저장 (메모리 효율)
- Rate limiting 적용
- 진행 상황 실시간 로그
- 일부 구만 테스트하는 옵션
"""

import csv
import os
import time
from datetime import datetime
from typing import Any

from crawler.asil import AsilAptListCrawler

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

# 테스트용: 특정 구만 크롤링 (index slice: 시작:끝)
# 예: [17:18]은 영등포구만, [0:1]은 종로구만, None이면 전체
TEST_SLICE = slice(17, 18)  # 영등포구만

# 동 코드 범위 (법정동 코드: 구코드5자리 + 동코드5자리)
# 예: 1156010100 = 영등포구(11560) + 영등포동(0100)
DONG_CODE_START = 1
DONG_CODE_END = 200  # 영등포구 전체

OUTPUT_DIR = "output"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"seoul_all_apt_{TIMESTAMP}.csv"
LOG_FILE = os.path.join(OUTPUT_DIR, f"crawl_log_{TIMESTAMP}.txt")

# Rate limiting
REQUEST_DELAY = 0.5  # 요청 간 딜레이 (초)
BATCH_DELAY = 5  # 배치完成后 추가 딜레이 (초)


def setup_csv_writer(filepath: str) -> tuple[csv.DictWriter, Any]:
    """CSV 파일 생성 및 writer 초기화 (streaming용)

    Returns:
        (writer, file_object) 튜플
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # 파일이 없으면 헤더와 함께 생성, 있으면 append 모드
    file_exists = os.path.exists(filepath)

    f = open(filepath, "a", newline="", encoding="utf-8")
    writer = None

    if not file_exists:
        # 첫 기록: 헤더 작성을 위해 더미 데이터로 fieldnames 추론
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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        f.flush()
    else:
        # 기존 파일에 추가
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


def generate_dong_codes(gu_code: str) -> list[str]:
    """구 코드에 해당하는 법정동 코드들 생성

    법정동 코드 형식: 구코드(5자리) + 동코드(3자리) + 00
    예: 1156010100 = 영등포구(11560) + 영등포동(010) + 00
    """
    dong_codes = []
    for i in range(DONG_CODE_START, DONG_CODE_END):
        dong_code = f"{gu_code}{i:03d}00"
        dong_codes.append(dong_code)
    return dong_codes


def main():
    """서울 전체 아파트 크롤링 (streaming)"""
    # 로그 파일 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_f = open(LOG_FILE, "w", encoding="utf-8")

    # CSV writer 초기화
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    writer, csv_f = setup_csv_writer(output_path)

    # 통계
    stats = {
        "total_processed": 0,
        "data_found": 0,
        "empty_dongs": 0,
        "error_dongs": 0,
        "total_apartments": 0,
        "unique_seqs": set(),
    }

    # 타겟 구 목록 (테스트용 제한)
    gu_list = list(SEOUL_GU_CODES.items())
    if TEST_SLICE:
        gu_list = gu_list[TEST_SLICE]

    log_message("=" * 60, log_f)
    log_message("서울 아파트 크롤링 시작", log_f)
    log_message(f"타겟 구: {len(gu_list)}개 (전체 25개 중)", log_f)
    log_message(f"구별 동 코드 범위: {DONG_CODE_START}~{DONG_CODE_END - 1}", log_f)
    log_message(f"요청 간 딜레이: {REQUEST_DELAY}초", log_f)
    log_message(f"출력 파일: {output_path}", log_f)
    log_message("=" * 60, log_f)

    start_time = time.time()

    for gu_code, gu_name in gu_list:
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

                    # 스트리밍: 바로 CSV에 기록
                    for apt in results:
                        seq = apt["seq"]
                        if seq not in stats["unique_seqs"]:
                            stats["unique_seqs"].add(seq)
                            writer.writerow(apt)
                            csv_f.flush()

                    # 10개마다 진행 상황 출력
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

                # Rate limiting
                time.sleep(REQUEST_DELAY)

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

        # 구 간 배치 딜레이
        time.sleep(BATCH_DELAY)

    # 종료 처리
    csv_f.close()
    log_f.close()

    elapsed = time.time() - start_time

    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("크롤링 완료!")
    print("=" * 60)
    print(f"총 처리 동: {stats['total_processed']}개")
    print(f"데이터 있는 동: {stats['data_found']}개")
    print(f"데이터 없는 동: {stats['empty_dongs']}개")
    print(f"에러 발생: {stats['error_dongs']}개")
    print(f"총 수집 아파트: {stats['total_apartments']}건")
    print(f"중복 제거 후: {len(stats['unique_seqs'])}건")
    print(f"소요 시간: {elapsed / 60:.1f}분")
    print(f"CSV 파일: {output_path}")
    print(f"로그 파일: {LOG_FILE}")


if __name__ == "__main__":
    main()

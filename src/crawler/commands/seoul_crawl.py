"""서울 아파트 크롤링 핵심 로직

Features:
- 실시간 스트리밍으로 CSV 저장 (메모리 효율)
- Rate limiting 적용
- 진행 상황 실시간 로그
- 타임아웃 및 재시도 로직 (지수 백오프)
- 체크포인트 지원 (중단 후 재개 가능)
"""

import csv
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TextIO, TypedDict

from crawler.asil import AsilAptListCrawler
from crawler.utils.filter import FilterOptions, filter_records

# CSV 필드명
CSV_FIELDNAMES = [
    "seq",
    "name",
    "gu_name",
    "dong",
    "dongname",
    "bungi",
    "movein",
    "household",
    "total_dong",
    "offer",
    "lat",
    "lng",
]


class CrawlStats(TypedDict):
    """크롤링 통계 정보를 위한 TypedDict"""

    total_processed: int
    data_found: int
    empty_dongs: int
    error_dongs: int
    total_apartments: int
    skipped_dongs: int
    unique_seqs: set[str]
    filtered_out: int


@dataclass
class SeoulCrawlConfig:
    """서울 아파트 크롤링 설정

    Attributes:
        output_dir: 출력 디렉토리
        dong_code_start: 동 코드 시작 번호
        dong_code_end: 동 코드 끝 번호
        request_delay: 요청 간 딜레이 (초)
        batch_delay: 배치 완료 후 추가 딜레이 (초)
        request_timeout: 요청 타임아웃 (초)
        max_retries: 최대 재시도 횟수
        retry_backoff_base: 지수 백오프 베이스
        progress_log_interval: 진행 상황 로그 출력 간격
        checkpoint_save_interval: 체크포인트 저장 간격
        filter_options: 데이터 필터링 옵션
    """

    output_dir: str = "output"
    dong_code_start: int = 1
    dong_code_end: int = 200
    request_delay: float = 0.5
    batch_delay: float = 5
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff_base: int = 2
    progress_log_interval: int = 5
    checkpoint_save_interval: int = 10
    filter_options: FilterOptions = field(default_factory=FilterOptions.moderate)

    @property
    def timestamp(self) -> str:
        """현재 타임스탬프"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def output_file(self) -> str:
        """출력 CSV 파일 경로"""
        return f"seoul_all_apt_{self.timestamp}.csv"

    @property
    def log_file(self) -> str:
        """로그 파일 경로"""
        return os.path.join(self.output_dir, f"crawl_log_{self.timestamp}.txt")

    @property
    def checkpoint_file(self) -> str:
        """체크포인트 파일 경로"""
        return os.path.join(self.output_dir, "crawl_checkpoint.json")


def setup_csv_writer(filepath: str) -> tuple[csv.DictWriter, TextIO]:
    """CSV 파일 생성 및 writer 초기화 (streaming용)

    Args:
        filepath: CSV 파일 경로

    Returns:
        (writer, file_object) 튜플
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    file_exists = os.path.exists(filepath)

    f = open(filepath, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)

    if not file_exists:
        writer.writeheader()
        f.flush()

    return writer, f


def log_message(message: str, file: TextIO | None = None) -> None:
    """로그 출력 (콘솔 + 파일)

    Args:
        message: 로그 메시지
        file: 로그 파일 객체 (선택사항)
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    if file:
        file.write(log_msg + "\n")
        file.flush()


def generate_dong_codes(gu_code: str, config: SeoulCrawlConfig) -> list[str]:
    """구 코드에 해당하는 법정동 코드들 생성

    법정동 코드 형식: 구코드(5자리) + 동코드(3자리) + 00

    Args:
        gu_code: 구 코드 (5자리)
        config: 크롤링 설정

    Returns:
        법정동 코드 리스트
    """
    dong_codes = []
    for i in range(config.dong_code_start, config.dong_code_end):
        dong_code = f"{gu_code}{i:03d}00"
        dong_codes.append(dong_code)
    return dong_codes


def save_checkpoint(
    completed_dongs: set[str],
    filepath: str,
    timestamp: str,
) -> None:
    """체크포인트 저장 (완료된 동 코드 목록)

    Args:
        completed_dongs: 완료된 동 코드 집합
        filepath: 체크포인트 파일 경로
        timestamp: 타임스탬프
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            {"completed_dongs": sorted(completed_dongs), "timestamp": timestamp},
            f,
            ensure_ascii=False,
            indent=2,
        )


def load_checkpoint(filepath: str) -> set[str]:
    """체크포인트 로드 (완료된 동 코드 목록)

    Args:
        filepath: 체크포인트 파일 경로

    Returns:
        완료된 동 코드 집합 (파일이 없으면 빈 집합)
    """
    if not os.path.exists(filepath):
        return set()

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("completed_dongs", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def crawl_with_timeout(
    dong_code: str,
    timeout: int,
) -> list[Any] | None:
    """타임아웃이 적용된 크롤링 함수

    Args:
        dong_code: 법정동 코드
        timeout: 타임아웃 시간 (초)

    Returns:
        크롤링 결과 리스트 (타임아웃 또는 에러 시 None)
    """
    result: list[Any] | None = None
    exception: Exception | None = None

    def crawl_worker() -> None:
        nonlocal result, exception
        try:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            result = crawler.crawl()
        except Exception as e:
            exception = e

    thread = threading.Thread(target=crawl_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        log_message(f"  [{dong_code}] 타임아웃 발생 ({timeout}초 초과)")
        return None

    if exception is not None:
        raise exception

    return result


def crawl_with_retry(
    dong_code: str,
    config: SeoulCrawlConfig,
) -> list[Any] | None:
    """재시도 로직이 포함된 크롤링 함수

    Args:
        dong_code: 법정동 코드
        config: 크롤링 설정

    Returns:
        크롤링 결과 리스트 (실패 시 None)
    """
    for attempt in range(config.max_retries):
        try:
            results = crawl_with_timeout(dong_code, config.request_timeout)
            if results is not None:
                return results
            if attempt < config.max_retries - 1:
                wait_time = config.retry_backoff_base**attempt
                log_message(
                    f"  [{dong_code}] 재시도 {attempt + 1}/{config.max_retries} "
                    f"({wait_time}초 후: 타임아웃)"
                )
                time.sleep(wait_time)
        except Exception as e:
            if attempt < config.max_retries - 1:
                wait_time = config.retry_backoff_base**attempt
                log_message(
                    f"  [{dong_code}] 재시도 {attempt + 1}/{config.max_retries} "
                    f"({wait_time}초 후): {e}"
                )
                time.sleep(wait_time)
            else:
                log_message(f"  [{dong_code}] 최대 재시도 횟수 초과: {e}")
                return None
    return None


def map_dto_to_csv(apt: Any) -> dict[str, Any]:
    """DTO를 CSV 필드명으로 매핑

    Args:
        apt: AsilAptListDTO 인스턴스

    Returns:
        CSV 필드명으로 매핑된 딕셔너리
    """
    apt_dict = apt.model_dump()

    apt_dict["movein"] = apt_dict.pop("build_year", None)
    apt_dict["total_dong"] = apt_dict.pop("dong_count", None)
    apt_dict["gu_name"] = apt.gu_name

    csv_dict = {field: apt_dict.get(field) for field in CSV_FIELDNAMES}

    return csv_dict


def crawl_single_gu(
    gu_code: str,
    gu_name: str,
    completed_dongs: set[str],
    unique_seqs: set[str],
    writer: csv.DictWriter,
    csv_f: TextIO,
    log_f: TextIO,
    config: SeoulCrawlConfig,
) -> dict[str, int]:
    """단일 구 크롤링

    Args:
        gu_code: 구 코드 (5자리)
        gu_name: 구 이름
        completed_dongs: 이미 완료된 동 코드 집합 (체크포인트)
        unique_seqs: 중복 제거를 위한 고유 아파트 seq 집합
        writer: CSV DictWriter 객체
        csv_f: CSV 파일 객체
        log_f: 로그 파일 객체
        config: 크롤링 설정

    Returns:
        구별 통계 (found, empty, error, apartments, skipped, filtered_out)
    """
    gu_stats = {
        "found": 0,
        "empty": 0,
        "error": 0,
        "apartments": 0,
        "skipped": 0,
        "filtered_out": 0,
    }

    all_collected_data = []

    dong_codes = generate_dong_codes(gu_code, config)

    for idx, dong_code in enumerate(dong_codes):
        if dong_code in completed_dongs:
            gu_stats["skipped"] += 1
            continue

        results = crawl_with_retry(dong_code, config)

        if results is None:
            gu_stats["error"] += 1
            time.sleep(config.request_delay)
            continue

        if results:
            gu_stats["found"] += 1
            gu_stats["apartments"] += len(results)

            all_collected_data.extend(results)

            filtered_results = filter_records(results, config.filter_options)
            gu_stats["filtered_out"] += len(results) - len(filtered_results)

            for apt in filtered_results:
                csv_dict = map_dto_to_csv(apt)
                seq = csv_dict["seq"]

                if seq not in unique_seqs:
                    unique_seqs.add(seq)
                    writer.writerow(csv_dict)
                    csv_f.flush()

            if gu_stats["found"] % config.progress_log_interval == 0:
                log_message(
                    f"  [{gu_name}] {dong_code}: +{len(results)}건 "
                    f"(누적:{len(unique_seqs)}건, "
                    f"처리:{idx + 1}/{len(dong_codes)})",
                    log_f,
                )
        else:
            gu_stats["empty"] += 1

        completed_dongs.add(dong_code)

        if len(completed_dongs) % config.checkpoint_save_interval == 0:
            save_checkpoint(completed_dongs, config.checkpoint_file, config.timestamp)

        time.sleep(config.request_delay)

    log_message(
        f"  [{gu_name}] 완료 - "
        f"데이터:{gu_stats['found']} 공백:{gu_stats['empty']} "
        f"에러:{gu_stats['error']} 아파트:{gu_stats['apartments']}건 "
        f"필터링:{gu_stats['filtered_out']}건 스킵:{gu_stats['skipped']}",
        log_f,
    )

    if gu_stats["skipped"] > 0:
        log_message(f"  [{gu_name}] 체크포인트로 {gu_stats['skipped']}개 동 스킵", log_f)

    return gu_stats

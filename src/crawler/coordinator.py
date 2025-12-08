"""Crawl coordinator for orchestrating incremental data saving.

This module provides CrawlCoordinator class that manages the crawling process
at the dong level, ensuring data is saved incrementally to prevent data loss
if crawling is interrupted.
"""

import time
from pathlib import Path
from typing import Any, Callable, Dict, List

import structlog

from crawler.utils.checkpoint import CheckpointManager
from crawler.rate_limiter import AdaptiveRateLimiter as RateLimiter
from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter
from crawler.progress_tracker import ProgressTracker


class CrawlCoordinator:
    """크롤링 코디네이터 - 동 단위로 점진적 저장을 관리

    설계 문서의 저장 전략에 따라:
    - 각 동이 완료될 때마다 데이터 저장
    - TransactionCSVWriter와 ComplexesCSVWriter를 사용하여 점진적 저장
    - 체크포인트 관리를 통해 중단된 크롤링 지원
    """

    # 거래 유형 상수 (매매, 전세, 월세)
    TRADE_TYPES = ["A1", "B1", "B2"]

    def __init__(
        self,
        config_or_output_dir: Path | Any,
        checkpoint_path: Path | None = None,
        initial_delay: float = 2.0,
        max_delay: float = 10.0,
        enable_progress_tracking: bool = True,
        progress_report_interval: int = 60,
    ) -> None:
        """CrawlCoordinator 초기화

        Args:
            config_or_output_dir: CrawlerConfig 객체 또는 CSV 파일 출력 디렉토리
            checkpoint_path: 체크포인트 파일 경로 (None이면 체크포인트 미사용)
            initial_delay: 초기 요청 간 지연 시간 (초)
            max_delay: 최대 지연 시간 (초)
            enable_progress_tracking: 진행 상황 추적 활성화 여부
            progress_report_interval: 진행 상황 리포트 출력 간격 (초)
        """
        # Check if first argument is a CrawlerConfig
        if hasattr(config_or_output_dir, "output_file"):
            # It's a CrawlerConfig object
            config = config_or_output_dir
            self.output_dir = (
                Path(config.output_file).parent if config.output_file else Path("output")
            )
            if not self.output_dir.exists():
                self.output_dir = Path("output/test-integration/csv")
        else:
            # It's a path string
            self.output_dir = Path(config_or_output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # CSV Writer 초기화
        self.transaction_writer = TransactionCSVWriter(self.output_dir / "transactions.csv")
        self.complexes_writer = ComplexesCSVWriter(self.output_dir / "complexes.csv")

        # 체크포인트 관리자
        self.checkpoint_manager = None
        if checkpoint_path:
            self.checkpoint_manager = CheckpointManager(str(checkpoint_path))
            self.checkpoint_manager.load()

        # Rate limiter
        self.rate_limiter = RateLimiter()
        # Override default delays if provided
        if initial_delay != 2.5:
            self.rate_limiter.current_delay = initial_delay
        # Note: max_delay is final in AdaptiveRateLimiter, cannot be modified
        # We'll use the provided max_delay as a soft limit in our code

        # Progress Tracker
        self.progress_tracker = None
        if enable_progress_tracking:
            self.progress_tracker = ProgressTracker(
                output_dir=self.output_dir,
                report_interval=progress_report_interval,
                log_file="progress.log",
            )

        # 통계
        self.stats: Dict[str, Any] = {
            "total_complexes_processed": 0,
            "total_transactions_collected": 0,
            "total_dongs_completed": 0,
            "errors": [],
        }

        self.logger = structlog.get_logger()

    def crawl_dong(
        self,
        dong_code: str,
        dong_name: str,
        complexes: List[Dict[str, Any]],
        fetch_complex_detail: Callable[..., Any],
        fetch_transaction_history: Callable[..., Any],
    ) -> Dict[str, Any]:
        """단일 동의 모든 단지를 크롤링하고 저장

        Args:
            dong_code: 동 코드 (예: "1154510200")
            dong_name: 동 이름
            complexes: 해당 동의 단지 리스트
            fetch_complex_detail: 단지 상세 정보 조회 함수
            fetch_transaction_history: 거래내역 조회 함수

        Returns:
            해당 동의 크롤링 결과 통계
        """
        self.logger.info("crawling_dong", dong_code=dong_code, dong_name=dong_name)

        # Progress tracking: 동 처리 시작
        if self.progress_tracker:
            self.progress_tracker.start_dong(dong_code, dong_name, len(complexes))

        dong_stats: Dict[str, Any] = {
            "dong_code": dong_code,
            "dong_name": dong_name,
            "complexes_count": len(complexes),
            "complexes_processed": 0,
            "transactions_collected": 0,
            "errors": [],
        }

        # 각 단지 처리
        for complex in complexes:
            try:
                # Rate limiting
                self.rate_limiter.wait()

                complex_id = complex["complex_id"]
                self.logger.info("processing_complex", complex_id=complex_id)

                # Progress tracking: 단지 처리 시작
                if self.progress_tracker:
                    self.progress_tracker.start_complex(complex_id, complex.get("complex_name", ""))

                # 1. 단지 상세 정보 조회
                detail = fetch_complex_detail(complex_id)
                if not detail:
                    dong_stats["errors"].append(f"Failed to fetch detail for complex {complex_id}")
                    continue

                # 2. 거래내역 조회 (평형별, 거래 유형별)
                all_transactions = []
                pyeong_types = detail.get("pyeong_types", [])

                # pyeong_types 데이터 타입 검증 및 변환
                pyeong_type_numbers = []

                if isinstance(pyeong_types, dict):
                    # pyeong_types가 딕셔너리인 경우 (key: 평형 타입 번호)
                    pyeong_type_numbers = list(pyeong_types.keys())
                elif isinstance(pyeong_types, list):
                    # pyeong_types가 리스트인 경우
                    for item in pyeong_types:
                        if isinstance(item, dict):
                            # 각 아이템이 딕셔너리인 경우 pyeong_type_number 추출
                            if "pyeong_type_number" in item:
                                pyeong_type_numbers.append(item["pyeong_type_number"])
                            elif "pyeongTypeNo" in item:
                                # 다른 가능한 필드명
                                pyeong_type_numbers.append(item["pyeongTypeNo"])
                            else:
                                self.logger.warning(
                                    "pyeong_item_missing_type_number",
                                    complex_id=complex_id,
                                    item=item,
                                )
                        else:
                            self.logger.warning(
                                "invalid_pyeong_item_type",
                                complex_id=complex_id,
                                item_type=type(item),
                                item=item,
                            )
                elif pyeong_types:
                    # 예상치 못한 타입인 경우 (문자열, 숫자 등)
                    self.logger.warning(
                        "unexpected_pyeong_types_type",
                        complex_id=complex_id,
                        pyeong_types_type=type(pyeong_types),
                        pyeong_types_value=str(pyeong_types)[:200],
                    )
                else:
                    # pyeong_types가 비어있는 경우
                    self.logger.info("no_pyeong_types_found", complex_id=complex_id)

                # 유효한 평형 타입 번호가 있는 경우에만 거래내역 조회
                if pyeong_type_numbers:
                    for pyeong_type_number in pyeong_type_numbers:
                        # 모든 거래 유형 조회 (매매, 전세, 월세)
                        for trade_type in self.TRADE_TYPES:
                            self.rate_limiter.wait()

                            transactions = fetch_transaction_history(
                                complex_id,
                                int(pyeong_type_number),  # 문자열일 수 있으므로 정수로 변환
                                trade_type,
                            )

                            if transactions:
                                # 거래내역을 즉시 CSV에 append
                                self.transaction_writer.append(transactions)
                                all_transactions.extend(transactions)

                                dong_stats["transactions_collected"] += len(transactions)
                                self.stats["total_transactions_collected"] += len(transactions)
                else:
                    # 평형 정보가 없는 경우에도 로그 남김
                    self.logger.info(
                        "skipping_transaction_collection",
                        complex_id=complex_id,
                        reason="no_valid_pyeong_type_numbers",
                    )

                # 3. 거래내역 통계 계산하여 단지 정보 저장
                # append 메서드가 이미 정규화를 수행하므로 all_transactions를 그대로 사용
                # append_with_statistics에서 내부적으로 다시 정규화함
                self.complexes_writer.append_with_statistics(
                    complex_data={**complex, **detail},
                    transactions=all_transactions,
                )

                dong_stats["complexes_processed"] += 1
                self.stats["total_complexes_processed"] += 1

                # Progress tracking: 단지 처리 완료
                if self.progress_tracker:
                    self.progress_tracker.complete_complex(
                        complex_id, complex.get("complex_name", ""), len(all_transactions)
                    )

                # 성공 시 rate limiter 보상
                self.rate_limiter.on_success()

            except Exception as e:
                error_msg = (
                    f"Error processing complex {complex.get('complex_id', 'unknown')}: {str(e)}"
                )
                self.logger.error("complex_error", error=error_msg)
                dong_stats["errors"].append(error_msg)
                self.stats["errors"].append(error_msg)

                # Progress tracking: 에러 기록
                if self.progress_tracker:
                    self.progress_tracker.add_error(error_msg)

                # 에러 시 rate limiter 페널티
                self.rate_limiter.on_error()

        # 동 단위 체크포인트 저장
        if self.checkpoint_manager:
            self.checkpoint_manager.save(dong_code)

        self.stats["total_dongs_completed"] += 1

        self.logger.info(
            "dong_completed",
            dong_code=dong_code,
            complexes_processed=dong_stats["complexes_processed"],
            transactions_collected=dong_stats["transactions_collected"],
            errors_count=len(dong_stats["errors"]),
        )

        # Progress tracking: 동 처리 완료
        if self.progress_tracker:
            self.progress_tracker.complete_dong(
                dong_code,
                dong_name,
                dong_stats["complexes_processed"],
                dong_stats["transactions_collected"],
                dong_stats["errors"],
            )
            # Rate limiter 상태 업데이트
            self.progress_tracker.update_rate_limiter_delay(self.rate_limiter.current_delay)

        return dong_stats

    def crawl_multiple_dongs(
        self,
        dong_complexes: List[Dict[str, Any]],
        fetch_complex_detail: Callable[..., Any],
        fetch_transaction_history: Callable[..., Any],
        resume: bool = True,
    ) -> Dict[str, Any]:
        """여러 동을 순차적으로 크롤링

        Args:
            dong_complexes: 동별 단지 정보 리스트
              [{'dong_code': '1154510200', 'dong_name': '역삼1동', 'complexes': [...]}]
            fetch_complex_detail: 단지 상세 정보 조회 함수
            fetch_transaction_history: 거래내역 조회 함수
            resume: True이면 체크포인트부터 이어서 진행

        Returns:
            전체 크롤링 결과 통계
        """
        start_time = time.time()

        # Progress tracking: 크롤링 시작
        if self.progress_tracker:
            total_complexes = sum(len(d["complexes"]) for d in dong_complexes)
            self.progress_tracker.start_crawling(
                total_dongs=len(dong_complexes), total_complexes=total_complexes
            )

        # 이어서 진행할 위치 찾기
        start_index = 0
        if resume and self.checkpoint_manager:
            last_dong = self.checkpoint_manager.checkpoint.get("last_dong")
            if last_dong:
                for i, dong_data in enumerate(dong_complexes):
                    if dong_data["dong_code"] == last_dong:
                        start_index = i + 1
                        self.logger.info(
                            "resuming_from_checkpoint",
                            last_dong=last_dong,
                            start_index=start_index,
                        )
                        break

        # CSV 파일 초기화 (새로 시작하는 경우에만)
        if start_index == 0:
            self.transaction_writer.write_header()
            self.complexes_writer.write_header()
        else:
            # 이어서 진행하는 경우 파일이 존재하는지 확인
            self.transaction_writer.ensure_file_exists()
            self.complexes_writer.ensure_file_exists()

        # 각 동 처리
        results: List[Dict[str, Any]] = []
        for dong_data in dong_complexes[start_index:]:
            result = self.crawl_dong(
                dong_code=dong_data["dong_code"],
                dong_name=dong_data["dong_name"],
                complexes=dong_data["complexes"],
                fetch_complex_detail=fetch_complex_detail,
                fetch_transaction_history=fetch_transaction_history,
            )
            results.append(result)

        # 최종 통계
        end_time = time.time()
        final_stats = {
            "total_dongs": len(dong_complexes),
            "dongs_processed": len(results),
            "total_complexes": sum(len(d["complexes"]) for d in dong_complexes),
            "total_complexes_processed": self.stats["total_complexes_processed"],
            "total_transactions_collected": self.stats["total_transactions_collected"],
            "total_errors": len(self.stats["errors"]),
            "duration_seconds": end_time - start_time,
            "rate_limiter_state": {
                "current_delay": self.rate_limiter.current_delay,
                "success_count": self.rate_limiter.success_count,
                "error_count": self.rate_limiter.error_count,
            },
            "results": results,
        }

        self.logger.info(
            "crawling_completed",
            dongs_processed=final_stats["dongs_processed"],
            complexes_processed=final_stats["total_complexes_processed"],
            transactions_collected=final_stats["total_transactions_collected"],
            duration_seconds=final_stats["duration_seconds"],
        )

        # Progress tracking: 크롤링 완료
        if self.progress_tracker:
            self.progress_tracker.finish_crawling()

        return final_stats

    def get_statistics(self) -> Dict[str, Any]:
        """현재까지의 통계 정보 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            **self.stats,
            "rate_limiter_state": {
                "current_delay": self.rate_limiter.current_delay,
                "success_count": self.rate_limiter.success_count,
                "error_count": self.rate_limiter.error_count,
            },
        }

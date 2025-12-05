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


class CrawlCoordinator:
    """크롤링 코디네이터 - 동 단위로 점진적 저장을 관리

    설계 문서의 저장 전략에 따라:
    - 각 동이 완료될 때마다 데이터 저장
    - TransactionCSVWriter와 ComplexesCSVWriter를 사용하여 점진적 저장
    - 체크포인트 관리를 통해 중단된 크롤링 지원
    """

    def __init__(
        self,
        output_dir: Path,
        checkpoint_path: Path | None = None,
        initial_delay: float = 2.0,
        max_delay: float = 10.0,
    ) -> None:
        """CrawlCoordinator 초기화

        Args:
            output_dir: CSV 파일 출력 디렉토리
            checkpoint_path: 체크포인트 파일 경로 (None이면 체크포인트 미사용)
            initial_delay: 초기 요청 간 지연 시간 (초)
            max_delay: 최대 지연 시간 (초)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # CSV Writer 초기화
        self.transaction_writer = TransactionCSVWriter(
            self.output_dir / "transactions.csv"
        )
        self.complexes_writer = ComplexesCSVWriter(
            self.output_dir / "complexes.csv"
        )

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

                # 1. 단지 상세 정보 조회
                detail = fetch_complex_detail(complex_id)
                if not detail:
                    dong_stats["errors"].append(
                        f"Failed to fetch detail for complex {complex_id}"
                    )
                    continue

                # 2. 거래내역 조회 (평형별, 거래 유형별)
                all_transactions = []
                pyeong_types = detail.get("pyeong_types", [])

                for pyeong in pyeong_types:
                    pyeong_type_number = pyeong["pyeong_type_number"]

                    # 모든 거래 유형 조회 (매매, 전세, 월세)
                    for trade_type in ["A1", "B1", "B2"]:
                        self.rate_limiter.wait()

                        transactions = fetch_transaction_history(
                            complex_id,
                            pyeong_type_number,
                            trade_type,
                        )

                        if transactions:
                            # 거래내역을 즉시 CSV에 append
                            self.transaction_writer.append(transactions)
                            all_transactions.extend(transactions)

                            dong_stats["transactions_collected"] += len(transactions)
                            self.stats["total_transactions_collected"] += len(transactions)

                # 3. 거래내역 정규화 후 통계 계산하여 단지 정보 저장
                # TransactionCSVWriter의 _normalize_transaction 메서드를 사용하여 정규화
                normalized_transactions = [
                    self.transaction_writer._normalize_transaction(t)
                    for t in all_transactions
                ]
                self.complexes_writer.append_with_statistics(
                    complex_data={**complex, **detail},
                    transactions=normalized_transactions,
                )

                dong_stats["complexes_processed"] += 1
                self.stats["total_complexes_processed"] += 1

                # 성공 시 rate limiter 보상
                self.rate_limiter.on_success()

            except Exception as e:
                error_msg = f"Error processing complex {complex.get('complex_id', 'unknown')}: {str(e)}"
                self.logger.error("complex_error", error=error_msg)
                dong_stats["errors"].append(error_msg)
                self.stats["errors"].append(error_msg)

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
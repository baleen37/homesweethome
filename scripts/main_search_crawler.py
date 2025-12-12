#!/usr/bin/env python3
"""메인 실행 스크립트 - 검색 기반 아파트 크롤러

호갱노노 웹사이트에서 분석한 검색 API를 사용하여
실제 아파트 데이터를 수집하는 메인 스크립트
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter
from crawler.coordinator.progress_tracker import ProgressTracker
from crawler.crawlers.apartment_search_crawler import ApartmentSearchCrawler
from crawler.utils.rate_limiter import AdaptiveRateLimiter
from crawler.utils.checkpoint import CheckpointManager


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("crawler_search.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    """메인 실행 함수"""
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="호갱노노 아파트 검색 크롤러")
    parser.add_argument(
        "--output-dir", type=str, default="output", help="출력 디렉토리 (기본값: output)"
    )
    parser.add_argument(
        "--config", type=str, default="config/crawler_config.json", help="설정 파일 경로"
    )
    parser.add_argument(
        "--apt-ids", type=str, nargs="*", help="수집할 특정 아파트 ID 목록 (선택적)"
    )
    parser.add_argument(
        "--regions", type=str, nargs="*", help="수집할 지역 목록 (예: 강남구 서초구 송파구)"
    )
    parser.add_argument("--resume", action="store_true", help="이전 작업 이어서 진행")
    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")

    args = parser.parse_args()

    # 로그 레벨 조정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 설정 로드
        config_path = Path(args.config)
        if config_path.exists():
            config = CrawlerConfig.from_file(config_path)
        else:
            logger.warning(f"설정 파일 {config_path}을 찾을 수 없습니다. 기본 설정을 사용합니다.")
            config = CrawlerConfig()

        # API 클라이언트 초기화
        api_client = HogangnonoAPIClient(config)

        # 데이터 매퍼 초기화
        data_mapper = HogangnonoDataMapper()

        # CSV 작성기 초기화
        writer = HogangnonoCSVWriter(
            output_dir=output_dir,
            complex_filename="hogangnono_complexes_search.csv",
            transaction_filename="hogangnono_transactions_search.csv",
        )

        # 진행률 추적기 초기화
        progress_tracker = ProgressTracker(checkpoint_file=output_dir / "progress_search.json")

        # 체크포인트 매니저 초기화
        checkpoint_manager = CheckpointManager(
            checkpoint_file=output_dir / "checkpoint_search.json"
        )

        # 적응형 속도 제한기 초기화
        rate_limiter = AdaptiveRateLimiter()

        # 검색 크롤러 초기화
        async with ApartmentSearchCrawler(
            api_client=api_client,
            data_mapper=data_mapper,
            writer=writer,
            progress_tracker=progress_tracker,
        ) as crawler:
            # 이어서 진행 옵션이 있는 경우 체크포인트 확인
            if args.resume:
                last_checkpoint = checkpoint_manager.load_checkpoint()
                if last_checkpoint:
                    logger.info(f"체크포인트에서 작업을 이어서 진행합니다: {last_checkpoint}")

            # 크롤링 실행
            if args.apt_ids:
                # 특정 아파트 ID 수집
                logger.info(f"특정 아파트 {len(args.apt_ids)}개 수집을 시작합니다")
                await crawler.collect_specific_apartments(args.apt_ids)
            elif args.regions:
                # 지역별 수집
                logger.info(f"지역별 아파트 수집을 시작합니다: {args.regions}")
                await crawler.collect_by_region(args.regions)
            else:
                # 전체 아파트 수집
                logger.info("전체 아파트 수집을 시작합니다")
                await crawler.crawl_all_apartments()

        # 최종 통계 출력
        stats = progress_tracker.get_stats()
        logger.info(
            f"크롤링 완료! "
            f"처리된 복합단지: {stats.get('complexes_processed', 0)}, "
            f"처리된 매물: {stats.get('items_processed', 0)}, "
            f"시작 시간: {stats.get('start_time', 'N/A')}, "
            f"종료 시간: {stats.get('end_time', 'N/A')}"
        )

    except KeyboardInterrupt:
        logger.info("사용자에 의해 크롤링이 중단되었습니다")
        # 체크포인트 저장
        if "progress_tracker" in locals():
            await progress_tracker.save_progress()
        sys.exit(1)
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # asyncio 이벤트 루프 실행
    asyncio.run(main())

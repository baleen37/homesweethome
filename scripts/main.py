import argparse
from pathlib import Path
import asyncio
import logging
import sys

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
)
logger = logging.getLogger(__name__)


def main() -> None:
    """HomeSweetHome 호갱노노 부동산 크롤러"""
    parser = argparse.ArgumentParser(
        description="호갱노노 부동산 데이터 수집",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행 (모든 지역 크롤링)
  python scripts/main.py

  # 특정 지역만 크롤링
  python scripts/main.py --region 강남구

  # 출력 디렉토리 지정
  python scripts/main.py --output results/20251212
        """,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="출력 디렉토리 (기본: output)",
    )

    parser.add_argument(
        "--region",
        type=str,
        help="특정 지역 크롤링 (예: 강남구, 서초구)",
    )

    args = parser.parse_args()

    # 설정 초기화
    try:
        config = CrawlerConfig.from_env(output_file=str(args.output))
    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        sys.exit(1)

    # 출력 디렉토리 생성
    args.output.mkdir(parents=True, exist_ok=True)

    # 크롤링 실행
    asyncio.run(run_crawler(config, args.output, args.region))


async def run_crawler(config: CrawlerConfig, output_dir: Path, region: str = None) -> None:
    """크롤러 실행"""
    crawler = HogangnonoCrawler(
        config=config,
        output_dir=output_dir,
    )

    try:
        if region:
            logger.info(f"'{region}' 지역 크롤링 시작...")
            # 특정 지역의 경우 districts로 처리
            stats = crawler.crawl(districts=[region])
            logger.info(f"{region} 지역 크롤링 완료")
        else:
            logger.info("전체 지역 크롤링 시작...")
            stats = crawler.crawl()
            logger.info("크롤링 완료")

        # 결과 출력
        logger.info(f"수집된 아파트: {len(stats.get('apartments', []))}개")
        logger.info(f"수집된 거래: {len(stats.get('transactions', []))}개")

        # CSV 파일 통계
        if hasattr(crawler, "hogangnono_writer") and hasattr(
            crawler.hogangnono_writer, "get_stats"
        ):
            csv_stats = crawler.hogangnono_writer.get_stats()
            logger.info("결과 파일:")
            logger.info(f"  - complexes.csv: {csv_stats.get('complexes_record_count', 0)}개 레코드")
            logger.info(
                f"  - transactions.csv: {csv_stats.get('transactions_record_count', 0)}개 레코드"
            )

    except Exception as e:
        logger.error(f"크롤링 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

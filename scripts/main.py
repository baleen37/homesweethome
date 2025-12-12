import argparse
from pathlib import Path
import asyncio

from crawler.config import CrawlerConfig
from crawler.crawlers.integrated_crawler import IntegratedCrawler, CrawlMethod


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
        print(f"설정 오류: {e}")
        exit(1)

    # 출력 디렉토리 생성
    args.output.mkdir(parents=True, exist_ok=True)

    # 크롤링 실행
    asyncio.run(run_crawler(config, args.output, args.region))


async def run_crawler(config: CrawlerConfig, output_dir: Path, region: str = None) -> None:
    """크롤러 실행"""
    crawler = IntegratedCrawler(
        config=config,
        output_dir=output_dir,
        method=CrawlMethod.AUTO,
    )

    try:
        if region:
            print(f"'{region}' 지역 크롤링 시작...")
            stats = await crawler.crawl_specific_region(region)
            print(f"\n=== {region} 지역 크롤링 완료 ===")
        else:
            print("전체 지역 크롤링 시작...")
            stats = await crawler.crawl_all()
            print("\n=== 크롤링 완료 ===")

        # 결과 출력
        print(f"수집된 아파트: {stats['apartments_count']}개")
        print(f"소요 시간: {stats['duration_seconds']:.2f}초")

        # CSV 파일 통계
        if hasattr(crawler, "writer") and hasattr(crawler.writer, "get_stats"):
            csv_stats = crawler.writer.get_stats()
            print("\n결과 파일:")
            print(f"  - complexes.csv: {csv_stats.get('complexes_record_count', 0)}개 레코드")
            print(f"  - transactions.csv: {csv_stats.get('transactions_record_count', 0)}개 레코드")

    except Exception as e:
        print(f"\n크롤링 실패: {e}")
        exit(1)


if __name__ == "__main__":
    main()

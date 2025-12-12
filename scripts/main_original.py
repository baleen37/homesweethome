import argparse
from pathlib import Path
import asyncio
from typing import Optional, List

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.crawlers.integrated_crawler import IntegratedCrawler, CrawlMethod
from structlog import get_logger

logger = get_logger().bind(component="main")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HomeSweetHome Crawler - 호갱노노 부동산",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
크롤러 방식 선택:
  --method bbox      bbox 기반 크롤링만 사용 (지역 좌표 기반)
  --method search    검색 기반 크롤링만 사용 (키워드 기반)
  --method hybrid    두 방식 모두 사용 후 병합
  --method auto      자동 선택 (기본값, bbox 우선 후 검색)

사용 예시:
  # 기본 실행 (자동 선택)
  python scripts/main.py

  # bbox 기반으로 강남구만 크롤링
  python scripts/main.py --method bbox --district 강남구

  # 검색 기반으로 특정 키워드 크롤링
  python scripts/main.py --method search --keywords "강남구,서초구"

  # 두 방식 모두 사용
  python scripts/main.py --method hybrid --regions "서울특별시"

  # 특정 지역 크롤링
  python scripts/main.py --region gangnam
        """,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 디렉토리 경로 (기본: output/)",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["auto", "bbox", "search", "hybrid"],
        default="auto",
        help="크롤링 방식 선택 (기본값: auto)",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="특정 지역 크롤링 (예: gangnam, songpa, seoul)",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="검색 키워드 (예: '강남구,서초구,송파구')",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="중단된 지점부터 재개",
    )
    parser.add_argument(
        "--district",
        type=str,
        default=None,
        help="크롤링할 구 이름 (예: 강남구). 쉼표로 구분하여 여러 구 지정 가능",
    )
    parser.add_argument(
        "--regions",
        type=str,
        default=None,
        help="크롤링할 시/도 코드 (예: 11,26). 쉼표로 구분하여 여러 시/도 지정 가능",
    )
    parser.add_argument(
        "--districts",
        type=str,
        default=None,
        help="크롤링할 구/군 코드 (예: 11680,11650). 쉼표로 구분하여 여러 구/군 지정 가능. --district 인자보다 우선순위가 높음",
    )
    parser.add_argument(
        "--full-period",
        action="store_true",
        help="전체 기간 데이터 수집 (기본값: 최근 3년)",
    )

    args = parser.parse_args()

    # 출력 디렉토리 설정
    output_dir = args.output or Path("output")

    try:
        config = CrawlerConfig.from_env(output_file=str(output_dir))
    except ValueError as e:
        print(f"설정 오류: {e}")
        exit(1)

    # 키워드 처리
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    # 크롤링 방식 결정
    method = CrawlMethod(args.method)

    # 특정 지역 크롤링
    if args.region:
        print(f"'{args.region}' 지역 크롤링 시작...")
        asyncio.run(run_region_crawl(config, output_dir, args.region, method))
        return

    # 전통적인 인자들 처리 (하위 호환성)
    if args.district or args.regions or args.districts:
        print("하위 호환성 모드로 실행합니다...")
        asyncio.run(run_legacy_crawl(config, output_dir, args, method))
        return

    # 통합 크롤러 실행
    print("호갱노노 부동산 크롤링 시작...")
    print(f"크롤링 방식: {method.value}")
    if keywords:
        print(f"검색 키워드: {', '.join(keywords)}")
    if args.resume:
        print("체크포인트에서 재개합니다.")

    asyncio.run(run_integrated_crawl(config, output_dir, method, keywords))


async def run_integrated_crawl(
    config: CrawlerConfig,
    output_dir: Path,
    method: CrawlMethod,
    keywords: Optional[List[str]] = None,
):
    """통합 크롤러 실행"""
    crawler = IntegratedCrawler(
        config=config,
        output_dir=output_dir,
        method=method,
    )

    try:
        stats = await crawler.crawl_all(keywords=keywords)
        print("\n=== 크롤링 완료 ===")
        print(f"소요 시간: {stats['duration_seconds']:.2f}초")
        print(f"수집된 아파트: {stats['apartments_count']}개")

        # CSV 파일 통계
        csv_stats = crawler.writer.get_stats()
        print(f"\ncomplexes.csv: {csv_stats['complexes_record_count']}개 레코드")
        print(f"transactions.csv: {csv_stats['transactions_record_count']}개 레코드")

    except Exception as e:
        logger.error("crawling_failed", error=str(e))
        print(f"\n크롤링 실패: {e}")
        exit(1)


async def run_region_crawl(
    config: CrawlerConfig,
    output_dir: Path,
    region_name: str,
    method: CrawlMethod,
):
    """특정 지역 크롤링 실행"""
    crawler = IntegratedCrawler(
        config=config,
        output_dir=output_dir,
        method=method,
    )

    try:
        stats = await crawler.crawl_specific_region(region_name)
        print(f"\n=== {region_name} 지역 크롤링 완료 ===")
        print(f"수집된 아파트: {stats['apartments_count']}개")
        if "error" in stats:
            print(f"오류: {stats['error']}")

    except Exception as e:
        logger.error("region_crawling_failed", region=region_name, error=str(e))
        print(f"\n지역 크롤링 실패: {e}")
        exit(1)


async def run_legacy_crawl(
    config: CrawlerConfig,
    output_dir: Path,
    args,
    method: CrawlMethod,
):
    """하위 호환성을 위한 레거시 크롤링 실행"""
    # 기존 HogangnonoCrawler 사용
    crawler = HogangnonoCrawler(config, output_dir=output_dir)

    # regions 처리
    regions_filter = None
    if args.regions:
        regions_names = [r.strip() for r in args.regions.split(",") if r.strip()]

        # 지역 이름을 코드로 변환
        regions_response = crawler.hogangnono_client.get_regions()
        if regions_response.success:
            name_to_code = {}
            for region in regions_response.data:
                if isinstance(region, dict):
                    region_code = region["regionCode"]
                    if "fullName" in region:
                        name_to_code[region["fullName"]] = region_code
                    if "name" in region:
                        name_to_code[region["name"]] = region_code

            regions_filter = []
            for name in regions_names:
                if name in name_to_code:
                    regions_filter.append(name_to_code[name])
                elif name in name_to_code.values():
                    regions_filter.append(name)
                else:
                    print(f"오류: '{name}'은(는) 유효한 지역 이름이나 코드가 아닙니다.")
                    exit(1)

    # districts 처리
    districts_filter = None
    if args.districts:
        districts_filter = [d.strip() for d in args.districts.split(",") if d.strip()]

    try:
        stats = crawler.crawl(
            regions=regions_filter,
            districts=districts_filter,
            full_period=args.full_period,
        )
        print("\n=== 크롤링 완료 ===")
        print(f"처리된 동 수: {stats.get('dongs_processed', 0)}")

    except Exception as e:
        logger.error("legacy_crawling_failed", error=str(e))
        print(f"\n크롤링 실패: {e}")
        exit(1)

    # 결과 출력
    print("\n크롤링 완료!")
    print(f"  - 처리된 구/군: {stats.get('dongs_processed', 0)}/{stats.get('total_dongs', 0)}")
    print(f"  - 소요 시간: {stats.get('duration_seconds', 0):.1f}초")
    print("\n결과 파일:")
    print("  - 거래내역: output/transactions.csv")
    print("  - 단지 정보: output/complexes.csv")

    # 실패 리포트
    failed = crawler.checkpoint_manager.checkpoint.get("failed_dongs", [])
    if failed:
        print(f"\n실패한 동: {len(failed)}개")
        for fail in failed[:5]:  # 최대 5개만 출력
            # 다양한 데이터 형식을 지원하도록 안전한 처리
            dong_name = fail.get("dong_name", fail.get("name", "알 수 없음"))
            dong_code = fail.get("dong_code", fail.get("cortarNo", fail.get("code", "알 수 없음")))
            error = fail.get("error", "알 수 없는 오류")
            print(f"  - {dong_name} ({dong_code}): {error}")


if __name__ == "__main__":
    main()

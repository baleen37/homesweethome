import argparse
from datetime import datetime
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler - 네이버 부동산")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 파일 경로 (기본: output/seoul_apartments_{timestamp}.csv)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="중단된 지점부터 재개",
    )

    args = parser.parse_args()

    # 출력 파일명 생성
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/seoul_apartments_{timestamp}.csv")
    else:
        output_path = args.output

    config = CrawlerConfig.from_env()

    print("네이버 부동산 크롤링 시작...")
    if args.resume:
        print("체크포인트에서 재개합니다.")

    crawler = NaverRealEstateCrawler(config)
    results = crawler.crawl()

    writer = CSVWriter(output_path)

    # 첫 실행이면 write, 재개면 append
    if args.resume and output_path.exists():
        writer.append(results)
    else:
        writer.write(results)

    print(f"{len(results)}개 아파트 단지 정보를 {output_path}에 저장했습니다.")

    # 실패 리포트
    failed = crawler.checkpoint_manager.checkpoint.get("failed_dongs", [])
    if failed:
        print(f"\n실패한 동: {len(failed)}개")
        for fail in failed[:5]:  # 최대 5개만 출력
            print(f"  - {fail['dong_name']} ({fail['cortarNo']}): {fail['error']}")


if __name__ == "__main__":
    main()

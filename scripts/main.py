import argparse
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.static import StaticCrawler
from crawler.writers.csv_writer import CSVWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler")
    parser.add_argument(
        "--output",
        type=Path,
        default="output/data.csv",
        help="출력 파일 경로 (기본: output/data.csv)",
    )

    args = parser.parse_args()

    config = CrawlerConfig.from_env()

    crawler = StaticCrawler(config)

    results = crawler.crawl()

    writer = CSVWriter(args.output)
    writer.write(results)

    print(f"{len(results)}개 데이터를 {args.output}에 저장했습니다.")


if __name__ == "__main__":
    main()

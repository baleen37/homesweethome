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
    parser.add_argument(
        "--district",
        type=str,
        default=None,
        help="크롤링할 구 이름 (예: 강남구). 쉼표로 구분하여 여러 구 지정 가능",
    )

    args = parser.parse_args()

    # district_filter 처리
    district_filter = None
    if args.district:
        # 쉼표로 구분된 문자열을 리스트로 변환
        district_filter = [d.strip() for d in args.district.split(",") if d.strip()]

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
    if district_filter:
        print(f"대상 구: {', '.join(district_filter)}")

    crawler = NaverRealEstateCrawler(config)

    try:
        results = crawler.crawl(district_filter=district_filter)
    except ValueError as e:
        print(f"\n오류: {e}")
        print("\n사용 가능한 구 목록을 확인하려면 다음 명령을 실행하세요:")
        print("python -c \"from crawler.crawlers.naver import NaverRealEstateCrawler; from crawler.config import CrawlerConfig; c = NaverRealEstateCrawler(CrawlerConfig.from_env()); districts = [d['district_name'] for d in c.districts_data['districts']]; print(', '.join(sorted(districts)))\"")
        exit(1)

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

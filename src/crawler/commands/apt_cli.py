"""아파트 목록 크롤링 CLI"""

import argparse
from pathlib import Path

from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv
from src.crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="아파트 목록 크롤링 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dong-code",
        action="append",
        dest="dong_code",
        help="법정동 코드 (예: 1150010100). 여러 번 사용 가능.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="서울 전체 법정동 크롤링",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output/apt_list.csv",
        help="출력 CSV 경로 (기본값: output/apt_list.csv)",
    )

    return parser.parse_args()


def main() -> None:
    """메인 진입점"""
    args = parse_args()

    # 동 코드 결정
    if args.all:
        dong_codes = list(SEOUL_LEGAL_DONG_CODES.keys())
    elif args.dong_code:
        dong_codes = args.dong_code
    else:
        # 기본값: 5개 샘플 동
        dong_codes = list(SEOUL_LEGAL_DONG_CODES.keys())[:5]

    output_path = Path(args.output)

    crawl_apt_list_to_csv(
        dong_codes=dong_codes,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()

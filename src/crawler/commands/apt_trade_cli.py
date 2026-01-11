"""아파트 기본정보 + 실거래가 크롤링 CLI"""

import argparse
from pathlib import Path

from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
from src.crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="아파트 기본정보 + 실거래가 크롤링 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dong-code",
        action="append",
        dest="dong_code",
        help="법정동 코드 (예: 1150010100). 여러 번 사용 가능.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="출력 디렉토리 (기본값: output)",
    )

    return parser.parse_args()


def main() -> None:
    """메인 진입점"""
    args = parse_args()

    # 동 코드 결정
    if args.dong_code:
        dong_codes = args.dong_code
    else:
        # 기본값: 5개 샘플 동
        dong_codes = list(SEOUL_LEGAL_DONG_CODES.keys())[:5]

    output_dir = Path(args.output)
    apt_output_path = output_dir / "apt_list.csv"
    trade_output_path = output_dir / "trade_price.csv"

    crawl_apt_and_trade(
        dong_codes=dong_codes,
        apt_output_path=apt_output_path,
        trade_output_path=trade_output_path,
    )


if __name__ == "__main__":
    main()

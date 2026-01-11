"""아파트 기본정보 + 실거래가 크롤링 CLI"""

from pathlib import Path

from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
from src.crawler.commands.cli_common import (
    add_output_argument,
    create_dong_code_parser,
    resolve_dong_codes,
)


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = create_dong_code_parser("아파트 기본정보 + 실거래가 크롤링 CLI")
    add_output_argument(
        parser,
        default="output",
        help="출력 디렉토리 (기본값: output)",
    )

    return parser.parse_args()


def main() -> None:
    """메인 진입점"""
    args = parse_args()

    dong_codes = resolve_dong_codes(args, has_all_flag=False)

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

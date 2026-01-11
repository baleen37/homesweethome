"""아파트 목록 크롤링 CLI"""

from pathlib import Path

from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv
from src.crawler.commands.cli_common import (
    add_all_argument,
    add_output_argument,
    create_dong_code_parser,
    resolve_dong_codes,
)


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = create_dong_code_parser("아파트 목록 크롤링 CLI")
    add_all_argument(parser)
    add_output_argument(
        parser,
        default="output/apt_list.csv",
        help="출력 CSV 경로 (기본값: output/apt_list.csv)",
    )

    return parser.parse_args()


def main() -> None:
    """메인 진입점"""
    args = parse_args()

    dong_codes = resolve_dong_codes(args, has_all_flag=True)
    output_path = Path(args.output)

    crawl_apt_list_to_csv(
        dong_codes=dong_codes,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()

"""아파트 목록 크롤링 명령어"""

from pathlib import Path

from src.crawler.asil import AsilAptListCrawler
from src.crawler.export.csv_export import export_apt_list_to_csv


def crawl_apt_list_to_csv(
    dong_codes: list[str],
    output_path: Path,
) -> int:
    """
    아파트 목록을 크롤링하여 CSV로 내보냅니다.

    Args:
        dong_codes: 법정동 코드 리스트
        output_path: 출력 CSV 경로

    Returns:
        아파트 수
    """
    all_apts = []

    for dong_code in dong_codes:
        print(f"동 코드 {dong_code} 조회 중...")
        apt_crawler = AsilAptListCrawler(dong_code=dong_code)
        apt_list = apt_crawler.crawl()
        all_apts.extend(apt_list)
        print(f"  - {len(apt_list)}개 아파트 찾음")

    export_apt_list_to_csv(all_apts, output_path)
    print(f"완료: {len(all_apts)}개 아파트 → {output_path}")

    return len(all_apts)

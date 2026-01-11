"""아파트 목록 크롤링 명령어"""

from pathlib import Path

from src.crawler.asil import AsilAptListCrawler
from src.crawler.dto.asil_apt_list import AsilAptListDTO
from src.crawler.export.csv_export import export_apt_list_to_csv


def deduplicate_apts(apts: list[AsilAptListDTO]) -> list[AsilAptListDTO]:
    """seq 기준 중복 제거 (좌표가 있는 버전 우선)

    Args:
        apts: 아파트 DTO 리스트

    Returns:
        중복 제거된 아파트 리스트
    """
    # seq를 키로 하여, 좌표 정보가 더 좋은 버전을 우선 선택
    apt_map: dict[str, AsilAptListDTO] = {}

    for apt in apts:
        seq = apt.seq
        if seq not in apt_map:
            apt_map[seq] = apt
        else:
            # 기존 데이터와 비교해서 좌표가 있는 쪽 선택
            existing = apt_map[seq]
            # lat/lng가 0이면 좌표 없는 것으로 간주
            has_coord = apt.lat != 0 and apt.lng != 0
            existing_has_coord = existing.lat != 0 and existing.lng != 0

            if has_coord and not existing_has_coord:
                apt_map[seq] = apt
            # 둘 다 좌표가 있거나 없으면 첫 번째 것 유지

    return list(apt_map.values())


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

    # 중복 제거
    before_count = len(all_apts)
    all_apts = deduplicate_apts(all_apts)
    after_count = len(all_apts)
    removed = before_count - after_count

    export_apt_list_to_csv(all_apts, output_path)
    print(f"완료: {after_count}개 아파트 → {output_path} (중복 {removed}개 제거)")

    return after_count

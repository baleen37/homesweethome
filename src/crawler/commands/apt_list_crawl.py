"""아파트 목록 크롤링 명령어"""

from pathlib import Path

from src.crawler.asil import AsilAptListCrawler
from src.crawler.dto.asil_apt_list import AsilAptListDTO
from src.crawler.export.csv_export import export_apt_list_to_csv
from src.crawler.utils.dong_detector import RepresentativeDongDetector


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

    대표동 감지 기능을 사용하여 중복 크롤링을 방지합니다.
    ASIL API는 대표동(예: 문래동) 조회 시 해당 지역 전체를 반환하므로,
    이미 처리된 그룹에 속한 동은 자동으로 스킵합니다.

    Args:
        dong_codes: 법정동 코드 리스트
        output_path: 출력 CSV 경로

    Returns:
        아파트 수
    """
    detector = RepresentativeDongDetector()
    all_apts = []
    skipped_count = 0

    for dong_code in dong_codes:
        print(f"동 코드 {dong_code} 조회 중...")
        apt_crawler = AsilAptListCrawler(dong_code=dong_code)
        apt_list = apt_crawler.crawl()

        if not apt_list:
            print("  - 데이터 없음")
            continue

        # 대표동 감지: 이미 처리된 그룹이면 스킵
        if detector.should_skip(apt_list):
            group = detector.get_dong_group(apt_list)
            print(f"  - {len(apt_list)}개 찾음 (그룹 '{group}' 이미 처리됨, 스킵)")
            skipped_count += 1
            continue

        # 대표동인 경우 통계 출력
        if detector.is_representative(apt_list):
            group = detector.get_dong_group(apt_list)
            dong_codes_in_group = detector.get_dong_codes(apt_list)
            print(
                f"  - {len(apt_list)}개 찾음 (대표동, 그룹: {group}, "
                f"포함된 동: {len(dong_codes_in_group)}개)"
            )
        else:
            print(f"  - {len(apt_list)}개 찾음")

        all_apts.extend(apt_list)

    # 최종 중복 제거 (seq 기준)
    before_count = len(all_apts)
    all_apts = deduplicate_apts(all_apts)
    after_count = len(all_apts)
    removed = before_count - after_count

    export_apt_list_to_csv(all_apts, output_path)

    stats = detector.get_stats()
    print("\n=== 크롤링 통계 ===")
    print(f"처리된 동 그룹: {stats['seen_groups']}개")
    print(f"스킵된 동: {skipped_count}개")
    print(f"중복 제거: {removed}개 ({before_count} → {after_count})")
    print(f"완료: {after_count}개 아파트 → {output_path}")

    return after_count

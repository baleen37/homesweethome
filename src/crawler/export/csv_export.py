"""CSV 내보내기 유틸리티"""

import csv
from pathlib import Path

from src.crawler.dto.asil_apt_list import AsilAptListDTO


def export_apt_list_to_csv(
    data: list[AsilAptListDTO],
    output_path: Path,
) -> None:
    """
    아파트 기본정보를 CSV로 내보냅니다.

    CSV 필드: seq, name, dong, dongname, build_year, household, lat, lng

    Args:
        data: 아파트 기본정보 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seq",
        "name",
        "dong",
        "dongname",
        "build_year",
        "household",
        "lat",
        "lng",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for apt in data:
            row = {
                "seq": apt.seq,
                "name": apt.name,
                "dong": apt.dong,
                "dongname": apt.dongname,
                "build_year": apt.build_year or "",
                "household": apt.household or "",
                "lat": apt.lat or "",
                "lng": apt.lng or "",
            }
            writer.writerow(row)

"""
서울시 구/동 데이터 수집 스크립트

네이버 부동산 사이트를 Playwright로 탐색하여 서울시 전체 구/동 목록과
cortarNo, 좌표 범위를 수집합니다.

실행: python scripts/collect_seoul_data.py
"""

import json
from pathlib import Path
from typing import Any


def collect_seoul_districts() -> dict[str, Any]:
    """
    네이버 부동산에서 서울시 구/동 데이터 수집

    TODO: 실제 구현 필요
    - 네이버 부동산 지역 검색 페이지 접속
    - 서울시 선택 후 구/동 목록 추출
    - 각 동의 cortarNo와 좌표 범위 추출
    """
    # 임시로 샘플 데이터 반환 (실제로는 크롤링해야 함)
    return {
        "districts": [
            {
                "district_name": "강남구",
                "district_code": "1168000000",
                "dongs": [
                    {
                        "dong_name": "삼성동",
                        "cortarNo": "1168010100",
                        "bounds": {
                            "leftLon": 127.05,
                            "rightLon": 127.07,
                            "topLat": 37.52,
                            "bottomLat": 37.50,
                        },
                    },
                    {
                        "dong_name": "역삼동",
                        "cortarNo": "1168010200",
                        "bounds": {
                            "leftLon": 127.03,
                            "rightLon": 127.05,
                            "topLat": 37.51,
                            "bottomLat": 37.49,
                        },
                    },
                ],
            },
            {
                "district_name": "서초구",
                "district_code": "1165000000",
                "dongs": [
                    {
                        "dong_name": "반포동",
                        "cortarNo": "1165010100",
                        "bounds": {
                            "leftLon": 126.99,
                            "rightLon": 127.01,
                            "topLat": 37.51,
                            "bottomLat": 37.49,
                        },
                    },
                ],
            },
        ]
    }


def main() -> None:
    print("서울시 구/동 데이터 수집 중...")

    data = collect_seoul_districts()

    output_path = Path("src/crawler/data/seoul_districts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total_dongs = sum(len(d["dongs"]) for d in data["districts"])
    print(f"✓ {len(data['districts'])}개 구, {total_dongs}개 동 데이터 저장")
    print(f"✓ 저장 위치: {output_path}")


if __name__ == "__main__":
    main()

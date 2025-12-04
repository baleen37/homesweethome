#!/usr/bin/env python3
"""서울시 수집 데이터를 통합하여 최종 JSON 파일 생성"""

import json
from pathlib import Path
from typing import Any


def calculate_bounds(center_lat: float, center_lon: float) -> dict[str, float]:
    """중심 좌표로부터 대략적인 bounds 계산

    Args:
        center_lat: 중심 위도
        center_lon: 중심 경도

    Returns:
        bounds 딕셔너리 (leftLon, rightLon, topLat, bottomLat)
    """
    # ±0.01도씩 확장 (약 1km)
    delta = 0.01
    return {
        "leftLon": center_lon - delta,
        "rightLon": center_lon + delta,
        "topLat": center_lat + delta,
        "bottomLat": center_lat - delta,
    }


def load_json(file_path: Path) -> Any:
    """JSON 파일 로드"""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """메인 통합 로직"""
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"

    # 1. 구 목록 로드
    districts_data = load_json(output_dir / "seoul_districts_step1.json")
    districts_map = {
        district["cortarName"]: {"cortarNo": district["cortarNo"], "dongs": []}
        for district in districts_data["regionList"]
    }

    # 2. 동 목록 로드 (step1~step5)
    dong_files = [
        "seoul_dongs_step1.json",
        "seoul_dongs_step2.json",
        "seoul_dongs_step3.json",
        "seoul_dongs_step4.json",
        "seoul_dongs_step5.json",
    ]

    for dong_file in dong_files:
        dong_data = load_json(output_dir / dong_file)

        # step1은 직접 구 이름을 키로 사용
        if dong_file == "seoul_dongs_step1.json":
            for district_name, district_info in dong_data.items():
                if district_name in districts_map:
                    for dong in district_info["dongs"]:
                        districts_map[district_name]["dongs"].append(
                            {
                                "dong_name": dong["cortarName"],
                                "cortarNo": dong["cortarNo"],
                                "bounds": calculate_bounds(dong["centerLat"], dong["centerLon"]),
                            }
                        )
        # step2~step3는 구 이름을 키로 사용하지만 regionList 사용
        elif dong_file in ["seoul_dongs_step2.json", "seoul_dongs_step3.json"]:
            for district_name, district_info in dong_data.items():
                if district_name in districts_map:
                    for dong in district_info["regionList"]:
                        districts_map[district_name]["dongs"].append(
                            {
                                "dong_name": dong["cortarName"],
                                "cortarNo": dong["cortarNo"],
                                "bounds": calculate_bounds(dong["centerLat"], dong["centerLon"]),
                            }
                        )
        # step4~step5는 districts 배열 사용
        else:
            for district_info in dong_data["districts"]:
                district_name = district_info["cortarName"]
                if district_name in districts_map:
                    for dong in district_info["dongs"]:
                        districts_map[district_name]["dongs"].append(
                            {
                                "dong_name": dong["cortarName"],
                                "cortarNo": dong["cortarNo"],
                                "bounds": calculate_bounds(dong["centerLat"], dong["centerLon"]),
                            }
                        )

    # 3. 최종 JSON 구조 생성
    final_data = {
        "districts": [
            {
                "district_name": district_name,
                "district_code": district_info["cortarNo"],
                "dongs": district_info["dongs"],
            }
            for district_name, district_info in sorted(districts_map.items())
        ]
    }

    # 4. 출력 디렉토리 생성
    data_dir = base_dir / "src" / "crawler" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 5. 최종 JSON 파일 저장
    output_file = data_dir / "seoul_districts.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    # 6. 통계 출력
    total_dongs = sum(len(d["dongs"]) for d in final_data["districts"])
    print(f"✓ 최종 JSON 파일 생성 완료: {output_file}")
    print(f"  - 구 개수: {len(final_data['districts'])}개")
    print(f"  - 동 개수: {total_dongs}개")

    # 각 구별 동 개수 출력
    print("\n구별 동 개수:")
    for district in final_data["districts"]:
        print(f"  - {district['district_name']}: {len(district['dongs'])}개")


if __name__ == "__main__":
    main()

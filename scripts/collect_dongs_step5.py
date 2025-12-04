"""
서울시 21-25번째 구(마지막)의 동 목록 수집 스크립트

대상 구:
21. 용산구 (1117000000)
22. 은평구 (1138000000)
23. 종로구 (1111000000)
24. 중구 (1114000000)
25. 중랑구 (1126000000)

실행: python scripts/collect_dongs_step5.py
"""

import json
from pathlib import Path
from typing import Any

# 대상 구 정보
TARGET_DISTRICTS = [
    {"cortarNo": "1117000000", "cortarName": "용산구"},
    {"cortarNo": "1138000000", "cortarName": "은평구"},
    {"cortarNo": "1111000000", "cortarName": "종로구"},
    {"cortarNo": "1114000000", "cortarName": "중구"},
    {"cortarNo": "1126000000", "cortarName": "중랑구"},
]


def load_districts() -> list[dict[str, Any]]:
    """output/seoul_districts_step1.json에서 구 목록 로드"""
    input_path = Path("output/seoul_districts_step1.json")
    with open(input_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data["regionList"]  # type: ignore[no-any-return]


def main() -> None:
    print("서울시 21-25번째 구(마지막)의 동 목록 수집 중...")
    print("=" * 60)

    # Playwright MCP를 사용하여 동 목록 수집
    print("\n[안내] Playwright MCP를 사용하여 동 목록을 수집합니다.")
    print("이 스크립트는 수동으로 Playwright MCP 도구를 호출해야 합니다.\n")

    result: dict[str, Any] = {"districts": []}

    for target in TARGET_DISTRICTS:
        print(f"\n처리 중: {target['cortarName']} ({target['cortarNo']})")
        print(f"API URL: https://new.land.naver.com/api/regions/list?cortarNo={target['cortarNo']}")

        # 여기서 실제로는 Playwright MCP를 통해 API 호출 결과를 받아야 함
        # 임시로 빈 배열 할당
        district_data = {
            "cortarNo": target["cortarNo"],
            "cortarName": target["cortarName"],
            "dongs": [],
        }
        result["districts"].append(district_data)

    # 결과 저장
    output_path = Path("output/seoul_dongs_step5.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 통계 출력
    print("\n" + "=" * 60)
    print("수집 완료 통계:")
    print("=" * 60)

    total_dongs = 0
    for district in result["districts"]:
        dong_count = len(district["dongs"])
        total_dongs += dong_count
        print(f"  - {district['cortarName']}: {dong_count}개 동")

    print(f"\n총 동 개수: {total_dongs}개")
    print(f"저장 위치: {output_path.absolute()}")


if __name__ == "__main__":
    main()

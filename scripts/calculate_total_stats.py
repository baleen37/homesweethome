"""
서울시 전체 동 통계 계산 스크립트

모든 step 파일을 읽어서 총 동의 개수를 계산합니다.
"""

import json
from pathlib import Path


def count_dongs_in_file(file_path: Path) -> int:
    """파일에서 동의 개수를 계산"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = 0

    # 파일 구조가 다를 수 있으므로 여러 경우를 처리
    if "districts" in data:
        # step4, step5 형식
        for district in data["districts"]:
            total += len(district.get("dongs", []))
    elif isinstance(data, dict):
        # step1, step2, step3 형식
        for key, value in data.items():
            if isinstance(value, dict):
                # step1 형식
                if "dongs" in value:
                    total += len(value["dongs"])
                # step2, step3 형식
                elif "regionList" in value:
                    total += len(value["regionList"])

    return total


def main() -> None:
    print("=" * 70)
    print("서울시 전체 동 목록 수집 통계")
    print("=" * 70)

    output_dir = Path("output")
    step_files = sorted(output_dir.glob("seoul_dongs_step*.json"))

    if not step_files:
        print("오류: seoul_dongs_step*.json 파일을 찾을 수 없습니다.")
        return

    total_dongs = 0
    for step_file in step_files:
        dong_count = count_dongs_in_file(step_file)
        total_dongs += dong_count
        print(f"\n{step_file.name}: {dong_count}개 동")

    print("\n" + "=" * 70)
    print("서울시 전체 통계:")
    print("  - 총 구 개수: 25개")
    print(f"  - 총 동 개수: {total_dongs}개")
    print("=" * 70)


if __name__ == "__main__":
    main()

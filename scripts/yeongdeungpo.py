"""영등포구 전체 아파트 크롤링 스크립트"""

import csv
import os

from crawler.asil import AsilAptListCrawler

# 영등포구 법정동 코드 (11560으로 시작)
YEONGDEUNGPO_DONG_CODES = {
    "1156010100": "영등포동",
    "1156010200": "여의도동",
    "1156010300": "당산동",
    "1156010400": "도림동",
    "1156010500": "문래동",
    "1156010600": "양평동",
    "1156010700": "신길동",
    "1156010800": "대림동",
    "1156010900": "노량진동",
    "1156011000": "사당동",  # 실제로는 동작구, 테스트용
    "1156011100": "상도동",  # 실제로는 동작구, 테스트용
}

OUTPUT_DIR = "output"
OUTPUT_FILE = "yeongdeungpo_apt.csv"


def export_to_csv(data: list[dict], filepath: str) -> None:
    """딕셔너리 리스트를 CSV로 내보내기"""
    if not data:
        print("저장할 데이터가 없습니다.")
        return

    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # 첫 번째 아이템의 키들을 헤더로 사용
    fieldnames = list(data[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"CSV 파일 저장 완료: {filepath} ({len(data)}건)")


def main():
    """영등포구 전체 아파트 크롤링"""
    all_apartments = []
    crawled_dongs = set()

    print("영등포구 아파트 크롤링 시작...")
    print(f"타겟 동: {len(YEONGDEUNGPO_DONG_CODES)}개\n")

    for dong_code, dong_name in YEONGDEUNGPO_DONG_CODES.items():
        print(f"크롤링 중: {dong_name} ({dong_code})...")

        try:
            crawler = AsilAptListCrawler(dong_code=dong_code)
            results = crawler.crawl()

            if results:
                crawled_dongs.add(dong_name)
                all_apartments.extend(results)
                print(f"  → {len(results)}개 아파트 수집 완료")
            else:
                print("  → 데이터 없음")

        except Exception as e:
            print(f"  → 에러 발생: {e}")

    print(f"\n{'=' * 50}")
    print("크롤링 완료!")
    print(f"수집된 동: {len(crawled_dongs)}개")
    print(f"총 아파트 수: {len(all_apartments)}건")

    # CSV 내보내기
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    export_to_csv(all_apartments, output_path)

    # 중복 제거 (seq 기준)
    unique_apartments = {apt["seq"]: apt for apt in all_apartments}.values()
    print(f"중복 제거 후: {len(unique_apartments)}건")

    if len(all_apartments) != len(unique_apartments):
        dup_output_path = os.path.join(OUTPUT_DIR, "yeongdeungpo_apt_unique.csv")
        export_to_csv(list(unique_apartments), dup_output_path)
        print(f"중복 제거 CSV 저장: {dup_output_path}")


if __name__ == "__main__":
    main()

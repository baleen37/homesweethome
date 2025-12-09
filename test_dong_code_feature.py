#!/usr/bin/env python3
"""동 코드 기능 테스트"""

import sys
import json
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig


def test_dong_code_fetching():
    """동 코드 가져오기 테스트"""
    print("동 코드 기능 테스트")
    print("=" * 50)

    # 크롤러 초기화
    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config, output_dir="output/test")

    # 강남구 동 코드 테스트
    print("\n1. 강남구 동 코드 테스트")
    gangnam_dongs = crawler.fetch_dong_codes("강남구", lat=37.517305, lng=127.047502)
    print(f"   찾은 동 수: {len(gangnam_dongs)}")
    for dong_name, dong_code in gangnam_dongs.items():
        print(f"   - {dong_name}: {dong_code}")

    # 특정 동 코드 조회 테스트
    print("\n2. 특정 동 코드 조회 테스트")
    test_dongs = ["청담동", "신사동", "역삼동"]
    for dong_name in test_dongs:
        dong_code = crawler.get_dong_code("강남구", dong_name)
        if dong_code:
            print(f"   ✓ {dong_name}: {dong_code}")
        else:
            print(f"   ✗ {dong_name}: 찾지 못함")

    # 서초구 동 코드 테스트
    print("\n3. 서초구 동 코드 테스트")
    seocho_dongs = crawler.fetch_dong_codes("서초구", lat=37.483735, lng=127.005732)
    print(f"   찾은 동 수: {len(seocho_dongs)}")
    for dong_name, dong_code in list(seocho_dongs.items())[:5]:  # 처음 5개만
        print(f"   - {dong_name}: {dong_code}")

    # 저장된 매핑 정보 확인
    print("\n4. 저장된 매핑 정보")
    mapping_file = Path("output/test/dong_code_mapping.json")
    if mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"   저장된 구/군 수: {len(mapping)}")
        for district, dongs in mapping.items():
            print(f"   - {district}: {len(dongs)}개 동")
    else:
        print("   매핑 파일이 없습니다")

    print("\n✅ 테스트 완료")


def test_dong_name_parsing():
    """주소에서 동 이름 추출 테스트"""
    print("\n\n동 이름 파싱 테스트")
    print("=" * 50)

    test_addresses = [
        ("서울특별시 강남구 청담동 123-45", "강남구", "청담동"),
        ("서울특별시 서초구 서초동 678-90", "서초구", "서초동"),
        ("서울 강남구 역삼동 111-22", "강남구", "역삼동"),
        ("경기도 성남시 분당구 판교동", None, None),  # 서울 외
    ]

    def parse_dong_from_address(address: str) -> tuple[str, str] | tuple[None, None]:
        """주소에서 구와 동 이름 추출"""
        if "서울특별시" not in address and not address.startswith("서울 "):
            return None, None

        # '구'와 '동' 찾기
        parts = address.split()
        gu = None
        dong = None

        for i, part in enumerate(parts):
            if part.endswith("구") and "시" not in part:
                gu = part
                # 다음 파트가 동인지 확인
                if i + 1 < len(parts) and parts[i + 1].endswith("동"):
                    dong = parts[i + 1]
                break

        return gu, dong

    for address, expected_gu, expected_dong in test_addresses:
        gu, dong = parse_dong_from_address(address)
        print(f"\n주소: {address}")
        print(f"  파싱 결과: {gu}, {dong}")
        print(f"  예상 결과: {expected_gu}, {expected_dong}")
        if gu == expected_gu and dong == expected_dong:
            print("  ✓ 일치")
        else:
            print("  ✗ 불일치")


if __name__ == "__main__":
    test_dong_code_fetching()
    test_dong_name_parsing()

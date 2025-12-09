#!/usr/bin/env python3
"""동 코드 전체 기능 테스트"""

import sys
import json
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig
from crawler.writers.transaction_csv_writer import TransactionCSVWriter


def test_dong_address_parsing():
    """주소 파싱 테스트"""
    print("주소 파싱 테스트")
    print("=" * 50)

    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config, output_dir="output/test")

    test_addresses = [
        "서울특별시 강남구 청담동 123-45",
        "서울특별시 서초구 서초동 678-90",
        "서울특별시 강남구 역삼동 825-24",
        "서울특별시 강남구 신사동 510-11",
        "서울 강남구 삼성동 123",
        "경기도 성남시 분당구 판교동",  # 서울 외
    ]

    for address in test_addresses:
        gu, dong = crawler._parse_gu_dong_from_address(address)
        print(f"\n주소: {address}")
        print(f"  구: {gu}")
        print(f"  동: {dong}")


def test_dong_code_with_csv():
    """CSV에 동 코드 저장 테스트"""
    print("\n\nCSV에 동 코드 저장 테스트")
    print("=" * 50)

    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config, output_dir="output/test")

    # 테스트 데이터
    test_items = [
        {
            "id": "test_001",
            "name": "테스트아파트",
            "address": "서울특별시 강남구 청담동 123-45",
            "trade": {
                "type": "sale",
                "price": 1000000000,
                "date": "2024-01-15",
                "floor": 5,
                "area": "84.97",
            },
        },
        {
            "id": "test_002",
            "name": "테스트오피스텔",
            "address": "서울특별시 서초구 서초동 678-90",
            "trade": {
                "type": "jeonse",
                "deposit": 500000000,
                "date": "2024-02-20",
                "floor": 3,
                "area": "59.34",
            },
        },
        {
            "id": "test_003",
            "name": "테스트빌딩",
            "address": "서울특별시 강남구 역삼동 825-24",
            "trade": {
                "type": "monthly",
                "deposit": 300000000,
                "monthly": 1000000,
                "date": "2024-03-10",
                "floor": 10,
                "area": "115.32",
            },
        },
    ]

    # 데이터 매핑
    mapped_data = []
    for item in test_items:
        mapped = crawler._map_to_naver_format(item)
        if mapped:
            mapped_data.append(mapped)
            print(f"\n매핑 결과: {mapped['complex_name']}")
            print(f"  주소: {mapped['address']}")
            print(f"  구: {mapped['gu_name']} (코드: {mapped['gu_code']})")
            print(f"  동: {mapped['dong_name']} (코드: {mapped['dong_code']})")

    # CSV 저장
    if mapped_data:
        csv_file = Path("output/test/test_transactions_with_dong.csv")
        writer = TransactionCSVWriter(csv_file)

        # 데이터 쓰기 (헤더 포함)
        writer.write(mapped_data, mode="w")

        print(f"\n✅ CSV 저장 완료: {csv_file}")

        # CSV 내용 확인
        print("\nCSV 파일 내용 (처음 3줄):")
        with open(csv_file, "r", encoding="utf-8") as f:
            lines = f.readlines()[:3]
            for line in lines:
                print(line.strip())


def test_dong_mapping_file():
    """동 코드 매핑 파일 확인"""
    print("\n\n동 코드 매핑 파일 확인")
    print("=" * 50)

    mapping_file = Path("output/test/dong_code_mapping.json")
    if mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        print(f"저장된 구/군 수: {len(mapping)}")
        for district, dongs in mapping.items():
            print(f"\n{district}:")
            for dong_name, dong_code in list(dongs.items())[:3]:  # 3개만 표시
                print(f"  - {dong_name}: {dong_code}")
            if len(dongs) > 3:
                print(f"  ... 외 {len(dongs) - 3}개")
    else:
        print("매핑 파일이 존재하지 않습니다")


if __name__ == "__main__":
    test_dong_address_parsing()
    test_dong_code_with_csv()
    test_dong_mapping_file()

    print("\n\n✅ 모든 테스트 완료")

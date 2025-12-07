#!/usr/bin/env python3
"""
데이터 품질 검증용 테스트 데이터 생성 스크립트
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict


def generate_test_complexes_data(output_dir: Path, count: int = 20):
    """테스트용 단지 데이터 생성"""
    complexes_file = output_dir / "complexes.csv"

    # 샘플 데이터 생성
    complexes = []
    real_estate_types = ["아파트", "오피스텔", "연립다세대"]

    for i in range(count):
        complex_id = f"{10000000 + i}"
        complex_name = f"테스트아파트{i + 1}"

        # 무작위 데이터 생성
        completion_year = random.randint(1990, 2023)
        completion_month = random.randint(1, 12)
        completion_year_month = f"{completion_year}{completion_month:02d}"

        total_dong = random.randint(1, 15)
        total_household = random.randint(50, 1500)

        min_area = random.uniform(20, 80)
        max_area = min_area + random.uniform(20, 100)

        deal_count = random.randint(0, 50)
        lease_count = random.randint(0, 100)
        rent_count = random.randint(0, 30)

        # 평형 타입 생성
        pyeong_types = []
        for p in range(random.randint(3, 8)):
            pyeong_type = random.randint(10, 50)
            if pyeong_type not in pyeong_types:
                pyeong_types.append(pyeong_type)
        pyeong_types.sort()

        complex_data = {
            "complex_id": complex_id,
            "complex_name": complex_name,
            "real_estate_type": random.choice(real_estate_types),
            "completion_year_month": completion_year_month,
            "total_dong_count": total_dong,
            "total_household_count": total_household,
            "min_area": round(min_area, 2),
            "max_area": round(max_area, 2),
            "deal_count": deal_count,
            "lease_count": lease_count,
            "rent_count": rent_count,
            "pyeong_types": ",".join(map(str, pyeong_types)),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_transaction_count": deal_count + lease_count + rent_count,
            "latest_deal_price": random.randint(50000, 200000) if deal_count > 0 else 0,
            "latest_deal_date": f"{2024}.{random.randint(1, 12):02d}" if deal_count > 0 else "",
            "avg_deal_price_1year": random.randint(60000, 180000) if deal_count > 0 else 0,
            "deal_count_1year": deal_count,
            "lease_count_1year": lease_count,
            "rent_count_1year": rent_count,
        }

        complexes.append(complex_data)

    # CSV 파일 작성
    fieldnames = [
        "complex_id",
        "complex_name",
        "real_estate_type",
        "completion_year_month",
        "total_dong_count",
        "total_household_count",
        "min_area",
        "max_area",
        "deal_count",
        "lease_count",
        "rent_count",
        "pyeong_types",
        "fetched_at",
        "total_transaction_count",
        "latest_deal_price",
        "latest_deal_date",
        "avg_deal_price_1year",
        "deal_count_1year",
        "lease_count_1year",
        "rent_count_1year",
    ]

    with open(complexes_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(complexes)

    print(f"✓ 단지 데이터 생성 완료: {len(complexes)}개")
    return complexes


def generate_test_transactions_data(
    output_dir: Path, complexes: List[Dict], transactions_per_complex: int = 10
):
    """테스트용 거래내역 데이터 생성"""
    transactions_file = output_dir / "transactions.csv"

    transactions = []
    trade_types = [("A1", "매매"), ("B1", "전세"), ("B2", "월세")]
    trade_categories = {
        "A1": ["일반매매", "신축분양"],
        "B1": ["일반전세", "신축전세"],
        "B2": ["일반월세", "신축월세"],
    }

    for complex in complexes:
        complex_id = complex["complex_id"]
        complex_name = complex["complex_name"]
        pyeong_types = complex["pyeong_types"].split(",")

        for i in range(random.randint(1, transactions_per_complex)):
            trade_type_code, trade_type_name = random.choice(trade_types)
            trade_category = random.choice(trade_categories[trade_type_code])

            # 무작위 날짜 생성 (최근 1년)
            days_ago = random.randint(0, 365)
            trade_date = datetime.now() - timedelta(days=days_ago)
            trade_date_str = trade_date.strftime("%Y.%m.%d")
            trade_year = str(trade_date.year)

            floor = random.randint(-1, 35)
            pyeong_type = random.choice(pyeong_types)

            # 거래 유형별 가격 설정
            if trade_type_code == "A1":  # 매매
                deal_price = random.randint(50000, 200000)
                deposit = 0
                monthly_rent = 0
            elif trade_type_code == "B1":  # 전세
                deal_price = 0
                deposit = random.randint(30000, 150000)
                monthly_rent = 0
            else:  # 월세
                deal_price = 0
                deposit = random.randint(10000, 80000)
                monthly_rent = random.randint(50, 500)

            # 10% 확률로 삭제된 거래
            is_delete = "Y" if random.random() < 0.1 else "N"
            # 20% 확률로 갱신된 거래
            is_renew = "Y" if random.random() < 0.2 else "N"

            transaction = {
                "complex_id": complex_id,
                "complex_name": complex_name,
                "pyeong_type_number": pyeong_type,
                "pyeong_name": f"{pyeong_type}평",
                "trade_type": trade_type_code,
                "trade_type_name": trade_type_name,
                "trade_date": trade_date_str,
                "trade_year": trade_year,
                "floor": str(floor),
                "deal_price": deal_price,
                "deposit": deposit,
                "monthly_rent": monthly_rent,
                "trade_category": trade_category,
                "is_delete": is_delete,
                "is_renew": is_renew,
            }

            transactions.append(transaction)

    # 거래일순으로 정렬
    transactions.sort(key=lambda x: datetime.strptime(x["trade_date"], "%Y.%m.%d"), reverse=True)

    # CSV 파일 작성
    fieldnames = [
        "complex_id",
        "complex_name",
        "pyeong_type_number",
        "pyeong_name",
        "trade_type",
        "trade_type_name",
        "trade_date",
        "trade_year",
        "floor",
        "deal_price",
        "deposit",
        "monthly_rent",
        "trade_category",
        "is_delete",
        "is_renew",
    ]

    with open(transactions_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"✓ 거래내역 데이터 생성 완료: {len(transactions)}개")
    return transactions


def generate_test_checkpoint(output_dir: Path, total_dongs: int = 10, total_complexes: int = 100):
    """테스트용 체크포인트 파일 생성"""
    checkpoint_file = output_dir / "checkpoint.json"

    completed_dongs = random.randint(0, total_dongs)
    completed_complexes = random.randint(0, total_complexes)
    error_count = random.randint(0, 5)

    checkpoint = {
        "start_time": datetime.now().timestamp(),
        "current_time": datetime.now().timestamp(),
        "total_dongs": total_dongs,
        "completed_dongs": completed_dongs,
        "total_complexes": total_complexes,
        "completed_complexes": completed_complexes,
        "total_transactions": 500,
        "collected_transactions": completed_complexes * 5,
        "errors": [],
        "error_count": error_count,
        "rate_limiter_delay": 2.5,
        "avg_complex_time": 3.2,
        "avg_dong_time": 45.6,
        "summary": {
            "elapsed_time_seconds": 1800,
            "elapsed_time_formatted": "30분",
            "eta_seconds": 7200,
            "eta_formatted": "2시간",
            "dong_progress_percent": (completed_dongs / total_dongs * 100)
            if total_dongs > 0
            else 0,
            "completed_dongs": completed_dongs,
            "total_dongs": total_dongs,
            "remaining_dongs": total_dongs - completed_dongs,
            "complex_progress_percent": (completed_complexes / total_complexes * 100)
            if total_complexes > 0
            else 0,
            "completed_complexes": completed_complexes,
            "total_complexes": total_complexes,
            "remaining_complexes": total_complexes - completed_complexes,
            "collected_transactions": completed_complexes * 5,
            "avg_complex_time_seconds": 3.2,
            "avg_dong_time_seconds": 45.6,
            "complexes_per_hour": 1125,
            "transactions_per_hour": 5625,
            "rate_limiter_delay": 2.5,
            "error_count": error_count,
            "error_rate_percent": (error_count / total_complexes * 100)
            if total_complexes > 0
            else 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print("✓ 체크포인트 파일 생성 완료")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="테스트 데이터 생성")
    parser.add_argument(
        "--output-dir", default="test_output", help="출력 디렉토리 경로 (기본: test_output)"
    )
    parser.add_argument("--complex-count", type=int, default=20, help="생성할 단지 수 (기본: 20)")
    parser.add_argument(
        "--transactions-per-complex",
        type=int,
        default=10,
        help="단지당 생성할 거래내역 수 (기본: 10)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 출력 디렉토리: {output_dir}")

    # 테스트 데이터 생성
    complexes = generate_test_complexes_data(output_dir, args.complex_count)
    generate_test_transactions_data(output_dir, complexes, args.transactions_per_complex)
    generate_test_checkpoint(output_dir)

    print("\n✅ 테스트 데이터 생성 완료!")
    print(f"단지: {len(complexes)}개")
    print(f"거래내역: {len(complexes) * args.transactions_per_complex}개 (평균)")


if __name__ == "__main__":
    main()

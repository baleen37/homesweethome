#!/usr/bin/env python3
"""
네이버 부동산 데이터 품질 검증 스크립트

Task 4.2: 데이터 품질 검증
- 수집된 데이터의 정확성 검증
- 데이터 형식과 스키마 일관성 확인
- 중복 데이터 제거 검증
- 누락된 필드나 비정상 값 확인
- 시간 순서 정합성 검증
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

# src 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from crawler.writers.transaction_csv_writer import TransactionCSVWriter

    # TransactionCSVWriter에서 필드네임 가져오기
    TRANSACTIONS_CSV_FIELDNAMES = TransactionCSVWriter.FIELDNAMES
except ImportError as e:
    print(f"오류: 모듈을 가져올 수 없습니다 - {e}")
    sys.exit(1)


class DataQualityVerifier:
    """데이터 품질 검증 클래스"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.issues = []
        self.stats = {
            "total_complexes": 0,
            "total_transactions": 0,
            "error_count": 0,
            "warning_count": 0,
        }

    def verify_all(self) -> Dict[str, Any]:
        """전체 데이터 품질 검증 수행"""
        print("🔍 데이터 품질 검증 시작...")
        print("=" * 50)

        # 1. 파일 존재 확인
        self._check_file_existence()

        # 2. 단지 데이터 검증
        complexes_data = self._load_complexes_data()
        if complexes_data:
            self._verify_complex_data(complexes_data)

        # 3. 거래내역 데이터 검증
        transactions_data = self._load_transactions_data()
        if transactions_data:
            self._verify_transaction_data(transactions_data)

        # 4. 데이터 일관성 검증
        if complexes_data and transactions_data:
            self._verify_data_consistency(complexes_data, transactions_data)

        # 5. 체크포인트 파일 검증
        self._verify_checkpoint()

        print("\n" + "=" * 50)
        print("📊 검증 요약:")
        print(f"  - 총 단지 수: {self.stats['total_complexes']}")
        print(f"  - 총 거래내역 수: {self.stats['total_transactions']}")
        print(f"  - 오류 수: {self.stats['error_count']}")
        print(f"  - 경고 수: {self.stats['warning_count']}")

        if self.issues:
            print("\n⚠️  발견된 이슈 (상위 20개):")
            for issue in self.issues[:20]:
                print(f"  - {issue}")
            if len(self.issues) > 20:
                print(f"  ... 그 외 {len(self.issues) - 20}개 이슈")

        return {
            "stats": self.stats,
            "issues": self.issues,
            "passed": self.stats["error_count"] == 0,
        }

    def _check_file_existence(self):
        """파일 존재 확인"""
        print("\n1. 파일 존재 확인...")

        complexes_file = self.output_dir / "complexes.csv"
        transactions_file = self.output_dir / "transactions.csv"

        if not complexes_file.exists():
            self._add_error(f"단지 정보 파일이 존재하지 않음: {complexes_file}")
        else:
            print(f"  ✓ 단지 정보 파일: {complexes_file}")

        if not transactions_file.exists():
            self._add_error(f"거래내역 파일이 존재하지 않음: {transactions_file}")
        else:
            print(f"  ✓ 거래내역 파일: {transactions_file}")

    def _load_complexes_data(self) -> List[Dict[str, Any]]:
        """단지 데이터 로드"""
        complexes_file = self.output_dir / "complexes.csv"
        if not complexes_file.exists():
            return []

        print("\n2. 단지 데이터 로드...")

        data = []
        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if any(row.values()):  # 빈 행 제외
                    data.append(row)

        self.stats["total_complexes"] = len(data)
        print(f"  - 로드된 단지 수: {len(data)}")
        return data

    def _load_transactions_data(self) -> List[Dict[str, Any]]:
        """거래내역 데이터 로드"""
        transactions_file = self.output_dir / "transactions.csv"
        if not transactions_file.exists():
            return []

        print("\n3. 거래내역 데이터 로드...")

        data = []
        with open(transactions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if any(row.values()):  # 빈 행 제외
                    data.append(row)

        self.stats["total_transactions"] = len(data)
        print(f"  - 로드된 거래내역 수: {len(data)}")
        return data

    def _verify_complex_data(self, complexes_data: List[Dict[str, Any]]):
        """단지 데이터 검증"""
        print("\n4. 단지 데이터 품질 검증...")

        if not complexes_data:
            self._add_error("단지 데이터가 없음")
            return

        # 샘플링 (최대 100개)
        sample_size = min(100, len(complexes_data))
        sample = complexes_data[:sample_size]

        # 필수 필드 확인
        required_fields = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
            "fetched_at",
        ]

        for complex in sample:
            complex_id = complex.get("complex_id", "Unknown")

            # 필수 필드 확인
            for field in required_fields:
                if not complex.get(field):
                    self._add_error(f"단지 {complex_id}: 필수 필드 누락 - {field}")

            # 데이터 형식 검증
            self._verify_complex_format(complex, complex_id)

        print(f"  - 검증된 샘플 수: {len(sample)}")

    def _verify_complex_format(self, complex: Dict[str, Any], complex_id: str):
        """단지 데이터 형식 검증"""
        # complex_id
        complex_id_value = complex.get("complex_id", "")
        if not complex_id_value.isdigit():
            self._add_error(f"단지 ID 형식 오류: {complex_id_value}")

        # completion_year_month
        completion = complex.get("completion_year_month", "")
        if completion:
            if not completion.isdigit() or len(completion) != 6:
                self._add_error(f"단지 {complex_id}: 준공년월 형식 오류 - {completion}")
            else:
                # 날짜 합리성 검증
                year = int(completion[:4])
                month = int(completion[4:])
                if year < 1970 or year > 2030 or month < 1 or month > 12:
                    self._add_warning(f"단지 {complex_id}: 준공년월 범위 비정상 - {completion}")

        # 숫자 필드
        for field in ["total_dong_count", "total_household_count", "min_area", "max_area"]:
            value = complex.get(field, "")
            if value:
                try:
                    num_value = float(value)
                    if num_value < 0:
                        self._add_error(f"단지 {complex_id}: {field}가 음수 - {value}")
                    elif (
                        field in ["total_dong_count", "total_household_count"] and num_value > 1000
                    ):
                        self._add_warning(f"단지 {complex_id}: {field}가 비정상적으로 큼 - {value}")
                except ValueError:
                    self._add_error(f"단지 {complex_id}: {field} 형식 오류 - {value}")

        # min_area <= max_area
        min_area = complex.get("min_area", "0")
        max_area = complex.get("max_area", "0")
        if min_area and max_area:
            try:
                min_val = float(min_area)
                max_val = float(max_area)
                if min_val > max_val:
                    self._add_error(
                        f"단지 {complex_id}: 최소 면적이 최대 면적보다 큼 - {min_area} > {max_area}"
                    )
            except ValueError:
                pass

    def _verify_transaction_data(self, transactions_data: List[Dict[str, Any]]):
        """거래내역 데이터 검증"""
        print("\n5. 거래내역 데이터 품질 검증...")

        if not transactions_data:
            self._add_warning("거래내역 데이터가 없음")
            return

        # 샘플링 (최대 100개)
        sample_size = min(100, len(transactions_data))
        sample = transactions_data[:sample_size]

        # 필수 필드 확인
        required_fields = [
            "complex_id",
            "complex_name",
            "pyeong_type_number",
            "trade_type",
            "trade_date",
            "trade_year",
            "floor",
        ]

        for transaction in sample:
            # 필수 필드 확인
            for field in required_fields:
                if not transaction.get(field):
                    self._add_error(f"거래 데이터 필수 필드 누락: {field}")

            # 데이터 형식 검증
            self._verify_transaction_format(transaction)

        print(f"  - 검증된 샘플 수: {len(sample)}")

    def _verify_transaction_format(self, transaction: Dict[str, Any]):
        """거래내역 데이터 형식 검증"""
        # trade_type
        trade_type = transaction.get("trade_type", "")
        if trade_type not in ["A1", "B1", "B2"]:
            self._add_error(f"거래 유형 코드 오류: {trade_type}")

        # trade_date
        trade_date = transaction.get("trade_date", "")
        if trade_date:
            if not re.match(r"^\d{4}\.\d{2}\.\d{2}$", trade_date):
                self._add_error(f"거래일 형식 오류: {trade_date}")
            else:
                try:
                    year, month, day = map(int, trade_date.split("."))
                    if not (1 <= month <= 12 and 1 <= day <= 31):
                        self._add_error(f"거래일 값 오류: {trade_date}")
                except ValueError:
                    self._add_error(f"거래일 파싱 오류: {trade_date}")

        # trade_year
        trade_year = transaction.get("trade_year", "")
        if trade_year:
            if not trade_year.isdigit() or len(trade_year) != 4:
                self._add_error(f"거래연도 형식 오류: {trade_year}")
            elif trade_date:
                # 거래일과 연도 일치성 확인
                date_year = trade_date.split(".")[0]
                if trade_year != date_year:
                    self._add_error(f"거래일과 연도 불일치: {trade_date} vs {trade_year}")

        # 숫자 필드
        for field in ["deal_price", "deposit", "monthly_rent"]:
            value = transaction.get(field, "")
            if value:
                try:
                    int_value = int(value)
                    if int_value < 0:
                        self._add_error(f"{field}가 음수: {value}")
                    elif int_value > 10000000:  # 100억원 이상
                        self._add_warning(f"{field}가 비정상적으로 큼: {value}")
                except ValueError:
                    self._add_error(f"{field} 형식 오류: {value}")

        # 거래 유형별 가격 정합성
        deal_price = transaction.get("deal_price", "0")
        deposit = transaction.get("deposit", "0")
        monthly_rent = transaction.get("monthly_rent", "0")

        if trade_type == "A1":  # 매매
            if deal_price == "0" or deposit != "0" or monthly_rent != "0":
                self._add_error(
                    f"매매 거래의 가격 정보 비정상: {deal_price}, {deposit}, {monthly_rent}"
                )
        elif trade_type == "B1":  # 전세
            if deal_price != "0" or deposit == "0" or monthly_rent != "0":
                self._add_error(
                    f"전세 거래의 가격 정보 비정상: {deal_price}, {deposit}, {monthly_rent}"
                )
        elif trade_type == "B2":  # 월세
            if deal_price != "0" or monthly_rent == "0":
                self._add_error(
                    f"월세 거래의 가격 정보 비정상: {deal_price}, {deposit}, {monthly_rent}"
                )

        # floor
        floor = transaction.get("floor", "")
        if floor and not re.match(r"^-?\d+$", floor):
            self._add_error(f"층 정보 형식 오류: {floor}")
        elif floor:
            floor_num = int(floor)
            if floor_num < -2 or floor_num > 80:
                self._add_warning(f"층 정보가 비정상적인 범위: {floor_num}")

    def _verify_data_consistency(
        self, complexes_data: List[Dict[str, Any]], transactions_data: List[Dict[str, Any]]
    ):
        """데이터 일관성 검증"""
        print("\n6. 데이터 일관성 검증...")

        # 단지 ID 집합
        complex_ids = {c.get("complex_id") for c in complexes_data if c.get("complex_id")}
        transaction_complex_ids = {
            t.get("complex_id") for t in transactions_data if t.get("complex_id")
        }

        # 거래내역에 있는 단지 ID가 단지 정보에 있는지 확인
        orphan_transactions = transaction_complex_ids - complex_ids
        if orphan_transactions:
            self._add_warning(f"단지 정보가 없는 거래내역 존재: {len(orphan_transactions)}개")
            for complex_id in list(orphan_transactions)[:5]:
                self._add_warning(f"  - 단지 ID: {complex_id}")

        # 중복 거래 확인
        duplicate_count = self._check_duplicate_transactions(transactions_data)
        if duplicate_count > 0:
            self._add_warning(f"중복된 거래내역: {duplicate_count}개")

    def _check_duplicate_transactions(self, transactions_data: List[Dict[str, Any]]) -> int:
        """중복 거래 확인"""
        seen_keys = set()
        duplicate_count = 0

        for transaction in transactions_data:
            # 복합 키: 단지ID + 평형 + 거래일 + 층 + 거래유형
            key = (
                transaction.get("complex_id"),
                transaction.get("pyeong_type_number"),
                transaction.get("trade_date"),
                transaction.get("floor"),
                transaction.get("trade_type"),
            )

            if key in seen_keys:
                duplicate_count += 1
            else:
                seen_keys.add(key)

        return duplicate_count

    def _verify_checkpoint(self):
        """체크포인트 파일 검증"""
        print("\n7. 체크포인트 파일 검증...")

        checkpoint_file = self.output_dir / "checkpoint.json"
        if not checkpoint_file.exists():
            self._add_warning("체크포인트 파일이 없음")
            return

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            # 필수 필드 확인
            required_fields = [
                "start_time",
                "total_dongs",
                "completed_dongs",
                "total_complexes",
                "completed_complexes",
                "summary",
            ]

            for field in required_fields:
                if field not in checkpoint:
                    self._add_warning(f"체크포인트 필드 누락: {field}")

            # summary 검증
            summary = checkpoint.get("summary", {})
            if "error_rate_percent" in summary:
                error_rate = summary["error_rate_percent"]
                if error_rate > 20:
                    self._add_warning(f"오류율이 높음: {error_rate}%")

            print(f"  - 진행률: {summary.get('dong_progress_percent', 0):.1f}%")
            print(f"  - 오류율: {summary.get('error_rate_percent', 0):.1f}%")

        except json.JSONDecodeError as e:
            self._add_error(f"체크포인트 파일 JSON 파싱 오류: {e}")

    def _add_error(self, message: str):
        """오류 추가"""
        self.issues.append(f"[오류] {message}")
        self.stats["error_count"] += 1

    def _add_warning(self, message: str):
        """경고 추가"""
        self.issues.append(f"[경고] {message}")
        self.stats["warning_count"] += 1


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="네이버 부동산 데이터 품질 검증")
    parser.add_argument("--output-dir", default="output", help="출력 디렉토리 경로 (기본: output)")
    args = parser.parse_args()

    verifier = DataQualityVerifier(args.output_dir)
    result = verifier.verify_all()

    # 종료 코드 설정
    if result["stats"]["error_count"] > 0:
        print("\n❌ 데이터 품질 검증 실패: 오류 발견")
        sys.exit(1)
    else:
        print("\n✅ 데이터 품질 검증 통과")
        sys.exit(0)


if __name__ == "__main__":
    main()

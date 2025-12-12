"""CSV writer for Hogangnono real estate data.

This module provides a simple HogangnonoCSVWriter that handles
both complexes and transactions CSV writing.
"""

import csv
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class HogangnonoCSVWriter:
    """호갱노노 데이터를 CSV로 저장하는 가장 단순한 Writer

    - complexes.csv: 단지 정보 저장
    - transactions.csv: 거래내역 저장
    """

    COMPLEXES_FIELDNAMES = [
        "complex_id",
        "complex_name",
        "real_estate_type",
        "address",
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
        "poi_type",
        "poi_category",
        "validation_result",
        "validation_reason",
        "data_source",
    ]

    TRANSACTIONS_FIELDNAMES = [
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

    def __init__(self, output_dir: str = "output") -> None:
        """초기화

        Args:
            output_dir: 출력 디렉토리 경로
        """
        self.output_dir = Path(output_dir)
        self.complexes_path = self.output_dir / "complexes.csv"
        self.transactions_path = self.output_dir / "transactions.csv"

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """단지 데이터를 complexes.csv로 저장

        Args:
            complexes_data: 단지 데이터 리스트
        """
        if not complexes_data:
            return

        transformed_data = []
        for data in complexes_data:
            transformed = self._transform_complex(data)
            transformed_data.append(transformed)

        self._append_to_csv(self.complexes_path, self.COMPLEXES_FIELDNAMES, transformed_data)
        logger.info(f"{len(transformed_data)}개 단지 데이터를 {self.complexes_path}에 저장")

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """거래내역 데이터를 transactions.csv로 저장

        Args:
            transactions_data: 거래내역 데이터 리스트
        """
        if not transactions_data:
            return

        transformed_data = []
        for data in transactions_data:
            transformed = self._transform_transaction(data)
            transformed_data.append(transformed)

        self._append_to_csv(self.transactions_path, self.TRANSACTIONS_FIELDNAMES, transformed_data)
        logger.info(f"{len(transformed_data)}개 거래 데이터를 {self.transactions_path}에 저장")

    def _append_to_csv(
        self, file_path: Path, fieldnames: List[str], data: List[Dict[str, Any]]
    ) -> None:
        """CSV 파일에 데이터 추가 (파일이 없으면 새로 생성)

        Args:
            file_path: 저장할 파일 경로
            fieldnames: CSV 필드명 리스트
            data: 저장할 데이터 리스트
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일이 존재하는지 확인
        file_exists = file_path.exists()

        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # 파일이 없으면 헤더 작성
            if not file_exists:
                writer.writeheader()

            # 데이터 작성
            if data:
                writer.writerows(data)

    def _transform_complex(self, complex_data: Dict[str, Any]) -> Dict[str, Any]:
        """단지 데이터를 CSV 형식으로 변환

        Args:
            complex_data: 원본 단지 데이터

        Returns:
            변환된 데이터
        """
        return {
            "complex_id": complex_data.get("aptSeq", ""),
            "complex_name": complex_data.get("aptName", ""),
            "real_estate_type": "아파트",
            "address": complex_data.get("address", ""),
            "completion_year_month": self._format_completion_date(complex_data.get("buildYear")),
            "total_dong_count": 1,
            "total_household_count": complex_data.get("householdCnt", ""),
            "min_area": 33.0,
            "max_area": 85.0,
            "deal_count": complex_data.get("dealCnt", ""),
            "lease_count": "",
            "rent_count": "",
            "pyeong_types": "33평, 59평",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "poi_type": "",
            "poi_category": "",
            "validation_result": "",
            "validation_reason": "",
            "data_source": "hogangnono",
        }

    def _transform_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """거래내역 데이터를 CSV 형식으로 변환

        Args:
            transaction_data: 원본 거래내역 데이터

        Returns:
            변환된 데이터
        """
        deal_type = transaction_data.get("dealType", "")
        if deal_type == "매매":
            trade_type, trade_type_name = "매매", "일반거래"
        elif deal_type == "전세":
            trade_type, trade_type_name = "전세", "일반거래"
        elif deal_type == "월세":
            trade_type, trade_type_name = "월세", "일반거래"
        else:
            trade_type, trade_type_name = "", "일반거래"

        deal_date = transaction_data.get("dealDate", "")
        if deal_date:
            deal_date = deal_date.replace(".", "-")
            try:
                date_obj = datetime.strptime(deal_date.split()[0], "%Y-%m-%d")
                trade_year = date_obj.year
            except (ValueError, IndexError):
                trade_year = datetime.now().year
        else:
            trade_year = datetime.now().year

        pyeong = transaction_data.get("pyeong", "")
        pyeong_type_number = int(pyeong) if pyeong and pyeong.isdigit() else 0

        return {
            "complex_id": transaction_data.get("aptSeq", ""),
            "complex_name": transaction_data.get("aptName", ""),
            "pyeong_type_number": pyeong_type_number,
            "pyeong_name": transaction_data.get("pyeongName", ""),
            "trade_type": trade_type,
            "trade_type_name": trade_type_name,
            "trade_date": deal_date,
            "trade_year": trade_year,
            "floor": self._parse_floor(transaction_data.get("floor", "")),
            "deal_price": self._parse_money(transaction_data.get("dealAmount", "")),
            "deposit": self._parse_money(transaction_data.get("deposit", "")),
            "monthly_rent": self._parse_money(transaction_data.get("monthlyRent", "")),
            "trade_category": "일반거래",
            "is_delete": False,
            "is_renew": False,
        }

    def _format_completion_date(self, build_year: Any) -> str:
        """준공일자 형식화

        Args:
            build_year: 건축년도

        Returns:
            형식화된 준공일자 (YYYYMMDD)
        """
        if build_year and str(build_year).isdigit() and len(str(build_year)) == 4:
            return f"{build_year}0101"
        return ""

    def _parse_floor(self, floor_str: str) -> int:
        """층수 파싱

        Args:
            floor_str: 층수 문자열

        Returns:
            층수 (정수)
        """
        if not floor_str:
            return 0

        if re.search(r"[bB지하]", floor_str):
            return 0

        numbers = re.findall(r"\d+", floor_str)
        if numbers:
            return int(numbers[0])
        return 0

    def _parse_money(self, amount_str: str) -> int:
        """금액 파싱

        Args:
            amount_str: 금액 문자열

        Returns:
            금액 (정수)
        """
        if not amount_str:
            return 0

        amount_str = amount_str.replace(",", "")
        numbers = re.findall(r"\d+", amount_str)
        if numbers:
            return int(numbers[0])
        return 0

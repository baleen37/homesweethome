"""CSV writer for Hogangnono transactions data.

This module provides HogangnonoTransactionsCSVWriter class that inherits from BaseCSVWriter
to handle transactions.csv file for Hogangnono data.
"""

import re
from typing import Any, Dict
from datetime import datetime

from crawler.writers.base_csv_writer import BaseCSVWriter


class HogangnonoTransactionsCSVWriter(BaseCSVWriter):
    """호갱노노 거래내역 데이터를 CSV로 저장하는 전용 클래스"""

    # 네이버 CSV 형식 필드명
    FIELDNAMES = [
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

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """거래내역 데이터를 네이버 형식으로 정규화"""
        # 거래 유형 매핑
        trade_type_mapping = {
            "매매": ("매매", "일반거래"),
            "전세": ("전세", "일반거래"),
            "월세": ("월세", "일반거래"),
        }

        # 거래 유형 파싱
        deal_type = row.get("dealType", "")
        trade_info = trade_type_mapping.get(deal_type, ("", "일반거래"))

        # 거래 날짜 파싱
        deal_date = row.get("dealDate", "")
        trade_year = datetime.now().year
        if deal_date:
            try:
                deal_date = deal_date.replace(".", "-")
                date_obj = datetime.strptime(deal_date.split()[0], "%Y-%m-%d")
                trade_year = date_obj.year
                deal_date = deal_date.split()[0]  # Keep YYYY-MM-DD format
            except (ValueError, IndexError):
                deal_date = ""

        # 평수 파싱
        pyeong = row.get("pyeong", "")
        pyeong_type_number = 0
        if pyeong and pyeong.isdigit():
            pyeong_type_number = int(pyeong)

        # 필드 매핑 및 정규화
        normalized_data = {
            "complex_id": str(row.get("aptSeq", "")),
            "complex_name": str(row.get("aptName", "")),
            "pyeong_type_number": str(pyeong_type_number),
            "pyeong_name": str(row.get("pyeongName", "")),
            "trade_type": trade_info[0],
            "trade_type_name": trade_info[1],
            "trade_date": deal_date,
            "trade_year": str(trade_year),
            "floor": str(self._parse_floor(row.get("floor", ""))),
            "deal_price": str(self._parse_money_amount(row.get("dealAmount", ""))),
            "deposit": str(self._parse_money_amount(row.get("deposit", ""))),
            "monthly_rent": str(self._parse_money_amount(row.get("monthlyRent", ""))),
            "trade_category": "일반거래",
            "is_delete": "false",
            "is_renew": "false",
        }

        # FIELDNAMES 순서로 필터링
        return {field: normalized_data.get(field, "") for field in self.FIELDNAMES}

    def _parse_floor(self, floor_str: str) -> int:
        """층수 문자열 파싱"""
        if not floor_str:
            return 0

        try:
            # B나 지하가 포함된 경우 0 반환
            if re.search(r"[bB지하]", floor_str):
                return 0
            numbers = re.findall(r"\d+", floor_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass

        return 0

    def _parse_money_amount(self, amount_str: str) -> int:
        """금액 문자열 파싱"""
        if not amount_str:
            return 0

        try:
            amount_str = amount_str.replace(",", "")
            numbers = re.findall(r"\d+", amount_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass

        return 0

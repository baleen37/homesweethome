"""CSV writer for Hogangnono real estate data.

This module provides HogangnonoCSVWriter class for saving Hogangnono API responses
to CSV files with proper field mapping to the expected CSV format.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict

from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter


class HogangnonoCSVWriter:
    """호갱노노 데이터를 CSV로 저장

    호갱노노 API 응답 데이터를 받아 CSV 파일로 저장합니다.
    - complexes.csv: 단지 정보 저장 (ComplexesCSVWriter 사용)
    - transactions.csv: 거래내역 저장 (TransactionCSVWriter 사용)
    """

    def __init__(self, output_dir: str = "output") -> None:
        """HogangnonoCSVWriter 초기화

        Args:
            output_dir: 출력 디렉토리 경로
        """
        self.output_dir = Path(output_dir)
        self.complexes_path = self.output_dir / "complexes.csv"
        self.transactions_path = self.output_dir / "transactions.csv"

        # 전용 CSV writer 인스턴스 생성
        self.complexes_writer = ComplexesCSVWriter(self.complexes_path)
        self.transactions_writer = TransactionCSVWriter(self.transactions_path)

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """단지 데이터를 complexes.csv로 저장

        Args:
            complexes_data: 호갱노노에서 가져온 단지 데이터 리스트 (POI 형식)
        """
        if not complexes_data:
            return

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # POI 데이터를 CSV 스키마에 맞게 변환
        transformed_data = self._transform_complexes_data(complexes_data)

        # ComplexesCSVWriter를 통해 저장
        self.complexes_writer.append(transformed_data)

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """거래내역 데이터를 transactions.csv로 저장

        Args:
            transactions_data: 호갱노노에서 가져온 거래내역 데이터 리스트
        """
        if not transactions_data:
            return

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 거래 데이터를 CSV 스키마에 맞게 변환
        transformed_data = self._transform_transactions_data(transactions_data)

        # TransactionCSVWriter를 통해 저장
        self.transactions_writer.append(transformed_data)

    def save_from_json_file(self, json_file_path: str, data_type: str = "complex") -> None:
        """JSON 파일에서 호갱노노 데이터를 읽어 CSV로 저장

        Args:
            json_file_path: JSON 파일 경로
            data_type: 저장할 데이터 타입 ("complex" 또는 "transaction")
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 단일 데이터가 아닌 리스트인지 확인
            if isinstance(data, dict) and "data" in data:
                data = data["data"]

            if isinstance(data, dict):
                data = [data]

            if data_type == "complex":
                self.save_complexes(data)
            elif data_type == "transaction":
                self.save_transactions(data)

        except FileNotFoundError:
            raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"JSON 파싱 오류: {json_file_path}")
        except Exception as e:
            raise RuntimeError(f"데이터 저장 중 오류 발생: {str(e)}")

    def _transform_complexes_data(
        self, complexes_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """POI 데이터를 complexes.csv 스키마에 맞게 변환

        Args:
            complexes_data: POI 형식의 단지 데이터

        Returns:
            CSV 스키마에 맞게 변환된 데이터
        """
        transformed = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in complexes_data:
            # completion_year_month 포맷팅 (YYYY-MM)
            approval_date = item.get("useApproveDate", "")
            completion_year_month = ""
            if approval_date and len(approval_date) >= 7:
                completion_year_month = approval_date[:7]

            # pyeong_types 목록 생성
            area_no_list = item.get("areaNoList", [])
            pyeong_types = ",".join(str(num) for num in area_no_list) if area_no_list else ""

            complex_data = {
                "complex_id": item.get("complexNo", ""),
                "complex_name": item.get("complexName", ""),
                "real_estate_type": str(item.get("realEstateType", 0)),
                "completion_year_month": completion_year_month,
                "total_dong_count": item.get("totalDongCount", 0),
                "total_household_count": item.get("totalHouseholdCount", 0),
                "min_area": item.get("minArea", 0.0),
                "max_area": item.get("maxArea", 0.0),
                "deal_count": item.get("dealCnt", 0),
                "lease_count": item.get("leaseCnt", 0),
                "rent_count": item.get("rentCnt", 0),
                "pyeong_types": pyeong_types,
                "fetched_at": current_time,
            }

            transformed.append(complex_data)

        return transformed

    def _transform_transactions_data(
        self, transactions_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """거래 데이터를 transactions.csv 스키마에 맞게 변환

        Args:
            transactions_data: 크롤러에서 수집한 거래 데이터

        Returns:
            CSV 스키마에 맞게 변환된 데이터
        """
        transformed = []

        for item in transactions_data:
            # 거래가격 파싱 (예: "11억 8,000" -> 118000)
            deal_price = item.get("deal_price", 0)
            price_str = item.get("price", "")  # Keep original price string for type detection

            if isinstance(deal_price, str):
                # If deal_price is already a string with price format
                price_str = deal_price
                deal_price = 0
                if price_str and "억" in price_str:
                    match = re.search(r"(\d+)억(?:\s*(\d+[,0-9]*)?)?", price_str)
                    if match:
                        eok = int(match.group(1))
                        man_str = match.group(2)
                        man = int(man_str.replace(",", "")) if man_str else 0
                        deal_price = eok * 10000 + man
            elif not isinstance(deal_price, (int, float)):
                # Fallback to parsing from price field
                deal_price = 0
                if price_str and "억" in price_str:
                    match = re.search(r"(\d+)억(?:\s*(\d+[,0-9]*)?)?", price_str)
                    if match:
                        eok = int(match.group(1))
                        man_str = match.group(2)
                        man = int(man_str.replace(",", "")) if man_str else 0
                        deal_price = eok * 10000 + man

            # 층수 파싱
            floor = 0
            floor_val = item.get("floor", 0)
            if isinstance(floor_val, str) and floor_val and "층" in floor_val:
                match = re.search(r"(\d+)", floor_val)
                if match:
                    floor = int(match.group(1))
            elif isinstance(floor_val, (int, float)):
                floor = int(floor_val)

            # 날짜 파싱 (예: "24.11.30" -> "2024-11-30")
            trade_date = ""
            trade_year = ""
            date_str = item.get("date", "")
            if date_str:
                parts = date_str.split(".")
                if len(parts) == 3:
                    year = "20" + parts[0]
                    month = parts[1].zfill(2)
                    day = parts[2].zfill(2)
                    trade_date = f"{year}-{month}-{day}"
                    trade_year = year

            # 면적 파싱
            area_str = item.get("area", "")
            pyeong_name = area_str.replace("㎡", "") if area_str else ""
            pyeong_type_number = 0
            if pyeong_name and pyeong_name.isdigit():
                pyeong_type_number = int(pyeong_name)

            # 전월세 구분
            trade_type = 0  # 기본값: 매매
            trade_type_name = "매매"
            if deal_price == 0 and "보증금" in price_str:
                trade_type = 1  # 전세
                trade_type_name = "전세"
            elif "월세" in price_str:
                trade_type = 2  # 월세
                trade_type_name = "월세"

            transaction_data = {
                "complex_id": item.get("apt_id", ""),
                "complex_name": item.get("complex_name", ""),
                "pyeong_type_number": pyeong_type_number,
                "pyeong_name": pyeong_name,
                "trade_type": trade_type,
                "trade_type_name": trade_type_name,
                "trade_date": trade_date,
                "trade_year": trade_year,
                "floor": floor,
                "deal_price": deal_price,
                "deposit": 0,  # 호갱노노에서는 보증금과 월세가 별도로 없음
                "monthly_rent": 0,
                "trade_category": "",
                "is_delete": False,
                "is_renew": False,
            }

            transformed.append(transaction_data)

        return transformed

    def get_stats(self) -> Dict[str, int]:
        """저장된 파일 통계 정보 반환

        Returns:
            파일 통계 정보
        """
        stats = {
            "complexes_file_size": 0,
            "transactions_file_size": 0,
            "complexes_record_count": 0,
            "transactions_record_count": 0,
        }

        try:
            if self.complexes_path.exists():
                stats["complexes_file_size"] = self.complexes_path.stat().st_size

                # 레코드 수 계산 (헤더 제외)
                with open(self.complexes_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        stats["complexes_record_count"] = len(lines) - 1

        except Exception:
            pass

        try:
            if self.transactions_path.exists():
                stats["transactions_file_size"] = self.transactions_path.stat().st_size

                # 레코드 수 계산 (헤더 제외)
                with open(self.transactions_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        stats["transactions_record_count"] = len(lines) - 1

        except Exception:
            pass

        return stats

"""CSV writer for Hogangnono real estate data.

This module provides a simplified HogangnonoCSVWriter that handles
both complexes and transactions CSV writing.
"""

import csv
import json
import re
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


class HogangnonoCSVWriter:
    """호갱노노 데이터를 네이버 형식 CSV로 변환 및 저장

    호갱노노 API 응답 데이터를 받아 네이버 CSV 형식으로 변환하여 저장합니다.
    - complexes.csv: 단지 정보 저장
    - transactions.csv: 거래내역 저장
    """

    # 네이버 CSV 형식 필드명
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
        """HogangnonoCSVWriter 초기화

        Args:
            output_dir: 출력 디렉토리 경로
        """
        self.output_dir = Path(output_dir)
        self.complexes_path = self.output_dir / "complexes.csv"
        self.transactions_path = self.output_dir / "transactions.csv"

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """단지 데이터를 complexes.csv로 저장

        Args:
            complexes_data: 호갱노노에서 가져온 단지 데이터 리스트
        """
        if not complexes_data:
            logger.info("save_complexes_skip", reason="empty_data")
            return

        # 변환된 데이터 준비
        transformed_data = []
        for data in complexes_data:
            transformed = self.transform_complex_to_naver_format(data)
            transformed_data.append(transformed)

        # CSV 파일에 저장 (파일이 있으면 추가, 없으면 새로 생성)
        if self.complexes_path.exists():
            # 기존 파일에 추가
            with open(self.complexes_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.COMPLEXES_FIELDNAMES)
                if transformed_data:
                    writer.writerows(transformed_data)
        else:
            # 새 파일 생성
            self._write_csv(self.complexes_path, self.COMPLEXES_FIELDNAMES, transformed_data)

        logger.info("complexes_saved", count=len(transformed_data), path=str(self.complexes_path))

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """거래내역 데이터를 transactions.csv로 저장

        Args:
            transactions_data: 호갱노노에서 가져온 거래내역 데이터 리스트
        """
        if not transactions_data:
            logger.info("save_transactions_skip", reason="empty_data")
            return

        # 변환된 데이터 준비
        transformed_data = []
        for data in transactions_data:
            transformed = self.transform_transaction_to_naver_format(data)
            transformed_data.append(transformed)

        # CSV 파일에 저장
        self._write_csv(self.transactions_path, self.TRANSACTIONS_FIELDNAMES, transformed_data)
        logger.info(
            "transactions_saved", count=len(transformed_data), path=str(self.transactions_path)
        )

    def _write_csv(
        self, file_path: Path, fieldnames: List[str], data: List[Dict[str, Any]]
    ) -> None:
        """CSV 파일 쓰기

        Args:
            file_path: 저장할 파일 경로
            fieldnames: CSV 필드명 리스트
            data: 저장할 데이터 리스트
        """
        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 쓰기
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            if data:
                writer.writerows(data)

    def transform_to_naver_format(
        self, hogangnono_data: Dict[str, Any], data_type: str = "complex"
    ) -> Dict[str, Any]:
        """호갱노노 데이터를 네이버 형식으로 변환

        Args:
            hogangnono_data: 호갱노노 API 응답 데이터
            data_type: 데이터 타입 ("complex" 또는 "transaction")

        Returns:
            변환된 네이버 형식 데이터
        """
        if data_type == "complex":
            return self.transform_complex_to_naver_format(hogangnono_data)
        elif data_type == "transaction":
            return self.transform_transaction_to_naver_format(hogangnono_data)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

    def transform_complex_to_naver_format(self, complex_data: Dict[str, Any]) -> Dict[str, Any]:
        """단지 데이터를 네이버 형식으로 변환

        Args:
            complex_data: 호갱노노 단지 데이터

        Returns:
            네이버 형식 단지 데이터
        """
        normalized = {}

        # 필드 매핑
        field_mapping = {
            "complex_id": "aptSeq",
            "complex_name": "aptName",
            "completion_year_month": lambda x: f"{x}0101"
            if x and x.isdigit() and len(x) == 4
            else "",
            "total_household_count": "householdCnt",
            "min_area": 33.0,  # 기본값
            "max_area": 85.0,  # 기본값
            "deal_count": "dealCnt",
            "lease_count": 0,  # 호갱노노에서 직접 제공하지 않음
            "rent_count": 0,  # 호갱노노에서 직접 제공하지 않음
        }

        # 기본값 설정
        default_values = {
            "real_estate_type": "아파트",
            "total_dong_count": 1,
            "pyeong_types": "33평, 59평",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "poi_type": "",
            "poi_category": "",
            "validation_result": "",
            "validation_reason": "",
            "data_source": "hogangnono",
        }

        # 필드 매핑 적용
        for naver_field, hogangnono_field in field_mapping.items():
            if callable(hogangnono_field):
                value = hogangnono_field(complex_data.get(naver_field))
            else:
                value = complex_data.get(hogangnono_field)

            # 타입 변환
            if value is None:
                value = ""
            else:
                value = str(value)

            normalized[naver_field] = value

        # 기본값 설정
        for field, default_value in default_values.items():
            if field not in normalized:
                normalized[field] = str(default_value)

        # completion_year_month 변환
        if not normalized.get("completion_year_month"):
            if complex_data.get("buildYear") and complex_data["buildYear"].isdigit():
                build_year = complex_data["buildYear"]
                normalized["completion_year_month"] = f"{build_year}0101"

        # CSV 스키마에 맞게 필터링
        result = {field: normalized.get(field) for field in self.COMPLEXES_FIELDNAMES}

        return result

    def transform_transaction_to_naver_format(
        self, transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """거래내역 데이터를 네이버 형식으로 변환

        Args:
            transaction_data: 호갱노노 거래내역 데이터

        Returns:
            네이버 형식 거래내역 데이터
        """
        # 거래 유형 매핑
        trade_type_mapping = {
            "매매": ("매매", "일반거래"),
            "전세": ("전세", "일반거래"),
            "월세": ("월세", "일반거래"),
        }

        # 거래 유형 파싱
        deal_type = transaction_data.get("dealType", "")
        trade_info = trade_type_mapping.get(deal_type, ("", "일반거래"))

        # 거래 날짜 파싱
        deal_date = transaction_data.get("dealDate", "")
        if deal_date:
            try:
                deal_date = deal_date.replace(".", "-")
                date_obj = datetime.strptime(deal_date.split()[0], "%Y-%m-%d")
                trade_year = date_obj.year
            except (ValueError, IndexError):
                trade_year = datetime.now().year
        else:
            trade_year = datetime.now().year

        # 평수 파싱
        pyeong = transaction_data.get("pyeong", "")
        pyeong_type_number = 0
        if pyeong and pyeong.isdigit():
            pyeong_type_number = int(pyeong)

        # 필드 매핑
        normalized = {
            "complex_id": transaction_data.get("aptSeq", ""),
            "complex_name": transaction_data.get("aptName", ""),
            "pyeong_type_number": pyeong_type_number,
            "pyeong_name": transaction_data.get("pyeongName", ""),
            "trade_type": trade_info[0],
            "trade_type_name": trade_info[1],
            "trade_date": deal_date,
            "trade_year": trade_year,
            "floor": self._parse_floor(transaction_data.get("floor", "")),
            "deal_price": self._parse_money_amount(transaction_data.get("dealAmount", "")),
            "deposit": self._parse_money_amount(transaction_data.get("deposit", "")),
            "monthly_rent": self._parse_money_amount(transaction_data.get("monthlyRent", "")),
            "trade_category": "일반거래",
            "is_delete": False,
            "is_renew": False,
        }

        # CSV 스키마에 맞게 필터링
        result = {field: normalized.get(field) for field in self.TRANSACTIONS_FIELDNAMES}

        return result

    def _parse_floor(self, floor_str: str) -> int:
        """층수 문자열 파싱

        Args:
            floor_str: 층수 문자열 (예: "5", "5/15", "B1")

        Returns:
            층수 (정수)
        """
        if not floor_str:
            return 0

        try:
            if re.search(r"[bB지하]", floor_str):
                return 0
            numbers = re.findall(r"\d+", floor_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass

        return 0

    def _parse_money_amount(self, amount_str: str) -> int:
        """금액 문자열 파싱

        Args:
            amount_str: 금액 문자열 (예: "45,000", "45억")

        Returns:
            금액 (만원 단위)
        """
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

    def save_from_json_file(self, json_file_path: str, data_type: str = "complex") -> None:
        """JSON 파일에서 호갱노노 데이터를 읽어 CSV로 저장

        Args:
            json_file_path: JSON 파일 경로
            data_type: 저장할 데이터 타입 ("complex" 또는 "transaction")
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

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

    def get_stats(self) -> Dict[str, int]:
        """저장된 파일 통계 정보 반환

        Returns:
            파일 통계 정보
        """
        stats = {}

        # complexes 파일 정보
        if self.complexes_path.exists():
            stats["complexes_file_size"] = self.complexes_path.stat().st_size
            with open(self.complexes_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                stats["complexes_record_count"] = max(0, len(lines) - 1)  # 헤더 제외
        else:
            stats["complexes_file_size"] = 0
            stats["complexes_record_count"] = 0

        # transactions 파일 정보
        if self.transactions_path.exists():
            stats["transactions_file_size"] = self.transactions_path.stat().st_size
            with open(self.transactions_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                stats["transactions_record_count"] = max(0, len(lines) - 1)  # 헤더 제외
        else:
            stats["transactions_file_size"] = 0
            stats["transactions_record_count"] = 0

        return stats

    def write_complexes_header(self) -> None:
        """complexes.csv에 헤더 작성"""
        self._write_csv(self.complexes_path, self.COMPLEXES_FIELDNAMES, [])

    def write_transactions_header(self) -> None:
        """transactions.csv에 헤더 작성"""
        self._write_csv(self.transactions_path, self.TRANSACTIONS_FIELDNAMES, [])

    async def write(self, data: List[Dict[str, Any]]) -> None:
        """비동기 write 래퍼 (ApartmentSearchCrawler 호환용)

        Args:
            data: 저장할 데이터 리스트
        """
        # complexes 데이터로 가정
        self.save_complexes(data)

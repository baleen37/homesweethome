"""CSV writer for Hogangnono real estate data.

This module provides HogangnonoCSVWriter as a compatibility wrapper
for the new unified writer architecture.
"""

import json
import re
from typing import Any, List, Dict
from datetime import datetime
import structlog

from crawler.writers.hogangnono_factory import HogangnonoCSVWriter as NewHogangnonoCSVWriter

logger = structlog.get_logger().bind(component="HogangnonoCSVWriter")


class HogangnonoCSVWriter:
    """호갱노노 데이터를 네이버 형식 CSV로 변환 및 저장

    호갱노노 API 응답 데이터를 받아 네이버 CSV 형식으로 변환하여 저장합니다.
    - complexes.csv: 단지 정보 저장
    - transactions.csv: 거래내역 저장

    This is a compatibility wrapper that delegates to the new implementation.
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
        # Delegate to the new implementation
        self._impl = NewHogangnonoCSVWriter(output_dir)

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """단지 데이터를 complexes.csv로 저장

        Args:
            complexes_data: 호갱노노에서 가져온 단지 데이터 리스트
        """
        self._impl.save_complexes(complexes_data)

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """거래내역 데이터를 transactions.csv로 저장

        Args:
            transactions_data: 호갱노노에서 가져온 거래내역 데이터 리스트
        """
        self._impl.save_transactions(transactions_data)

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
        return self._impl.transform_to_naver_format(hogangnono_data, data_type)

    def transform_complex_to_naver_format(self, complex_data: Dict[str, Any]) -> Dict[str, Any]:
        """단지 데이터를 네이버 형식으로 변환

        Args:
            complex_data: 호갱노노 단지 데이터

        Returns:
            네이버 형식 단지 데이터
        """
        # 호갱노노 데이터 구조 예시:
        # {
        #     "aptSeq": "아파트 ID",
        #     "aptName": "아파트명",
        #     "address": "주소",
        #     "buildYear": "건축년도",
        #     "dealCnt": "거래 건수",
        #     "realPrice": "실거래가",
        #     "realPriceYear": "실거래가 기준년도",
        #     "realPriceQuarter": "실거래가 기준분기",
        #     "recentDealPrice": "최근 거래가",
        #     "recentDealDate": "최근 거래일",
        #     "lng": "경도",
        #     "lat": "위도",
        #     "householdCnt": "세대수",
        #     "parkingCnt": "주차수"
        # }

        normalized = {}

        # 필드 매핑
        field_mapping = {
            "complex_id": "aptSeq",
            "complex_name": "aptName",
            "completion_year_month": lambda x: f"{x}0101"
            if x and x.isdigit() and len(x) == 4
            else "",
            "total_household_count": "householdCnt",
            "min_area": 33.0,  # 기본값 (전용면적 정보가 없음)
            "max_area": 85.0,  # 기본값 (전용면적 정보가 없음)
            "deal_count": "dealCnt",
            "lease_count": 0,  # 호갱노노에서 직접 제공하지 않음
            "rent_count": 0,  # 호갱노노에서 직접 제공하지 않음
        }

        # 기본값 설정
        default_values = {
            "real_estate_type": "아파트",
            "total_dong_count": 1,
            "pyeong_types": "33평, 59평",  # 추정치
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 필드 매핑 적용
        for naver_field, hogangnono_field in field_mapping.items():
            if callable(hogangnono_field):
                value = hogangnono_field(complex_data.get(naver_field))
            else:
                value = complex_data.get(hogangnono_field)

            # 타입 변환 - 모든 값을 문자열로 통일
            if value is None:
                value = ""
            else:
                value = str(value)

            normalized[naver_field] = value

        # 기본값 설정 (문자열로 변환)
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
        # 호갱노노 거래내역 데이터 구조는 일반적으로 다음과 같을 것으로 예상:
        # {
        #     "aptSeq": "아파트 ID",
        #     "aptName": "아파트명",
        #     "dong": "동",
        #     "ho": "호수",
        #     "pyeong": "평수",
        #     "pyeongName": "평수명",
        #     "floor": "층",
        #     "dealType": "거래 유형 (매매/전세/월세)",
        #     "dealAmount": "거래 금액 (만원)",
        #     "deposit": "보증금 (만원)",
        #     "monthlyRent": "월세 (만원)",
        #     "dealDate": "거래일",
        #     "area": "전용면적 (㎡)",
        #     "pyeongTypeNumber": "평수 번호"
        # }

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
                # YYYY-MM-DD 또는 YYYY.MM.DD 형식 가정
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
            floor_str: �수 문자열 (예: "5", "5/15", "B1")

        Returns:
            �수 (정수)
        """
        if not floor_str:
            return 0

        try:
            # 숫자만 추출 (음수는 허용하지 않음)
            # B나 지하가 포함된 경우 0 반환
            import re

            if re.search(r"[bB지하]", floor_str):
                return 0
            numbers = re.findall(r"\d+", floor_str)
            if numbers:
                # 첫 번째 숫자만 반환
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
            # 쉼표 제거
            amount_str = amount_str.replace(",", "")

            # 숫자만 추출
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

    def get_stats(self) -> Dict[str, int]:
        """저장된 파일 통계 정보 반환

        Returns:
            파일 통계 정보
        """
        return self._impl.get_stats()

    async def write(self, data: List[Dict[str, Any]]) -> None:
        """비동기 write 래퍼 (ApartmentSearchCrawler 호환용)

        Args:
            data: 저장할 데이터 리스트
        """
        await self._impl.write(data)

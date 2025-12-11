"""호갱노노 데이터 변환기

호갱노노 API 응답 데이터를 네이버 호갱노노 CSV 형식으로 변환합니다.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from structlog import stdlib

logger = stdlib.get_logger()


class HogangnonoDataMapper:
    """호갱노노 데이터를 네이버 형식으로 매핑

    호갱노노 API에서 받은 데이터를 네이버 CSV 저장 형식으로 변환합니다.
    - 단지 정보와 거래 정보를 모두 처리
    - 다양한 거래 유형 지원 (매매/전세/월세)
    - 주소에서 행정구역 정보 추출
    """

    def __init__(self, dong_code_mapping_file: Optional[Path] = None):
        """HogangnonoDataMapper 초기화

        Args:
            dong_code_mapping_file: 동 코드 매핑 파일 경로
        """
        self.logger = stdlib.get_logger().bind(component="HogangnonoDataMapper")

        # 동 코드 매핑 정보
        self.dong_code_mapping: Dict[str, Dict[str, Any]] = {}
        self.dong_code_mapping_file = dong_code_mapping_file

        if dong_code_mapping_file and dong_code_mapping_file.exists():
            self._load_dong_code_mapping()

    def _load_dong_code_mapping(self) -> None:
        """동 코드 매핑 정보 로드"""
        if not self.dong_code_mapping_file:
            return

        try:
            with open(self.dong_code_mapping_file, "r", encoding="utf-8") as f:
                self.dong_code_mapping = json.load(f)
            self.logger.info(
                "dong_code_mapping_loaded",
                file_path=str(self.dong_code_mapping_file),
                districts_count=len(self.dong_code_mapping),
            )
        except Exception as e:
            self.logger.error(
                "failed_to_load_dong_code_mapping",
                file_path=str(self.dong_code_mapping_file),
                error=str(e),
            )

    def update_dong_code_mapping(self, district_name: str, dong_mapping: Dict[str, str]) -> None:
        """동 코드 매핑 정보 업데이트

        Args:
            district_name: 구 이름
            dong_mapping: 동 이름-코드 매핑
        """
        if district_name not in self.dong_code_mapping:
            self.dong_code_mapping[district_name] = {}

        self.dong_code_mapping[district_name].update(dong_mapping)

        # 파일에 저장
        if self.dong_code_mapping_file:
            try:
                with open(self.dong_code_mapping_file, "w", encoding="utf-8") as f:
                    json.dump(self.dong_code_mapping, f, ensure_ascii=False, indent=2)
                self.logger.info(
                    "dong_code_mapping_saved",
                    district=district_name,
                    dongs_count=len(dong_mapping),
                )
            except Exception as e:
                self.logger.error(
                    "failed_to_save_dong_code_mapping",
                    error=str(e),
                )

    def get_dong_code(self, district_name: str, dong_name: str) -> Optional[str]:
        """동 이름으로 코드 조회

        Args:
            district_name: 구 이름
            dong_name: 동 이름

        Returns:
            동 코드 (있는 경우)
        """
        if district_name in self.dong_code_mapping:
            return self.dong_code_mapping[district_name].get(dong_name)
        return None

    def map_to_naver_format(
        self, item: Dict[str, Any], fetch_dong_code_func: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """호갱노노 데이터를 네이버 형식으로 매핑

        Args:
            item: 호갱노노 아파트/매물 데이터
            fetch_dong_code_func: 동 코드를 조회하기 위한 함수 (선택사항)

        Returns:
            네이버 CSV 형식으로 매핑된 데이터
        """
        try:
            # 기본 정보 매핑
            complex_id = str(item.get("id") or item.get("apt_id", ""))
            if not complex_id:
                return None

            complex_name = item.get("name", "") or item.get("apt_name", "")
            address = item.get("address", "") or item.get("full_address", "")

            # 위치 정보
            lat = item.get("lat") or item.get("latitude")
            lng = item.get("lng") or item.get("longitude")

            # 건물 기본 정보
            build_year = item.get("build_year") or item.get("completion_year")
            households = item.get("households") or item.get("household_count")
            floors = item.get("floors") or item.get("max_floor")

            # 거래 정보가 있는 경우
            trade_info = item.get("trade", {}) or item.get("recent_trade", {})

            # 거래 타입 결정
            trade_type = trade_info.get("type", "sale")
            if trade_type == "sale":
                trade_type_code = "A1"
                trade_type_name = "매매"
            elif trade_type == "jeonse":
                trade_type_code = "B1"
                trade_type_name = "전세"
            elif trade_type == "monthly":
                trade_type_code = "B2"
                trade_type_name = "월세"
            else:
                trade_type_code = "A1"
                trade_type_name = "매매"

            # 매물 상세 정보
            exclusive_area = trade_info.get("exclusive_area") or trade_info.get("area")
            if exclusive_area:
                # 평형으로 변환 (제곱미터 → 평)
                pyeong = float(exclusive_area) / 3.305785
                pyeong_type_number = round(pyeong)  # 올바른 반올림 적용
                pyeong_name = f"{pyeong_type_number}평형"
            else:
                pyeong_type_number = 0
                pyeong_name = ""

            floor = trade_info.get("floor") or trade_info.get("floor_info", "")
            deal_price = trade_info.get("price") or trade_info.get("deal_price", 0)
            deposit = trade_info.get("deposit") or trade_info.get("jeonse_price", 0)
            monthly_rent = trade_info.get("monthly") or trade_info.get("monthly_rent", 0)

            # 거래일
            trade_date = trade_info.get("date") or trade_info.get("trade_date", "")
            if trade_date and len(trade_date) >= 4:
                # 연도만 추출 (YYYY-MM-DD, YYYY.MM.DD, YYYYMM 등)
                year_str = trade_date[:4]
                if year_str.isdigit():
                    trade_year = int(year_str)
                else:
                    trade_year = 0
            else:
                trade_year = 0

            # 주소에서 구와 동 정보 추출
            gu_name, dong_name = self._parse_gu_dong_from_address(address)

            # 동 코드 조회
            dong_code = None
            gu_code = None
            if gu_name and dong_name:
                # 먼저 매핑된 정보에서 조회
                dong_code = self.get_dong_code(gu_name, dong_name)

                # 없고 fetch 함수가 제공된 경우 호출
                if not dong_code and fetch_dong_code_func:
                    dong_code = fetch_dong_code_func(gu_name, dong_name)

                    # 조회된 코드를 매핑에 추가
                    if dong_code:
                        self.update_dong_code_mapping(gu_name, {dong_name: dong_code})

                if dong_code:
                    # 구 코드는 동 코드의 앞 5자리
                    gu_code = dong_code[:5]

            # 결과 조합
            result = {
                # 단지 정보 (complexes.csv용)
                "complex_id": complex_id,
                "complex_name": complex_name,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "build_year": int(build_year) if build_year else 0,
                "households": int(households) if households else 0,
                "floors": int(floors) if floors else 0,
                # 거래 정보 (transactions.csv용)
                "pyeong_type_number": pyeong_type_number,
                "pyeong_name": pyeong_name,
                "trade_type": trade_type_code,
                "trade_type_name": trade_type_name,
                "trade_date": trade_date,
                "trade_year": trade_year,
                "floor": str(floor),
                "deal_price": int(str(deal_price).replace(",", "")) if deal_price else 0,
                "deposit": int(str(deposit).replace(",", "")) if deposit else 0,
                "monthly_rent": int(str(monthly_rent).replace(",", "")) if monthly_rent else 0,
                "trade_category": trade_type,
                "is_delete": "N",
                "is_renew": "N",
                # 추가: 행정구역 정보
                "gu_code": gu_code or "",
                "dong_code": dong_code or "",
                "gu_name": gu_name or "",
                "dong_name": dong_name or "",
            }

            return result

        except Exception as e:
            self.logger.error(
                "mapping_error",
                item=item,
                error=str(e),
            )
            return None

    def _parse_gu_dong_from_address(self, address: str) -> tuple[Optional[str], Optional[str]]:
        """주소에서 구와 동 이름 추출

        Args:
            address: 전체 주소

        Returns:
            (구 이름, 동 이름) 튜플
        """
        if not address:
            return None, None

        # 서울특별시가 아닌 경우
        if "서울특별시" not in address and not address.startswith("서울 "):
            return None, None

        # 주소 파싱
        parts = address.split()
        gu = None
        dong = None

        for i, part in enumerate(parts):
            # 구 찾기 (시가 아닌 구)
            if part.endswith("구") and "시" not in part:
                gu = part
                # 다음 파트가 동인지 확인
                if i + 1 < len(parts):
                    next_part = parts[i + 1]
                    # 번지가 포함된 동 처리 (예: 역삼동 825-24)
                    dong_part = next_part.split("-")[0]
                    if dong_part.endswith("동"):
                        dong = dong_part
                break

        return gu, dong

    def extract_complex_info(self, mapped_data: Dict[str, Any]) -> Dict[str, Any]:
        """매핑된 데이터에서 단지 정보만 추출

        Args:
            mapped_data: map_to_naver_format에서 변환된 데이터

        Returns:
            단지 정보
        """
        return {
            "complex_id": mapped_data["complex_id"],
            "complex_name": mapped_data["complex_name"],
            "address": mapped_data.get("address", ""),
            "latitude": mapped_data.get("latitude"),
            "longitude": mapped_data.get("longitude"),
            "build_year": mapped_data.get("build_year", 0),
            "households": mapped_data.get("households", 0),
            "floors": mapped_data.get("floors", 0),
            "gu_code": mapped_data.get("gu_code", ""),
            "dong_code": mapped_data.get("dong_code", ""),
            "gu_name": mapped_data.get("gu_name", ""),
            "dong_name": mapped_data.get("dong_name", ""),
        }

    def extract_transaction_info(self, mapped_data: Dict[str, Any]) -> Dict[str, Any]:
        """매핑된 데이터에서 거래 정보만 추출

        Args:
            mapped_data: map_to_naver_format에서 변환된 데이터

        Returns:
            거래 정보
        """
        return {
            "complex_id": mapped_data["complex_id"],
            "complex_name": mapped_data["complex_name"],
            "pyeong_type_number": mapped_data["pyeong_type_number"],
            "pyeong_name": mapped_data["pyeong_name"],
            "trade_type": mapped_data["trade_type"],
            "trade_type_name": mapped_data["trade_type_name"],
            "trade_date": mapped_data["trade_date"],
            "trade_year": mapped_data["trade_year"],
            "floor": mapped_data["floor"],
            "deal_price": mapped_data["deal_price"],
            "deposit": mapped_data["deposit"],
            "monthly_rent": mapped_data["monthly_rent"],
            "trade_category": mapped_data["trade_category"],
            "is_delete": mapped_data["is_delete"],
            "is_renew": mapped_data["is_renew"],
        }

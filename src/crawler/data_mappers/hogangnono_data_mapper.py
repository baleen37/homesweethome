"""호갱노노 데이터 변환기

호갱노노 API 응답 데이터를 네이버 호갱노노 CSV 형식으로 변환합니다.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import structlog
from ..models.api_responses import ComplexInfo, complex_info_from_api_response

logger = structlog.get_logger()

# 상수 정의
SQM_TO_PYEONG_RATIO = 3.305785


class TradeType:
    """거래 유형 상수"""

    SALE = "A1"
    SALE_NAME = "매매"
    JEONSE = "B1"
    JEONSE_NAME = "전세"
    MONTHLY = "B2"
    MONTHLY_NAME = "월세"


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
        self.logger = structlog.get_logger().bind(component="HogangnonoDataMapper")

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
        self,
        item: Dict[str, Any],
        fetch_dong_code_func: Optional[Callable[[str, str], Optional[str]]] = None,
    ) -> Optional[ComplexInfo]:
        """호갱노노 데이터를 ComplexInfo 객체로 매핑

        Args:
            item: 호갱노노 아파트/매물 데이터
            fetch_dong_code_func: 동 코드를 조회하기 위한 함수 (선택사항)

        Returns:
            ComplexInfo 객체로 매핑된 데이터, 실패 시 None
        """
        item_id = item.get("id", "unknown")
        item_name = item.get("name", "unknown")

        # Validate item is a valid apartment
        if not self._is_valid_apartment_data(item):
            self.logger.warning(
                "invalid_apartment_data_skipped",
                item_id=item_id,
                item_name=item_name,
                reason="Data does not appear to be a valid apartment",
            )
            return None

        # Convert to ComplexInfo for type safety
        try:
            complex_info = complex_info_from_api_response(item)

            # Validate complex_info was created successfully
            if not complex_info.id or not complex_info.name:
                self.logger.warning(
                    "invalid_complex_info_skipped",
                    item_id=item_id,
                    item_name=item_name,
                    complex_id=complex_info.id,
                    complex_name=complex_info.name,
                    reason="Missing required fields in ComplexInfo",
                )
                return None

            # 주소에서 구와 동 정보 추출
            try:
                gu_name, dong_name = self._parse_gu_dong_from_address(complex_info.address)
            except Exception as e:
                self.logger.warning(
                    "address_parsing_failed",
                    item_id=item_id,
                    item_name=item_name,
                    address=complex_info.address,
                    error=str(e),
                )
                gu_name, dong_name = None, None

            # 동 코드 조회
            dong_code = None
            gu_code = None
            if gu_name and dong_name:
                try:
                    # 먼저 매핑된 정보에서 조회
                    dong_code = self.get_dong_code(gu_name, dong_name)

                    # 없고 fetch 함수가 제공된 경우 호출
                    if not dong_code and fetch_dong_code_func:
                        self.logger.info(
                            "diagnostic_fetching_dong_code",
                            component="HogangnonoDataMapper",
                            gu_name=gu_name,
                            dong_name=dong_name,
                        )
                        dong_code = fetch_dong_code_func(gu_name, dong_name)

                        # 조회된 코드를 매핑에 추가
                        if dong_code:
                            self.update_dong_code_mapping(gu_name, {dong_name: dong_code})

                    if dong_code:
                        # 구 코드는 동 코드의 앞 5자리
                        gu_code = dong_code[:5]
                except Exception as e:
                    self.logger.warning(
                        "dong_code_fetching_failed",
                        item_id=item_id,
                        item_name=item_name,
                        gu_name=gu_name,
                        dong_name=dong_name,
                        error=str(e),
                    )
                    dong_code, gu_code = None, None

            # Create new ComplexInfo with administrative codes
            # ComplexInfo is immutable, so we need to create a new instance
            return ComplexInfo(
                id=complex_info.id,
                name=complex_info.name,
                address=complex_info.address,
                latitude=complex_info.latitude,
                longitude=complex_info.longitude,
                build_year=complex_info.build_year,
                households=complex_info.households,
                floors=complex_info.floors,
                elevator_count=complex_info.elevator_count,
                parking_count=complex_info.parking_count,
                heating_type=complex_info.heating_type,
                total_floor_area=complex_info.total_floor_area,
                total_site_area=complex_info.total_site_area,
                trade_info=complex_info.trade_info,
                gu_code=gu_code,
                dong_code=dong_code,
                gu_name=gu_name,
                dong_name=dong_name,
            )

        except Exception as e:
            self.logger.error(
                "mapping_error",
                item_id=item_id,
                item_name=item_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None

    def _parse_gu_dong_from_address(self, address: str) -> tuple[Optional[str], Optional[str]]:
        """주소에서 구와 동 이름 추출

        Args:
            address: 전체 주소

        Returns:
            (구 이름, 동 이름) 튜플
        """
        if not address or not isinstance(address, str):
            return None, None

        # Normalize address
        address = address.strip()
        if not address:
            return None, None

        # 서울특별시가 아닌 경우
        if "서울특별시" not in address and not address.startswith("서울 "):
            return None, None

        # 주소 파싱
        try:
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

            # Validate extracted gu and dong
            if gu and len(gu) < 2:  # Too short for a valid gu name
                gu = None
            if dong and len(dong) < 2:  # Too short for a valid dong name
                dong = None

            return gu, dong
        except Exception:
            # If parsing fails, return None values
            return None, None

    def _is_valid_apartment_data(self, item: Dict[str, Any]) -> bool:
        """Check if item represents valid apartment data

        Args:
            item: Raw data item

        Returns:
            True if item appears to be a valid apartment
        """
        if not isinstance(item, dict):
            return False

        # Check ID format
        item_id = str(item.get("id", ""))
        if not item_id:
            return False

        # Exclude known non-apartment patterns
        excluded_patterns = [
            "bi",  # Subway stations
            "1zg",  # Subway stations
            "bh",  # Subway stations
            "1H",  # Hospitals
            "1A",  # Marts
        ]

        for pattern in excluded_patterns:
            if item_id.startswith(pattern):
                return False

        # Must have some apartment-like characteristics
        has_name = bool(item.get("name"))
        has_coordinates = item.get("lat") is not None and item.get("lng") is not None
        has_households = item.get("households") is not None
        has_floors = item.get("floors") is not None
        has_address = bool(item.get("address"))

        # Check for obvious non-apartments
        name = item.get("name", "")
        description = item.get("description", "")

        if any(keyword in name for keyword in ["역", "병원", "마트", "점"]):
            return False
        if any(keyword in description for keyword in ["호선", "선", "역", "지하철", "종합병원"]):
            return False

        # Must have at least some apartment-like data
        apartment_indicators = [has_name, has_coordinates, has_households, has_floors, has_address]

        return sum(apartment_indicators) >= 3  # At least 3 indicators must be true

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

    def _complex_info_to_dict(self, complex_info: ComplexInfo) -> Dict[str, Any]:
        """Convert ComplexInfo back to dictionary for compatibility

        Args:
            complex_info: ComplexInfo object

        Returns:
            Dictionary representation
        """
        # 거래 정보 처리
        pyeong_type_number = 0
        pyeong_name = ""
        trade_type_code = TradeType.SALE
        trade_type_name = TradeType.SALE_NAME
        trade_date = ""
        floor = ""
        deal_price = 0
        deposit = 0
        monthly_rent = 0
        trade_category = "sale"

        if complex_info.trade_info:
            trade_type = complex_info.trade_info.trade_type
            if trade_type == "sale":
                trade_type_code = TradeType.SALE
                trade_type_name = TradeType.SALE_NAME
            elif trade_type == "jeonse":
                trade_type_code = TradeType.JEONSE
                trade_type_name = TradeType.JEONSE_NAME
            elif trade_type == "monthly":
                trade_type_code = TradeType.MONTHLY
                trade_type_name = TradeType.MONTHLY_NAME

            if complex_info.trade_info.exclusive_area:
                pyeong = complex_info.trade_info.exclusive_area / SQM_TO_PYEONG_RATIO
                pyeong_type_number = round(pyeong)
                pyeong_name = f"{pyeong_type_number}평형"

            trade_date = complex_info.trade_info.trade_date or ""
            floor = complex_info.trade_info.floor or ""
            deal_price = complex_info.trade_info.price or 0
            deposit = complex_info.trade_info.deposit or 0
            monthly_rent = complex_info.trade_info.monthly_rent or 0
            trade_category = trade_type

        return {
            # 단지 정보 (complexes.csv용)
            "complex_id": complex_info.id,
            "complex_name": complex_info.name,
            "address": complex_info.address,
            "latitude": complex_info.latitude,
            "longitude": complex_info.longitude,
            "build_year": complex_info.build_year or 0,
            "households": complex_info.households or 0,
            "floors": complex_info.floors or 0,
            # 거래 정보 (transactions.csv용)
            "pyeong_type_number": pyeong_type_number,
            "pyeong_name": pyeong_name,
            "trade_type": trade_type_code,
            "trade_type_name": trade_type_name,
            "trade_date": trade_date,
            "trade_year": complex_info.trade_info.trade_year if complex_info.trade_info else 0,
            "floor": floor,
            "deal_price": deal_price,
            "deposit": deposit,
            "monthly_rent": monthly_rent,
            "trade_category": trade_category,
            "is_delete": "N",
            "is_renew": "N",
            # 추가: 행정구역 정보
            "gu_code": complex_info.gu_code or "",
            "dong_code": complex_info.dong_code or "",
            "gu_name": complex_info.gu_name or "",
            "dong_name": complex_info.dong_name or "",
        }

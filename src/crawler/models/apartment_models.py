"""데이터 모델을 위한 data class 정의

타입 안전성을 보장하고 데이터 일관성을 유지하기 위한 data class들
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RealEstateType(Enum):
    """부동산 유형"""

    APARTMENT = "아파트"
    MIXED_USE = "주상복합"
    OFFICETEL = "오피스텔"
    UNKNOWN = "알 수 없음"


class POICategory(Enum):
    """POI 카테고리"""

    SUBWAY = "지하철역"
    HOSPITAL = "병원"
    MART = "마트"
    APARTMENT = "아파트"
    SCHOOL = "학교"
    ETC = "기타"


@dataclass(frozen=True)
class BoundingBox:
    """지역 bounding box"""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.max_x, self.min_y, self.max_y)


@dataclass
class Apartment:
    """아파트 정보를 담는 data class"""

    complex_id: str
    complex_name: str
    real_estate_type: RealEstateType
    completion_year_month: Optional[str] = None
    total_dong_count: Optional[int] = None
    total_household_count: Optional[int] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    deal_count: int = 0
    lease_count: int = 0
    rent_count: int = 0
    pyeong_types: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def is_valid_apartment(self) -> bool:
        """유효한 아파트인지 검증"""
        # 최소 필수 조건 확인
        if not self.complex_id or not self.complex_name:
            return False

        # 아파트 ID 형식 확인 (APT_ 접두사)
        if not self.complex_id.startswith("APT_"):
            return False

        # 아파트 특유 필드 존재 여부 확인
        if self.total_household_count is None or self.total_household_count <= 0:
            return False

        return True

    def to_csv_row(self) -> Dict[str, Any]:
        """CSV 출력용 데이터로 변환"""
        return {
            "complex_id": self.complex_id,
            "complex_name": self.complex_name,
            "real_estate_type": self.real_estate_type.value,
            "completion_year_month": self.completion_year_month or "",
            "total_dong_count": self.total_dong_count or 0,
            "total_household_count": self.total_household_count or 0,
            "min_area": self.min_area or 0.0,
            "max_area": self.max_area or 0.0,
            "deal_count": self.deal_count,
            "lease_count": self.lease_count,
            "rent_count": self.rent_count,
            "pyeong_types": self.pyeong_types or "",
            "address": self.address or "",
            "latitude": self.coordinates[0] if self.coordinates else None,
            "longitude": self.coordinates[1] if self.coordinates else None,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class POI:
    """POI(Point of Interest) 정보를 담는 data class"""

    id: str
    name: str
    category: POICategory
    coordinates: tuple[float, float]
    address: Optional[str] = None

    def is_apartment(self) -> bool:
        """아파트 POI인지 확인"""
        return self.category == POICategory.APARTMENT and self.id.startswith("APT_")


@dataclass
class ApartmentFilter:
    """아파트 데이터 필터링 기준"""

    min_household_count: int = 1
    max_household_count: Optional[int] = None
    allowed_real_estate_types: List[RealEstateType] = field(
        default_factory=lambda: [RealEstateType.APARTMENT, RealEstateType.MIXED_USE]
    )

    def is_valid(self, apartment: Apartment) -> bool:
        """아파트가 필터 조건에 맞는지 확인"""
        # 최소 세대 수 확인
        if (
            apartment.total_household_count
            and apartment.total_household_count < self.min_household_count
        ):
            return False

        # 최대 세대 수 확인
        if (
            self.max_household_count
            and apartment.total_household_count
            and apartment.total_household_count > self.max_household_count
        ):
            return False

        # 부동산 유형 확인
        if apartment.real_estate_type not in self.allowed_real_estate_types:
            return False

        return True


@dataclass
class CrawlStats:
    """크롤링 통계 정보"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    apartments_found: int = 0
    apartments_processed: int = 0
    pois_filtered: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def apartment_processing_rate(self) -> float:
        """아파트 처리율 계산"""
        if self.apartments_found == 0:
            return 0.0
        return self.apartments_processed / self.apartments_found

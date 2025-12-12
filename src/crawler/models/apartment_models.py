"""데이터 모델을 위한 data class 정의

타입 안전성을 보장하고 데이터 일관성을 유지하기 위한 data class들
"""

from dataclasses import dataclass, field, asdict
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
class PoiData:
    """Represents POI data from API response."""

    # Required fields from POI API
    poi_id: str
    name: str
    lat: float
    lng: float
    category: int

    # Optional fields
    description: Optional[str] = None
    address: Optional[str] = None
    dong: Optional[str] = None  # This is the field we need to extract!

    def __post_init__(self):
        """Validate data after initialization."""
        # Validate required fields
        if not self.poi_id or not isinstance(self.poi_id, str):
            raise ValueError("poi_id is required and must be a string")

        if not self.name or not isinstance(self.name, str):
            raise ValueError("name is required and must be a string")

        # Validate coordinates
        if not isinstance(self.lat, (int, float)):
            raise ValueError("lat must be a number")
        if not isinstance(self.lng, (int, float)):
            raise ValueError("lng must be a number")

        # Validate latitude range (-90 to 90)
        if not -90 <= self.lat <= 90:
            raise ValueError(f"lat must be between -90 and 90, got {self.lat}")

        # Validate longitude range (-180 to 180)
        if not -180 <= self.lng <= 180:
            raise ValueError(f"lng must be between -180 and 180, got {self.lng}")

        # Validate category
        if not isinstance(self.category, int):
            raise ValueError("category must be an integer")
        if self.category < 0:
            raise ValueError(f"category must be non-negative, got {self.category}")

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "PoiData":
        """Create PoiData from API response dictionary."""
        return cls(
            poi_id=response.get("id", ""),
            name=response.get("name", ""),
            lat=float(response.get("lat", 0.0)),
            lng=float(response.get("lng", 0.0)),
            category=int(response.get("category", 0)),
            description=response.get("description"),
            address=response.get("address"),
            dong=response.get("dong"),  # Extract the dong field!
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing."""
        return asdict(self)


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


@dataclass
class ApartmentComplex:
    """Represents an apartment complex with full details."""

    # Basic info
    complex_id: str
    complex_name: str
    real_estate_type: str = "아파트"

    # Location info
    address: Optional[str] = None
    dong_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    # Building details
    completion_year_month: Optional[str] = None
    total_dong_count: Optional[int] = None
    total_household_count: Optional[int] = None

    # Area info
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    pyeong_types: Optional[str] = None

    # Transaction counts
    deal_count: int = 0
    lease_count: int = 0
    rent_count: int = 0

    # Metadata
    fetched_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def __post_init__(self):
        """Validate data after initialization."""
        # Validate required fields
        if not self.complex_id or not isinstance(self.complex_id, str):
            raise ValueError("complex_id is required and must be a string")

        if not self.complex_name or not isinstance(self.complex_name, str):
            raise ValueError("complex_name is required and must be a string")

        if not isinstance(self.real_estate_type, str):
            raise ValueError("real_estate_type must be a string")

        # Validate coordinates if provided
        if self.lat is not None:
            if not isinstance(self.lat, (int, float)):
                raise ValueError("lat must be a number if provided")
            if not -90 <= self.lat <= 90:
                raise ValueError(f"lat must be between -90 and 90, got {self.lat}")

        if self.lng is not None:
            if not isinstance(self.lng, (int, float)):
                raise ValueError("lng must be a number if provided")
            if not -180 <= self.lng <= 180:
                raise ValueError(f"lng must be between -180 and 180, got {self.lng}")

        # Validate counts
        if not isinstance(self.deal_count, int) or self.deal_count < 0:
            raise ValueError(f"deal_count must be a non-negative integer, got {self.deal_count}")

        if not isinstance(self.lease_count, int) or self.lease_count < 0:
            raise ValueError(f"lease_count must be a non-negative integer, got {self.lease_count}")

        if not isinstance(self.rent_count, int) or self.rent_count < 0:
            raise ValueError(f"rent_count must be a non-negative integer, got {self.rent_count}")

        # Validate optional integer fields
        if self.total_dong_count is not None:
            if not isinstance(self.total_dong_count, int) or self.total_dong_count <= 0:
                raise ValueError(
                    f"total_dong_count must be a positive integer if provided, got {self.total_dong_count}"
                )

        if self.total_household_count is not None:
            if not isinstance(self.total_household_count, int) or self.total_household_count <= 0:
                raise ValueError(
                    f"total_household_count must be a positive integer if provided, got {self.total_household_count}"
                )

        # Validate area fields
        if self.min_area is not None:
            if not isinstance(self.min_area, (int, float)) or self.min_area <= 0:
                raise ValueError(
                    f"min_area must be a positive number if provided, got {self.min_area}"
                )

        if self.max_area is not None:
            if not isinstance(self.max_area, (int, float)) or self.max_area <= 0:
                raise ValueError(
                    f"max_area must be a positive number if provided, got {self.max_area}"
                )

        # Validate min/max area consistency
        if self.min_area is not None and self.max_area is not None:
            if self.min_area > self.max_area:
                raise ValueError(
                    f"min_area ({self.min_area}) cannot be greater than max_area ({self.max_area})"
                )

    @classmethod
    def from_poi_data(cls, poi: PoiData) -> "ApartmentComplex":
        """Create ApartmentComplex from PoiData."""
        # Extract dong name from POI data if available
        dong_name = poi.dong

        # Try to extract dong from address if not directly available
        if not dong_name and poi.address:
            # Simple parsing for "서울특별시 구 동" format
            address_parts = poi.address.split()
            if len(address_parts) >= 3:
                dong_name = address_parts[-1]

        return cls(
            complex_id=poi.poi_id,
            complex_name=poi.name,
            real_estate_type=poi.description or "아파트",
            address=poi.address,
            dong_name=dong_name,
            lat=poi.lat,
            lng=poi.lng,
        )

    @classmethod
    def from_complex_api_response(cls, response: Dict[str, Any]) -> "ApartmentComplex":
        """Create ApartmentComplex from complex API response."""
        complex_data = response.get("complex", response)

        # Extract dong from cortarName if available
        cortar_name = complex_data.get("cortarName", "")
        dong_name = None
        if cortar_name:
            # Extract from "구 동" format
            parts = cortar_name.split()
            if len(parts) >= 2:
                dong_name = parts[-1]

        return cls(
            complex_id=f"APT_{complex_data.get('no', '')}",
            complex_name=complex_data.get("name", ""),
            dong_name=dong_name,
            address=cortar_name,
            completion_year_month=complex_data.get("buildYear"),
            lat=float(complex_data.get("lat", 0.0)) if complex_data.get("lat") else None,
            lng=float(complex_data.get("lng", 0.0)) if complex_data.get("lng") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing."""
        return asdict(self)

    def merge_with_details(self, details: Dict[str, Any]) -> None:
        """Merge with additional details from another API call."""
        if "completionYear" in details:
            self.completion_year_month = details["completionYear"]
        if "households" in details:
            self.total_household_count = int(details["households"])
        if "buildings" in details:
            self.total_dong_count = len(details["buildings"])
        # Add more fields as needed

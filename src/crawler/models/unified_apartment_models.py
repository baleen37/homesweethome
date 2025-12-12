"""Unified apartment and POI models to eliminate code duplication."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
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


@dataclass
class UnifiedPOI:
    """통합 POI 모델 - PoiData와 POI의 기능을 모두 포함"""

    # Common fields
    id: str
    name: str
    coordinates: Tuple[float, float]  # (lat, lng)
    category: Union[int, POICategory]

    # Optional fields
    description: Optional[str] = None
    address: Optional[str] = None
    dong: Optional[str] = None

    # POI-specific fields from apartment_models
    category_enum: Optional[POICategory] = None

    # Additional fields for apartments
    build_date: Optional[str] = None
    households: Optional[int] = None
    floors: Optional[int] = None

    # Metadata
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 데이터 검증 및 변환"""
        # Validate coordinates
        if not isinstance(self.coordinates, tuple) or len(self.coordinates) != 2:
            raise ValueError("coordinates must be a tuple of (lat, lng)")

        lat, lng = self.coordinates
        if not -90 <= lat <= 90:
            raise ValueError(f"latitude must be between -90 and 90, got {lat}")
        if not -180 <= lng <= 180:
            raise ValueError(f"longitude must be between -180 and 180, got {lng}")

        # Convert category to enum if needed
        if isinstance(self.category, int) and self.category_enum is None:
            self.category_enum = self._int_to_category_enum(self.category)

    def _int_to_category_enum(self, category_int: int) -> POICategory:
        """정수 카테고리를 enum으로 변환"""
        category_mapping = {
            1: POICategory.APARTMENT,
            2: POICategory.SUBWAY,
            3: POICategory.HOSPITAL,
            4: POICategory.MART,
            5: POICategory.SCHOOL,
        }
        return category_mapping.get(category_int, POICategory.ETC)

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "UnifiedPOI":
        """API 응답에서 UnifiedPOI 생성"""
        # Handle both "id" and "poi_id" field names
        poi_id = response.get("id", response.get("poi_id", ""))

        # Handle coordinates
        lat = float(response.get("lat", 0.0))
        lng = float(response.get("lng", 0.0))

        # Handle category
        category = response.get("category", 0)

        return cls(
            id=poi_id,
            name=response.get("name", ""),
            coordinates=(lat, lng),
            category=category,
            description=response.get("description"),
            address=response.get("address"),
            dong=response.get("dong"),
            build_date=response.get("buildYear"),
            households=int(response.get("households", 0)) if response.get("households") else None,
            floors=int(response.get("floors", 0)) if response.get("floors") else None,
        )

    @classmethod
    def from_poi_data(cls, poi_data) -> "UnifiedPOI":
        """기존 PoiData 객체에서 변환"""
        return cls(
            id=poi_data.poi_id,
            name=poi_data.name,
            coordinates=(poi_data.lat, poi_data.lng),
            category=poi_data.category,
            description=poi_data.description,
            address=poi_data.address,
            dong=poi_data.dong,
        )

    @classmethod
    def from_poi(cls, poi) -> "UnifiedPOI":
        """기존 POI 객체에서 변환"""
        return cls(
            id=poi.id,
            name=poi.name,
            coordinates=poi.coordinates,
            category=poi.category,
            address=poi.address,
            category_enum=poi.category,
        )

    def is_apartment(self) -> bool:
        """아파트 POI인지 확인"""
        # Check multiple ways this could be an apartment
        if self.category_enum and self.category_enum == POICategory.APARTMENT:
            return True
        if isinstance(self.category, int) and self.category == 1:
            return True
        if self.id.startswith("APT_"):
            return True
        if self.description and "아파트" in self.description:
            return True
        return False

    def validate_for_apartment_crawling(self) -> bool:
        """아파트 크롤링을 위한 검증"""
        return self.is_apartment() and bool(self.id) and bool(self.name)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        # Convert coordinates back to separate fields for compatibility
        result["lat"] = self.coordinates[0]
        result["lng"] = self.coordinates[1]
        return result


@dataclass
class UnifiedApartment:
    """통합 아파트 모델 - ApartmentComplex와 Apartment의 기능을 모두 포함"""

    # Basic info
    complex_id: str
    complex_name: str
    real_estate_type: Union[str, RealEstateType] = "아파트"

    # Location info
    address: Optional[str] = None
    dong_name: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None

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
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 데이터 검증 및 변환"""
        # Convert enum to string if needed
        if isinstance(self.real_estate_type, RealEstateType):
            self.real_estate_type = self.real_estate_type.value

        # Validate required fields
        if not self.complex_id or not isinstance(self.complex_id, str):
            raise ValueError("complex_id is required and must be a string")

        if not self.complex_name or not isinstance(self.complex_name, str):
            raise ValueError("complex_name is required and must be a string")

        # Validate counts
        if not isinstance(self.deal_count, int) or self.deal_count < 0:
            raise ValueError(f"deal_count must be a non-negative integer, got {self.deal_count}")

        # Validate area consistency
        if self.min_area is not None and self.max_area is not None:
            if self.min_area > self.max_area:
                raise ValueError(
                    f"min_area ({self.min_area}) cannot be greater than max_area ({self.max_area})"
                )

    @classmethod
    def from_poi(cls, poi: UnifiedPOI) -> "UnifiedApartment":
        """UnifiedPOI에서 UnifiedApartment 생성"""
        # Extract dong name from POI data if available
        dong_name = poi.dong

        # Try to extract dong from address if not directly available
        if not dong_name and poi.address:
            # Simple parsing for "서울특별시 구 동" format
            address_parts = poi.address.split()
            if len(address_parts) >= 3:
                dong_name = address_parts[-1]

        # Determine real estate type from description
        real_estate_type = "아파트"
        if poi.description:
            if "주상복합" in poi.description:
                real_estate_type = "주상복합"
            elif "오피스텔" in poi.description:
                real_estate_type = "오피스텔"

        return cls(
            complex_id=poi.id,
            complex_name=poi.name,
            real_estate_type=real_estate_type,
            address=poi.address,
            dong_name=dong_name,
            coordinates=poi.coordinates,
            completion_year_month=poi.build_date,
            total_household_count=poi.households,
        )

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "UnifiedApartment":
        """API 응답에서 UnifiedApartment 생성"""
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
            coordinates=(
                float(complex_data.get("lat", 0.0)) if complex_data.get("lat") else None,
                float(complex_data.get("lng", 0.0)) if complex_data.get("lng") else None,
            ),
        )

    @classmethod
    def from_apartment_complex(cls, apt_complex) -> "UnifiedApartment":
        """기존 ApartmentComplex에서 변환"""
        return cls(
            complex_id=apt_complex.complex_id,
            complex_name=apt_complex.complex_name,
            real_estate_type=apt_complex.real_estate_type,
            address=apt_complex.address,
            dong_name=apt_complex.dong_name,
            coordinates=(apt_complex.lat, apt_complex.lng)
            if apt_complex.lat and apt_complex.lng
            else None,
            completion_year_month=apt_complex.completion_year_month,
            total_dong_count=apt_complex.total_dong_count,
            total_household_count=apt_complex.total_household_count,
            min_area=apt_complex.min_area,
            max_area=apt_complex.max_area,
            pyeong_types=apt_complex.pyeong_types,
            deal_count=apt_complex.deal_count,
            lease_count=apt_complex.lease_count,
            rent_count=apt_complex.rent_count,
        )

    @classmethod
    def from_apartment(cls, apartment) -> "UnifiedApartment":
        """기존 Apartment에서 변환"""
        return cls(
            complex_id=apartment.complex_id,
            complex_name=apartment.complex_name,
            real_estate_type=apartment.real_estate_type.value
            if hasattr(apartment.real_estate_type, "value")
            else apartment.real_estate_type,
            address=apartment.address,
            dong_name=apartment.dong_name,
            coordinates=apartment.coordinates,
            completion_year_month=apartment.completion_year_month,
            total_dong_count=apartment.total_dong_count,
            total_household_count=apartment.total_household_count,
            min_area=apartment.min_area,
            max_area=apartment.max_area,
            pyeong_types=apartment.pyeong_types,
            deal_count=apartment.deal_count,
            lease_count=apartment.lease_count,
            rent_count=apartment.rent_count,
        )

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
        result = {
            "complex_id": self.complex_id,
            "complex_name": self.complex_name,
            "real_estate_type": self.real_estate_type,
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
            "fetched_at": self.fetched_at.isoformat(),
        }

        # Add coordinates if available
        if self.coordinates:
            result["latitude"] = self.coordinates[0]
            result["longitude"] = self.coordinates[1]
        else:
            result["latitude"] = None
            result["longitude"] = None

        return result

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    def merge_with_details(self, details: Dict[str, Any]) -> None:
        """추가 정보와 병합"""
        if "completionYear" in details:
            self.completion_year_month = details["completionYear"]
        if "households" in details:
            self.total_household_count = int(details["households"])
        if "buildings" in details:
            self.total_dong_count = len(details["buildings"])


@dataclass
class ApartmentFilter:
    """아파트 데이터 필터링 기준"""

    min_household_count: int = 1
    max_household_count: Optional[int] = None
    allowed_real_estate_types: List[RealEstateType] = field(
        default_factory=lambda: [RealEstateType.APARTMENT, RealEstateType.MIXED_USE]
    )

    def is_valid(self, apartment: UnifiedApartment) -> bool:
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
        apartment_type = RealEstateType(apartment.real_estate_type)
        if apartment_type not in self.allowed_real_estate_types:
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


@dataclass(frozen=True)
class BoundingBox:
    """지역 bounding box"""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.max_x, self.min_y, self.max_y)

"""Type-safe data classes for API responses

These data classes provide type safety and validation for API responses,
preventing common errors like typos in field names and type mismatches.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .validators import validate_coordinates, validate_price, validate_area, validate_year


class POICategory(Enum):
    """POI category classification based on API response"""

    SUBWAY_STATION = 1
    HOSPITAL = 9
    MART = 10
    TRAIN_STATION = 11
    APARTMENT = 100  # Assumed category for apartments

    @classmethod
    def from_value(cls, value: Optional[int]) -> "POICategory":
        """Create POICategory from raw category value"""
        if value is None:
            return cls.APARTMENT  # Default to apartment for safety

        try:
            return cls(value)
        except ValueError:
            # Unknown category, default to apartment for safety
            return cls.APARTMENT

    def is_apartment(self) -> bool:
        """Check if this category represents an apartment"""
        return self == POICategory.APARTMENT

    def is_transit(self) -> bool:
        """Check if this category represents public transit"""
        return self in {POICategory.SUBWAY_STATION, POICategory.TRAIN_STATION}

    def is_facility(self) -> bool:
        """Check if this category represents a public facility"""
        return self in {POICategory.HOSPITAL, POICategory.MART}


@dataclass(frozen=True)
class APIResponse:
    """Generic API response wrapper"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


@dataclass(frozen=True)
class TradeInfo:
    """Trade/pricing information for a property"""

    trade_type: str  # "sale", "jeonse", "monthly"
    price: Optional[int] = None
    deposit: Optional[int] = None
    monthly_rent: Optional[int] = None
    exclusive_area: Optional[float] = None
    floor: Optional[str] = None
    trade_date: Optional[str] = None
    trade_year: Optional[int] = None

    def __post_init__(self):
        """Validate trade information after initialization"""
        if self.price is not None:
            object.__setattr__(self, "price", validate_price(self.price))
        if self.deposit is not None:
            object.__setattr__(self, "deposit", validate_price(self.deposit))
        if self.monthly_rent is not None:
            object.__setattr__(self, "monthly_rent", validate_price(self.monthly_rent))
        if self.exclusive_area is not None:
            object.__setattr__(self, "exclusive_area", validate_area(self.exclusive_area))
        if self.trade_year is not None:
            object.__setattr__(self, "trade_year", validate_year(self.trade_year))


@dataclass(frozen=True)
class ComplexInfo:
    """Complex/apartment building information"""

    id: Union[str, int]
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    build_year: Optional[int] = None
    households: Optional[int] = None
    floors: Optional[int] = None
    elevator_count: Optional[int] = None
    parking_count: Optional[int] = None
    heating_type: Optional[str] = None
    total_floor_area: Optional[float] = None
    total_site_area: Optional[float] = None
    trade_info: Optional[TradeInfo] = None
    gu_code: Optional[str] = None
    dong_code: Optional[str] = None
    gu_name: Optional[str] = None
    dong_name: Optional[str] = None

    def __post_init__(self):
        """Validate complex information after initialization"""
        # Ensure ID is always a string for consistency
        id_str = str(self.id)
        object.__setattr__(self, "id", id_str)

        if self.latitude is not None or self.longitude is not None:
            validated_lat, validated_lng = validate_coordinates(self.latitude, self.longitude)
            object.__setattr__(self, "latitude", validated_lat)
            object.__setattr__(self, "longitude", validated_lng)

        if self.build_year is not None:
            object.__setattr__(self, "build_year", validate_year(self.build_year))

        if self.households is not None:
            object.__setattr__(self, "households", int(self.households))

        if self.floors is not None:
            object.__setattr__(self, "floors", int(self.floors))


@dataclass(frozen=True)
class POIInfo:
    """Point of Interest information from bounding box API"""

    id: Union[str, int]
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    type: Optional[str] = None
    category: Optional[int] = None
    region1: Optional[str] = None
    region2: Optional[str] = None
    region3: Optional[str] = None
    address: Optional[str] = None
    build_date: Optional[str] = None
    households: Optional[int] = None
    floors: Optional[int] = None
    elevator_count: Optional[int] = None
    parking_count: Optional[int] = None
    heating_type: Optional[str] = None
    total_floor_area: Optional[float] = None
    total_site_area: Optional[float] = None
    description: Optional[str] = None

    # Internal field for categorized type
    _poi_category: Optional[POICategory] = field(init=False, default=None, repr=False)

    def __post_init__(self):
        """Validate POI information after initialization"""
        # Convert ID to string for consistency
        if isinstance(self.id, int):
            object.__setattr__(self, "id", str(self.id))

        # Validate coordinates
        if self.lat is not None or self.lng is not None:
            validated_lat, validated_lng = validate_coordinates(self.lat, self.lng)
            object.__setattr__(self, "lat", validated_lat)
            object.__setattr__(self, "lng", validated_lng)

        # Categorize the POI based on available information
        self._categorize_poi()

    def _categorize_poi(self):
        """Categorize POI based on available data"""
        # First, try to use the category field
        if self.category is not None:
            category = POICategory.from_value(self.category)
        else:
            # Infer category from other fields
            if self._looks_like_apartment():
                category = POICategory.APARTMENT
            elif self._looks_like_transit():
                category = POICategory.SUBWAY_STATION
            elif self._looks_like_hospital():
                category = POICategory.HOSPITAL
            elif self._looks_like_mart():
                category = POICategory.MART
            else:
                # Default to apartment for safety
                category = POICategory.APARTMENT

        object.__setattr__(self, "_poi_category", category)

    def _looks_like_apartment(self) -> bool:
        """Heuristic to determine if POI looks like an apartment"""
        # Must have valid apartment ID format
        if not self.is_valid_apartment_id():
            return False

        # Check for apartment-specific fields
        if (
            self.households is not None and self.households > 10
        ):  # Real apartments have 10+ households
            return True
        if self.floors is not None and self.floors > 5:  # Apartments typically have 5+ floors
            return True
        if self.address and ("아파트" in self.address):
            return True
        if self.name and any(keyword in self.name for keyword in ["아파트", "APT"]):
            return True

        # Exclude obvious non-apartments
        if self.name and any(keyword in self.name for keyword in ["역", "병원", "마트", "점"]):
            return False
        if self.description and any(
            keyword in self.description for keyword in ["호선", "선", "역", "지하철", "종합병원"]
        ):
            return False

        return False

    def _looks_like_transit(self) -> bool:
        """Heuristic to determine if POI looks like public transit"""
        if self.description and any(
            keyword in self.description for keyword in ["호선", "선", "역", "지하철", "GTX", "SRT"]
        ):
            return True
        if self.name and any(keyword in self.name for keyword in ["역", "역사", "터미널"]):
            return True
        return False

    def _looks_like_hospital(self) -> bool:
        """Heuristic to determine if POI looks like a hospital"""
        if self.description and "병원" in self.description:
            return True
        if self.name and "병원" in self.name:
            return True
        return False

    def _looks_like_mart(self) -> bool:
        """Heuristic to determine if POI looks like a mart"""
        if self.description and any(keyword in self.description for keyword in ["마트", "백화점"]):
            return True
        if self.name and any(keyword in self.name for keyword in ["마트", "점"]):
            return True
        return False

    @property
    def poi_category(self) -> POICategory:
        """Get the POI category"""
        return self._poi_category or POICategory.APARTMENT

    def is_apartment(self) -> bool:
        """Check if this POI is an apartment"""
        return self.poi_category.is_apartment()

    def is_transit(self) -> bool:
        """Check if this POI is public transit"""
        return self.poi_category.is_transit()

    def is_facility(self) -> bool:
        """Check if this POI is a public facility"""
        return self.poi_category.is_facility()

    def is_valid_apartment_id(self) -> bool:
        """Check if this POI has a valid apartment ID format"""
        # Real apartments typically have longer, more complex IDs
        if not self.id:
            return False

        id_str = str(self.id)

        # Current API returns short IDs for non-apartments:
        # - Subway stations: "bi03", "1zgA75", "1zgB56", "bhf2", "1zgzf4"
        # - Hospitals: "1Hbd0a"
        # - Marts: "1A7fe4"
        # These patterns should be excluded
        excluded_patterns = [
            "bi",  # Subway stations starting with "bi"
            "1zg",  # Subway stations starting with "1zg"
            "bh",  # Subway stations starting with "bh"
            "1H",  # Hospitals and other facilities starting with "1H"
            "1A",  # Marts and other facilities starting with "1A"
        ]

        # Exclude known non-apartment patterns
        for pattern in excluded_patterns:
            if id_str.startswith(pattern):
                return False

        # For now, only accept longer IDs or specific patterns that might be apartments
        # This is a conservative approach - better to miss some apartments than to include wrong data
        return len(id_str) >= 6

    def validate_for_apartment_crawling(self) -> bool:
        """Validate if this POI is suitable for apartment data crawling"""
        if not self.is_apartment():
            return False

        if not self.is_valid_apartment_id():
            return False

        # Must have valid coordinates
        if not self.lat or not self.lng:
            return False

        # Should have at least some apartment-specific data
        if not self.address and not self.households and not self.floors:
            return False

        return True


@dataclass(frozen=True)
class ApartmentInfo(POIInfo):
    """Extended POI info specifically for apartments"""

    complex_id: Optional[str] = None
    apt_name: Optional[str] = None
    recent_trade: Optional[TradeInfo] = None

    def __post_init__(self):
        """Post-init for apartment-specific validation"""
        # Call parent __post_init__ manually since frozen dataclass can't use super()
        if isinstance(self.id, int):
            object.__setattr__(self, "id", str(self.id))

        if self.lat is not None or self.lng is not None:
            validated_lat, validated_lng = validate_coordinates(self.lat, self.lng)
            object.__setattr__(self, "lat", validated_lat)
            object.__setattr__(self, "lng", validated_lng)

        # Categorize the POI based on available information
        self._categorize_poi()

        # Apartment-specific validation
        if self.complex_id is None and self.id is not None:
            object.__setattr__(self, "complex_id", str(self.id))


@dataclass(frozen=True)
class RankingInfo:
    """Ranking information from ranks/rolling API"""

    hash: str
    name: str
    sido_name: Optional[str] = None
    sigungu_name: Optional[str] = None
    dong_name: Optional[str] = None
    region_name: Optional[str] = None
    rank: Optional[int] = None
    prev_rank: Optional[int] = None
    visitor: Optional[int] = None
    rank_type: Optional[str] = None
    status_tag: Optional[str] = None

    def __post_init__(self):
        """Validate ranking information"""
        if self.rank is not None:
            object.__setattr__(self, "rank", int(self.rank))
        if self.prev_rank is not None:
            object.__setattr__(self, "prev_rank", int(self.prev_rank))
        if self.visitor is not None:
            object.__setattr__(self, "visitor", int(self.visitor))


@dataclass(frozen=True)
class RegionInfo:
    """Administrative region information"""

    region_code: str
    name: str
    full_name: Optional[str] = None
    children: List["RegionInfo"] = field(default_factory=list)

    def __post_init__(self):
        """Validate region information"""
        if isinstance(self.region_code, int):
            object.__setattr__(self, "region_code", str(self.region_code))


@dataclass(frozen=True)
class TransactionReport:
    """Monthly transaction report for an apartment"""

    date: datetime
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    average_price: Optional[int] = None
    volume: Optional[int] = None
    trades: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Validate transaction report data"""
        if self.min_price is not None:
            object.__setattr__(self, "min_price", validate_price(self.min_price))
        if self.max_price is not None:
            object.__setattr__(self, "max_price", validate_price(self.max_price))
        if self.average_price is not None:
            object.__setattr__(self, "average_price", validate_price(self.average_price))
        if self.volume is not None:
            object.__setattr__(self, "volume", int(self.volume))


# Factory functions to create data classes from API responses
def complex_info_from_api_response(data: Dict[str, Any]) -> ComplexInfo:
    """Create ComplexInfo from API response data

    Raises:
        KeyError: If required fields are missing
        ValueError: If field values are invalid
    """
    # Validate required fields
    id_value = data.get("id") or data.get("complex_id") or data.get("apt_id")
    if not id_value:
        raise KeyError("Missing required field: id (or complex_id, apt_id)")

    name_value = data.get("name") or data.get("apt_name")
    if not name_value:
        raise KeyError("Missing required field: name (or apt_name)")

    address_value = data.get("address") or data.get("full_address")
    if not address_value:
        raise KeyError("Missing required field: address (or full_address)")

    # Handle trade information if present
    trade_info = None
    if "trade" in data or "recent_trade" in data:
        trade_data = data.get("trade", {}) or data.get("recent_trade", {})

        # Set trade year from date if present
        trade_date = trade_data.get("date") or trade_data.get("trade_date")
        trade_year = None
        if trade_date:
            # Extract year from date string (YYYY.MM.DD or YYYY-MM-DD)
            year_str = trade_date.split(".")[0] if "." in trade_date else trade_date.split("-")[0]
            if year_str.isdigit():
                trade_year = int(year_str)

        trade_info = TradeInfo(
            trade_type=trade_data.get("type", "sale"),
            price=trade_data.get("price") or trade_data.get("deal_price"),
            deposit=trade_data.get("deposit") or trade_data.get("jeonse_price"),
            monthly_rent=trade_data.get("monthly") or trade_data.get("monthly_rent"),
            exclusive_area=trade_data.get("exclusive_area") or trade_data.get("area"),
            floor=trade_data.get("floor") or trade_data.get("floor_info"),
            trade_date=trade_date,
            trade_year=trade_year,
        )

    return ComplexInfo(
        id=id_value,
        name=name_value,
        address=address_value,
        latitude=data.get("lat") or data.get("latitude"),
        longitude=data.get("lng") or data.get("longitude"),
        build_year=data.get("build_year") or data.get("completion_year"),
        households=data.get("households") or data.get("household_count"),
        floors=data.get("floors") or data.get("max_floor"),
        elevator_count=data.get("elevatorCount"),
        parking_count=data.get("parkingCount"),
        heating_type=data.get("heatingType"),
        total_floor_area=data.get("totalFloorArea"),
        total_site_area=data.get("totalSiteArea"),
        trade_info=trade_info,
    )


def poi_info_from_bounding_response(data: Dict[str, Any]) -> POIInfo:
    """Create POIInfo from bounding box API response"""
    return POIInfo(
        id=data.get("id"),
        name=data.get("name", ""),
        lat=data.get("lat"),
        lng=data.get("lng"),
        type=data.get("type"),
        category=data.get("category"),
        region1=data.get("region1"),
        region2=data.get("region2"),
        region3=data.get("region3"),
        address=data.get("address"),
        build_date=data.get("buildDate"),
        households=data.get("households"),
        floors=data.get("floors"),
        elevator_count=data.get("elevatorCount"),
        parking_count=data.get("parkingCount"),
        heating_type=data.get("heatingType"),
        total_floor_area=data.get("totalFloorArea"),
        total_site_area=data.get("totalSiteArea"),
        description=data.get("description"),
    )


def ranking_info_from_rolling_response(data: Dict[str, Any]) -> RankingInfo:
    """Create RankingInfo from ranks/rolling API response"""
    return RankingInfo(
        hash=data.get("hash"),
        name=data.get("name"),
        sido_name=data.get("sidoName"),
        sigungu_name=data.get("sigunguName"),
        dong_name=data.get("dongName"),
        region_name=data.get("regionName"),
        rank=data.get("rank"),
        prev_rank=data.get("prevRank"),
        visitor=data.get("visitor"),
        rank_type=data.get("rankType"),
        status_tag=data.get("statusTag"),
    )


def region_info_from_api_response(data: Dict[str, Any]) -> RegionInfo:
    """Create RegionInfo from regions API response"""
    children = []
    if "children" in data:
        children = [region_info_from_api_response(child_data) for child_data in data["children"]]

    return RegionInfo(
        region_code=str(data.get("region_code") or data.get("regionCode")),
        name=data.get("name"),
        full_name=data.get("full_name") or data.get("fullName"),
        children=children,
    )


def safe_extract_field(
    data: Dict[str, Any], field_path: str, default: Any = None, field_type: Optional[type] = None
) -> Any:
    """안전하게 필드 값을 추출하고 타입 변환

    Args:
        data: 데이터 딕셔너리
        field_path: 필드 경로 (예: "data.items.0.name")
        default: 기본값
        field_type: 변환할 타입

    Returns:
        추출된 값 또는 기본값
    """
    try:
        keys = field_path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return default
            else:
                return default

        # 타입 변환
        if field_type and current is not None:
            if field_type is int:
                try:
                    return int(float(str(current)))  # 문자열 숫자 처리
                except (ValueError, TypeError):
                    return default
            elif field_type is float:
                try:
                    return float(str(current))
                except (ValueError, TypeError):
                    return default
            elif field_type is str:
                return str(current) if current is not None else default
            elif field_type is bool:
                if isinstance(current, str):
                    return current.lower() in ("true", "1", "yes", "on")
                return bool(current)

        return current
    except Exception:
        return default


def safe_extract_list(
    data: Dict[str, Any], list_path: str, default: Optional[List] = None
) -> List[Any]:
    """안전하게 리스트 필드 추출

    Args:
        data: 데이터 딕셔너리
        list_path: 리스트 필드 경로
        default: 기본값

    Returns:
        리스트 또는 기본값
    """
    result = safe_extract_field(data, list_path, default)

    # 리스트가 아니면 리스트로 변환
    if result is None:
        return []
    elif isinstance(result, list):
        return result
    else:
        return [result]


def safe_extract_nested_dict(
    data: Dict[str, Any], dict_path: str, default: Optional[Dict] = None
) -> Dict[str, Any]:
    """안전하게 중첩 딕셔너리 추출

    Args:
        data: 데이터 딕셔너리
        dict_path: 딕셔너리 필드 경로
        default: 기본값

    Returns:
        딕셔너리 또는 기본값
    """
    result = safe_extract_field(data, dict_path, default)

    if result is None:
        return {}
    elif isinstance(result, dict):
        return result
    else:
        return {}


def clean_string_value(value: Any, strip: bool = True, remove_newlines: bool = False) -> str:
    """문자열 값 정리

    Args:
        value: 원본 값
        strip: 앞뒤 공백 제거
        remove_newlines: 줄바꿈 제거

    Returns:
        정리된 문자열
    """
    if value is None:
        return ""

    # 문자열로 변환
    str_value = str(value)

    # 유니코드 정규화
    import unicodedata

    str_value = unicodedata.normalize("NFC", str_value)

    # 공백 처리
    if strip:
        str_value = str_value.strip()

    if remove_newlines:
        str_value = str_value.replace("\n", " ").replace("\r", " ")
        # 연속된 공백을 하나로
        import re

        str_value = re.sub(r"\s+", " ", str_value)

    return str_value


def validate_and_extract_coordinates(
    data: Dict[str, Any], lat_key: str = "lat", lng_key: str = "lng"
) -> tuple[Optional[float], Optional[float]]:
    """좌표 값 검증 및 추출

    Args:
        data: 데이터 딕셔너리
        lat_key: 위도 키
        lng_key: 경도 키

    Returns:
        (위도, 경도) 튜플, 유효하지 않으면 (None, None)
    """
    lat = safe_extract_field(data, lat_key, None, float)
    lng = safe_extract_field(data, lng_key, None, float)

    # 유효한 범위 확인
    if lat is not None and not (-90 <= lat <= 90):
        lat = None
    if lng is not None and not (-180 <= lng <= 180):
        lng = None

    return lat, lng


def extract_pagination_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """페이지네이션 정보 추출

    Args:
        data: API 응답 데이터

    Returns:
        페이지네이션 정보 딕셔너리
    """
    pagination = {}

    # 일반적인 페이지네이션 필드들
    pagination_fields = [
        ("page", int),
        ("limit", int),
        ("total", int),
        ("totalCount", int),
        ("offset", int),
        ("hasNext", bool),
        ("hasPrev", bool),
        ("nextPage", str),
        ("prevPage", str),
    ]

    for field_name, field_type in pagination_fields:
        value = safe_extract_field(data, field_name, None, field_type)
        if value is not None:
            pagination[field_name] = value

    return pagination

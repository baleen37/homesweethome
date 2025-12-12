"""Data models for apartment and POI data using dataclasses."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any


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

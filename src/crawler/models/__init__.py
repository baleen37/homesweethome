"""Data models for type-safe API responses and CSV output

This package provides data classes that ensure type safety and prevent
common errors when handling API responses and generating CSV output.
"""

from .api_responses import (
    APIResponse,
    ComplexInfo,
    POIInfo,
    ApartmentInfo,
    TradeInfo,
    RankingInfo,
    RegionInfo,
)

from .apartment_models import (
    RealEstateType,
    POICategory,
    BoundingBox,
    Apartment,
    POI,
    PoiData,
    ApartmentComplex,
    ApartmentFilter,
    CrawlStats,
)

from .validators import (
    validate_coordinates,
    validate_price,
    validate_area,
    validate_year,
)

__all__ = [
    # API Response Models
    "APIResponse",
    "ComplexInfo",
    "POIInfo",
    "ApartmentInfo",
    "TradeInfo",
    "RankingInfo",
    "RegionInfo",
    # Apartment Models
    "RealEstateType",
    "POICategory",
    "BoundingBox",
    "Apartment",
    "POI",
    "PoiData",
    "ApartmentComplex",
    "ApartmentFilter",
    "CrawlStats",
    # Validators
    "validate_coordinates",
    "validate_price",
    "validate_area",
    "validate_year",
]

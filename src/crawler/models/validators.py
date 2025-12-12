"""Data validation utilities for type safety

These validators ensure data integrity and provide clear error messages
when invalid data is encountered.
"""

from typing import Any, Dict, Tuple, Optional, Union


# Constants
SQM_TO_PYEONG_RATIO = 3.305785


class ValidationError(Exception):
    """Custom exception for validation errors"""

    pass


def validate_coordinates(
    lat: Optional[float], lng: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """Validate geographic coordinates

    Args:
        lat: Latitude value
        lng: Longitude value

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        ValidationError: If coordinates are out of valid range
    """
    if lat is None and lng is None:
        return None, None

    if lat is not None:
        if not isinstance(lat, (int, float)):
            raise ValidationError(f"Latitude must be a number, got {type(lat).__name__}")
        if not (-90 <= lat <= 90):
            raise ValidationError(f"Latitude must be between -90 and 90, got {lat}")

    if lng is not None:
        if not isinstance(lng, (int, float)):
            raise ValidationError(f"Longitude must be a number, got {type(lng).__name__}")
        if not (-180 <= lng <= 180):
            raise ValidationError(f"Longitude must be between -180 and 180, got {lng}")

    return float(lat) if lat is not None else None, float(lng) if lng is not None else None


def validate_price(price: Union[int, str, None]) -> Optional[int]:
    """Validate and normalize price values

    Args:
        price: Price value (may include commas as string)

    Returns:
        Normalized price as integer

    Raises:
        ValidationError: If price is invalid
    """
    if price is None:
        return None

    if isinstance(price, str):
        # Remove commas and convert to int
        price = price.replace(",", "").strip()
        if not price:
            return None
        try:
            price = int(price)
        except ValueError:
            raise ValidationError(f"Invalid price format: {price}")

    if not isinstance(price, (int, float)):
        raise ValidationError(f"Price must be a number, got {type(price).__name__}")

    if price < 0:
        raise ValidationError(f"Price cannot be negative, got {price}")

    # Convert to integer (prices are typically in units of 10,000 KRW)
    return int(price)


def validate_area(area: Union[int, float, str, None]) -> Optional[float]:
    """Validate and normalize area values

    Args:
        area: Area value in square meters

    Returns:
        Normalized area as float

    Raises:
        ValidationError: If area is invalid
    """
    if area is None:
        return None

    if isinstance(area, str):
        area = area.replace(",", "").strip()
        if not area:
            return None
        try:
            area = float(area)
        except ValueError:
            raise ValidationError(f"Invalid area format: {area}")

    if not isinstance(area, (int, float)):
        raise ValidationError(f"Area must be a number, got {type(area).__name__}")

    if area < 0:
        raise ValidationError(f"Area cannot be negative, got {area}")

    if area > 10000:  # Unreasonably large area (10,000 sqm)
        raise ValidationError(f"Area too large: {area} sqm")

    return float(area)


def validate_year(year: Union[int, str, None]) -> Optional[int]:
    """Validate and normalize year values

    Args:
        year: Year value

    Returns:
        Normalized year as integer

    Raises:
        ValidationError: If year is invalid
    """
    if year is None:
        return None

    if isinstance(year, str):
        year = year.strip()
        if not year:
            return None
        try:
            year = int(year)
        except ValueError:
            raise ValidationError(f"Invalid year format: {year}")

    if not isinstance(year, int):
        raise ValidationError(f"Year must be an integer, got {type(year).__name__}")

    current_year = 2025  # Update as needed
    if year < 1800 or year > current_year + 10:  # Allow some future dates
        raise ValidationError(f"Year out of valid range (1800-{current_year + 10}): {year}")

    return year


def validate_trade_type(trade_type: str) -> str:
    """Validate trade type

    Args:
        trade_type: Trade type string

    Returns:
        Normalized trade type

    Raises:
        ValidationError: If trade type is invalid
    """
    if not isinstance(trade_type, str):
        raise ValidationError(f"Trade type must be a string, got {type(trade_type).__name__}")

    valid_types = {"sale", "jeonse", "monthly", "jeonse/monthly"}
    trade_type = trade_type.lower().strip()

    if trade_type not in valid_types:
        raise ValidationError(f"Invalid trade type: {trade_type}. Valid types: {valid_types}")

    return trade_type


def validate_floor(floor: Union[str, int, None]) -> str:
    """Validate and normalize floor information

    Args:
        floor: Floor information

    Returns:
        Normalized floor string

    Raises:
        ValidationError: If floor is invalid
    """
    if floor is None:
        return ""

    if isinstance(floor, int):
        if floor < 0:
            raise ValidationError(f"Floor cannot be negative: {floor}")
        return str(floor)

    if isinstance(floor, str):
        floor = floor.strip()
        if not floor:
            return ""

        # Common floor patterns
        if floor.lower() in ["b1", "지하1", "지하1층"]:
            return "B1"
        elif floor.lower() in ["b2", "지하2", "지하2층"]:
            return "B2"
        elif "층" in floor:
            return floor
        elif floor.isdigit():
            return floor
        else:
            # Return as-is for non-standard formats
            return floor

    raise ValidationError(f"Invalid floor format: {floor}")


def validate_household_count(count: Union[int, str, None]) -> Optional[int]:
    """Validate household count

    Args:
        count: Number of households

    Returns:
        Normalized count as integer

    Raises:
        ValidationError: If count is invalid
    """
    if count is None:
        return None

    if isinstance(count, str):
        count = count.replace(",", "").strip()
        if not count:
            return None
        try:
            count = int(count)
        except ValueError:
            raise ValidationError(f"Invalid household count format: {count}")

    if not isinstance(count, int):
        raise ValidationError(f"Household count must be an integer, got {type(count).__name__}")

    if count < 1:
        raise ValidationError(f"Household count must be at least 1, got {count}")

    if count > 10000:  # Unreasonably large
        raise ValidationError(f"Household count too large: {count}")

    return count


def validate_building_info(
    floors: Union[int, str, None],
    elevator_count: Union[int, str, None] = None,
    parking_count: Union[int, str, None] = None,
) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Validate building information

    Args:
        floors: Number of floors
        elevator_count: Number of elevators
        parking_count: Number of parking spaces

    Returns:
        Tuple of (floors, elevator_count, parking_count)

    Raises:
        ValidationError: If any value is invalid
    """
    # Validate floors
    if floors is None:
        validated_floors = None
    elif isinstance(floors, str):
        floors = floors.replace(",", "").strip()
        if floors:
            try:
                validated_floors = int(floors)
            except ValueError:
                raise ValidationError(f"Invalid floor count format: {floors}")
        else:
            validated_floors = None
    else:
        validated_floors = int(floors) if isinstance(floors, (int, float)) else None

    if validated_floors is not None:
        if validated_floors < 1:
            raise ValidationError(f"Floor count must be at least 1, got {validated_floors}")
        if validated_floors > 200:  # Unreasonably tall
            raise ValidationError(f"Floor count too large: {validated_floors}")

    # Validate elevator count
    validated_elevator_count = _validate_count_field(elevator_count, "elevator count", 0, 50)

    # Validate parking count
    validated_parking_count = _validate_count_field(parking_count, "parking count", 0, 10000)

    return validated_floors, validated_elevator_count, validated_parking_count


def _validate_count_field(
    value: Union[int, str, None], field_name: str, min_val: int, max_val: int
) -> Optional[int]:
    """Helper function to validate count-type fields"""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if not value:
            return None
        try:
            value = int(value)
        except ValueError:
            raise ValidationError(f"Invalid {field_name} format: {value}")

    if not isinstance(value, int):
        raise ValidationError(
            f"{field_name.capitalize()} must be an integer, got {type(value).__name__}"
        )

    if value < min_val or value > max_val:
        raise ValidationError(
            f"{field_name.capitalize()} out of range ({min_val}-{max_val}): {value}"
        )

    return value


def validate_address(address: str) -> str:
    """Validate Korean address format

    Args:
        address: Address string

    Returns:
        Normalized address

    Raises:
        ValidationError: If address is invalid
    """
    if not isinstance(address, str):
        raise ValidationError(f"Address must be a string, got {type(address).__name__}")

    address = address.strip()
    if not address:
        raise ValidationError("Address cannot be empty")

    # Basic validation for Korean addresses
    # Should contain at least one of these patterns
    patterns = ["시", "도", "구", "군", "동", "면", "리", "읍"]

    if not any(pattern in address for pattern in patterns):
        # It might still be a valid address, just log a warning
        pass  # Could add logging here

    return address


def validate_complex_name(name: str) -> str:
    """Validate complex/apartment name

    Args:
        name: Complex name

    Returns:
        Normalized name

    Raises:
        ValidationError: If name is invalid
    """
    if not isinstance(name, str):
        raise ValidationError(f"Complex name must be a string, got {type(name).__name__}")

    name = name.strip()
    if not name:
        raise ValidationError("Complex name cannot be empty")

    if len(name) > 100:
        raise ValidationError(f"Complex name too long: {len(name)} characters")

    return name


def validate_poi_id(poi_id: Union[str, int, None]) -> Optional[str]:
    """Validate POI ID format

    Args:
        poi_id: POI ID from API

    Returns:
        Normalized POI ID as string

    Raises:
        ValidationError: If ID is invalid
    """
    if poi_id is None:
        return None

    if isinstance(poi_id, int):
        poi_id = str(poi_id)

    if not isinstance(poi_id, str):
        raise ValidationError(f"POI ID must be a string, got {type(poi_id).__name__}")

    poi_id = poi_id.strip()
    if not poi_id:
        raise ValidationError("POI ID cannot be empty")

    # Basic validation for ID format
    if len(poi_id) < 2:
        raise ValidationError(f"POI ID too short: {poi_id}")

    return poi_id


def validate_apartment_poi(
    poi_id: Union[str, int, None],
    address: Optional[str] = None,
    households: Optional[int] = None,
    floors: Optional[int] = None,
) -> bool:
    """Validate if POI represents a valid apartment

    Args:
        poi_id: POI ID
        address: Address string
        households: Number of households
        floors: Number of floors

    Returns:
        True if POI appears to be a valid apartment

    Raises:
        ValidationError: If required validation fails
    """
    # Validate ID first
    if poi_id:
        poi_id_str = str(poi_id)

        # Check for non-apartment ID patterns
        non_apartment_patterns = [
            ("bh", 4),  # Short IDs starting with "bh"
            ("1zg", 5),  # IDs starting with "1zg"
            ("Dn", 4),  # IDs starting with "Dn"
            ("1A", 5),  # IDs starting with "1A"
        ]

        for prefix, min_length in non_apartment_patterns:
            if poi_id_str.startswith(prefix) and len(poi_id_str) <= min_length + 2:
                return False

        # Real apartments typically have longer IDs
        if len(poi_id_str) < 5:
            return False

    # Check for apartment indicators
    apartment_indicators = 0

    if address:
        if any(keyword in address for keyword in ["아파트", "동", "번지"]):
            apartment_indicators += 1

    if households is not None and households > 0:
        # Most apartments have more than 10 households
        if households > 10:
            apartment_indicators += 1

    if floors is not None and floors > 0:
        # Most apartments have more than 3 floors
        if floors > 3:
            apartment_indicators += 1

    # Consider it an apartment if we have multiple indicators
    return apartment_indicators >= 1


def validate_coordinates_for_crawling(lat: Optional[float], lng: Optional[float]) -> bool:
    """Validate coordinates for crawling purposes

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        True if coordinates are valid for crawling
    """
    if lat is None or lng is None:
        return False

    # Check if coordinates are within reasonable bounds for Korea
    if not (33.0 <= lat <= 43.0 and 124.0 <= lng <= 132.0):
        return False

    return True


def validate_poi_completeness(poi_data: Dict[str, Any]) -> Dict[str, bool]:
    """Validate POI data completeness for different use cases

    Args:
        poi_data: POI data dictionary

    Returns:
        Dictionary with validation results for different use cases
    """
    results = {
        "has_id": bool(poi_data.get("id")),
        "has_coordinates": bool(poi_data.get("lat") and poi_data.get("lng")),
        "has_name": bool(poi_data.get("name")),
        "has_address": bool(poi_data.get("address")),
        "has_households": bool(poi_data.get("households")),
        "has_floors": bool(poi_data.get("floors")),
        "is_apartment": False,
        "is_transit": False,
        "is_facility": False,
        "suitable_for_crawling": False,
    }

    # Check POI type
    category = poi_data.get("category")
    description = poi_data.get("description", "")
    name = poi_data.get("name", "")

    if category == 1 or "호선" in description or "역" in name:
        results["is_transit"] = True
    elif category == 9 or "병원" in description or "병원" in name:
        results["is_facility"] = True
    elif category == 10 or ("마트" in description or "점" in name):
        results["is_facility"] = True

    # Determine if suitable for crawling (likely an apartment)
    apartment_indicators = 0

    if not results["is_transit"] and not results["is_facility"]:
        apartment_indicators += 1

    if results["has_households"]:
        apartment_indicators += 1

    if results["has_floors"]:
        apartment_indicators += 1

    if results["has_address"]:
        apartment_indicators += 1

    results["is_apartment"] = apartment_indicators >= 2

    # Suitable for crawling if it's likely an apartment and has essential data
    results["suitable_for_crawling"] = (
        results["is_apartment"] and results["has_id"] and results["has_coordinates"]
    )

    return results

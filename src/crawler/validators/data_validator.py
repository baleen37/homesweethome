"""Data validation utilities for apartment data

This module provides Defense-in-Depth validation layers to ensure
data quality and detect potential issues.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


class ValidationResult:
    """Result of data validation"""

    def __init__(self, is_valid: bool, reason: str = "", score: float = 0.0):
        self.is_valid = is_valid
        self.reason = reason
        self.score = score  # Confidence score (0.0 to 1.0)


class ApartmentValidator:
    """Validates apartment data with multiple layers of checks"""

    # Common patterns for apartments
    APARTMENT_PATTERNS = [
        r"아파트",
        r"APT",
        r" Apartment ",
        r"코오롱",
        r"삼성",
        r"LG",
        r"현대",
        r"롯데",
        r"포스코",
        r"신한",
        r"우성",
        r"건영",
        r"경남",
        r"동부",
        r"두산",
        r"대우",
        r"한신",
        r"한양",
        r" 힐스",
        r"레미안",
        r"자이",
        r"푸르지오",
        r"이지안",
        r"더샵",
        r"래미안",
    ]

    # Subway station patterns to exclude
    SUBWAY_PATTERNS = [
        r"역$",
        r"Station$",
        r"지하철",
        r"~선$",
        r"\d호선",
    ]

    # Non-residential patterns to exclude
    NON_RESIDENTIAL_PATTERNS = [
        r"병원$",
        r"Hospital$",
        r"학교$",
        r"School$",
        r"은행$",
        r"Bank$",
        r"마트$",
        r"Mart$",
        r"백화점$",
        r"Department",
        r"오피스",
        r"Office",
        r"타워$",
        r"Tower$",
    ]

    def __init__(self):
        """Initialize validator with compiled regex patterns"""
        self.logger = structlog.get_logger().bind(component="ApartmentValidator")

        # Compile patterns for efficiency
        self.apartment_regex = re.compile("|".join(self.APARTMENT_PATTERNS), re.IGNORECASE)
        self.subway_regex = re.compile("|".join(self.SUBWAY_PATTERNS), re.IGNORECASE)
        self.non_residential_regex = re.compile(
            "|".join(self.NON_RESIDENTIAL_PATTERNS), re.IGNORECASE
        )

    def validate_name(self, name: str) -> ValidationResult:
        """Validate apartment name

        Args:
            name: Property name to validate

        Returns:
            ValidationResult with confidence score
        """
        if not name or not isinstance(name, str):
            return ValidationResult(False, "Name is empty or not a string", 0.0)

        name = name.strip()
        score = 0.0

        # Check for non-residential patterns (negative scoring)
        if self.subway_regex.search(name):
            self.logger.warning("potential_subway_station", name=name)
            return ValidationResult(False, "Name matches subway station pattern", 0.0)

        if self.non_residential_regex.search(name):
            self.logger.warning("potential_non_residential", name=name)
            return ValidationResult(False, "Name matches non-residential pattern", 0.0)

        # Check for apartment patterns (positive scoring)
        if self.apartment_regex.search(name):
            score += 0.8
            self.logger.debug("apartment_pattern_found", name=name)

        # Additional heuristics
        # Check if name ends with typical apartment suffixes
        if re.search(r"(동|차|아파트|APT|빌라|힐스|자이|푸르지오|이지안|더샵|래미안)$", name):
            score += 0.2

        # Check for company names
        if re.search(
            r"^(삼성|LG|현대|롯데|포스코|신한|우성|건영|경남|동부|두산|대우|한신|한양)", name
        ):
            score += 0.3

        # Check for numeric patterns common in apartment names
        if re.search(r"\d+", name):
            score += 0.1

        is_valid = score >= 0.3  # Minimum threshold for confidence
        reason = f"Confidence score: {score:.2f}"

        return ValidationResult(is_valid, reason, score)

    def validate_coordinates(self, lat: Optional[float], lng: Optional[float]) -> ValidationResult:
        """Validate geographic coordinates

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            ValidationResult
        """
        if lat is None or lng is None:
            return ValidationResult(False, "Missing coordinates", 0.0)

        # Check Seoul area roughly
        if not (37.4 <= lat <= 37.7) or not (126.8 <= lng <= 127.2):
            self.logger.warning("coordinates_outside_seoul", lat=lat, lng=lng)
            return ValidationResult(False, "Coordinates outside Seoul area", 0.0)

        return ValidationResult(True, "Valid coordinates", 1.0)

    def validate_address(self, address: Optional[str]) -> ValidationResult:
        """Validate address format

        Args:
            address: Address string

        Returns:
            ValidationResult
        """
        if not address:
            return ValidationResult(False, "No address provided", 0.0)

        # Check for Korean address patterns
        if re.search(r"(서울특별시|서울)\s*\w+\s*\w+동", address):
            return ValidationResult(True, "Valid Korean address format", 1.0)

        return ValidationResult(False, "Invalid address format", 0.0)

    def validate_building_info(
        self, build_year: Optional[int], households: Optional[int]
    ) -> ValidationResult:
        """Validate building information

        Args:
            build_year: Building completion year
            households: Number of households

        Returns:
            ValidationResult
        """
        score = 0.0

        # Validate build year
        if build_year:
            if 1970 <= build_year <= 2025:
                score += 0.5
            else:
                self.logger.warning("invalid_build_year", build_year=build_year)

        # Validate household count
        if households:
            if 10 <= households <= 3000:  # Typical apartment range
                score += 0.5
            else:
                self.logger.warning("invalid_household_count", households=households)

        is_valid = score > 0.3
        return ValidationResult(is_valid, f"Building info score: {score}", score)

    def validate_item(
        self, item: Dict[str, Any]
    ) -> Tuple[ValidationResult, Dict[str, ValidationResult]]:
        """Comprehensive validation of apartment data

        Args:
            item: Dictionary containing apartment data

        Returns:
            Tuple of (overall_result, individual_results)
        """
        results = {}

        # Validate name
        name = item.get("name") or item.get("complex_name") or item.get("apt_name")
        results["name"] = (
            self.validate_name(name) if name else ValidationResult(False, "No name found", 0.0)
        )

        # Validate coordinates
        lat = item.get("lat") or item.get("latitude")
        lng = item.get("lng") or item.get("longitude")
        results["coordinates"] = self.validate_coordinates(lat, lng)

        # Validate address
        address = item.get("address") or item.get("full_addr")
        results["address"] = self.validate_address(address)

        # Validate building info
        build_year = item.get("build_year") or item.get("completion_year")
        households = item.get("households") or item.get("household_count")
        results["building"] = self.validate_building_info(build_year, households)

        # Calculate overall score
        scores = [r.score for r in results.values()]
        overall_score = sum(scores) / len(scores)

        # Name validation is critical
        if not results.get("name", ValidationResult(False)).is_valid:
            overall_score = 0.0

        overall_valid = overall_score >= 0.4 and results["name"].is_valid
        overall_result = ValidationResult(
            overall_valid, f"Overall score: {overall_score:.2f}", overall_score
        )

        # Log validation results
        self.logger.info(
            "item_validation_complete",
            item_name=name,
            is_valid=overall_valid,
            score=overall_score,
            failures=[k for k, v in results.items() if not v.is_valid],
        )

        return overall_result, results


def filter_apartments(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Filter list of items to get valid apartments only

    Uses enhanced POI data model for better validation.
    Implements stronger filtering logic based on analysis of API response patterns.

    Args:
        items: List of dictionaries to validate

    Returns:
        Tuple of (valid_items, statistics)
    """
    from ..models.api_responses import poi_info_from_bounding_response

    validator = ApartmentValidator()
    valid_items = []
    stats = {
        "total": len(items),
        "valid": 0,
        "invalid": 0,
        "reasons": {},
        "poi_types": {"apartment": 0, "transit": 0, "facility": 0, "unknown": 0},
    }

    # 아파트 이름 패턴 - 더 확실한 식별자
    APARTMENT_NAME_PATTERNS = [
        r"아파트",
        r"APT",
        r"자이",
        r"힐스테이트",
        r"래미안",
        r"푸르지오",
        r"롯데캐슬",
        r"e편한",
        r"더샵",
        r"이지안",
        r"포레",
        r" sk",
        r"GS",
        r"현대",
        r"삼성",
        r"LG",
        r"대우",
        r"동부",
        r"우성",
    ]

    # 컴파일된 정규식
    apartment_name_regex = re.compile("|".join(APARTMENT_NAME_PATTERNS), re.IGNORECASE)

    for item in items:
        # First, use POI model to determine type
        try:
            poi = poi_info_from_bounding_response(item)

            # Track POI types
            if poi.is_apartment():
                stats["poi_types"]["apartment"] += 1
            elif poi.is_transit():
                stats["poi_types"]["transit"] += 1
            elif poi.is_facility():
                stats["poi_types"]["facility"] += 1
            else:
                stats["poi_types"]["unknown"] += 1

            # 강화된 필터링 로직
            is_apartment = False
            filter_reason = ""

            # 1. Category 기반 필터링 (가장 신뢰도 높음)
            if poi.category == 1:  # 아파트 카테고리
                is_apartment = True
                filter_reason = "category_apartment"
            elif poi.category == 2:  # 지하철역
                is_apartment = False
                filter_reason = "category_subway"
            elif poi.category == 3:  # 기타 시설
                is_apartment = False
                filter_reason = "category_facility"

            # 2. Category가 없거나 모호할 경우 이름 기반 필터링
            else:
                name = poi.name.lower()
                description = (poi.description or "").lower()

                # 지하철역 제외 패턴
                if poi.category == 1 or any(
                    keyword in name for keyword in ["역", "station", "지하철"]
                ):
                    is_apartment = False
                    filter_reason = "name_subway"
                # 아파트 이름 패턴 확인
                elif apartment_name_regex.search(name) or apartment_name_regex.search(description):
                    is_apartment = True
                    filter_reason = "name_apartment_pattern"
                # 단지, 아파트 관련 키워드
                elif any(keyword in description for keyword in ["단지", "아파트", "apt"]):
                    is_apartment = True
                    filter_reason = "description_apartment"
                else:
                    is_apartment = False
                    filter_reason = "no_apartment_pattern"

            # 3. ID 패턴으로 최종 검증
            if is_apartment and not poi.is_valid_apartment_id():
                is_apartment = False
                filter_reason += "_invalid_id"

            # 최종 결정
            if is_apartment:
                valid_items.append(item)
                stats["valid"] += 1
                stats["reasons"][filter_reason] = stats["reasons"].get(filter_reason, 0) + 1
            else:
                stats["invalid"] += 1
                stats["reasons"][filter_reason] = stats["reasons"].get(filter_reason, 0) + 1

        except Exception as e:
            # Fallback to legacy validation if POI model fails
            logger.warning(
                "poi_validation_failed",
                item_id=item.get("id", "unknown"),
                error=str(e),
                fallback=True,
            )

            result, details = validator.validate_item(item)

            if result.is_valid:
                valid_items.append(item)
                stats["valid"] += 1
            else:
                stats["invalid"] += 1

                # Track failure reasons
                for field, detail in details.items():
                    if not detail.is_valid:
                        reason = f"legacy:{field}:{detail.reason}"
                        stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1

    logger.info(
        "enhanced_filtering_complete",
        total=stats["total"],
        valid=stats["valid"],
        invalid=stats["invalid"],
        valid_ratio=stats["valid"] / stats["total"] if stats["total"] > 0 else 0,
        poi_types=stats["poi_types"],
        filter_reasons=stats["reasons"],
    )

    # Add warning if no valid apartments found
    if stats["valid"] == 0 and stats["total"] > 0:
        logger.warning(
            "no_valid_apartments_found",
            message="All POIs were filtered out - check if API is returning apartment data",
            poi_types=stats["poi_types"],
            total_items=stats["total"],
            filter_reasons=stats["reasons"],
        )

    return valid_items, stats

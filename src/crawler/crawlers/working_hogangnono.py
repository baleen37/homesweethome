"""Working Hogangnono crawler using actual working APIs.

This crawler uses the confirmed working API endpoints:
- /api/v2/ranks/rolling: Get popular apartment rankings
- /api/v2/pois-bounding: Get points of interest in a bounding box
"""

import structlog
import requests
from typing import Dict, Any, List, Optional, Final, Union
from dataclasses import dataclass
from crawler.config import CrawlerConfig


logger = structlog.get_logger()


# Constants
DEFAULT_TIMEOUT: Final[int] = 30
DEFAULT_ZOOM_LEVEL: Final[int] = 17
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.0


@dataclass
class BoundingBox:
    """Represents a geographical bounding box."""

    start_x: float
    end_x: float
    start_y: float
    end_y: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary format for API."""
        return {
            "startX": self.start_x,
            "endX": self.end_x,
            "startY": self.start_y,
            "endY": self.end_y,
        }


class HogangnonoAPIError(Exception):
    """Custom exception for Hogangnono API errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class WorkingHogangnonoCrawler:
    """Hogangnono crawler that uses confirmed working API endpoints."""

    # API Endpoints
    RANKINGS_ENDPOINT: Final[str] = "/api/v2/ranks/rolling"
    POIS_ENDPOINT: Final[str] = "/api/v2/pois-bounding"

    def __init__(self, config: CrawlerConfig):
        """Initialize the crawler with configuration."""
        self.config = config
        self.base_url = "https://hogangnono.com"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create and configure HTTP session."""
        session = requests.Session()

        # Set default headers
        session.headers.update(
            {
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://hogangnono.com/",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

        return session

    def _make_request(
        self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries.

        Args:
            url: Request URL
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response data

        Raises:
            HogangnonoAPIError: If request fails after retries
        """
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(
                    "Making API request", url=url, attempt=attempt + 1, max_attempts=MAX_RETRIES
                )

                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()

                # Check API response status
                if data.get("status") != "success":
                    error_msg = data.get("message", "API returned non-success status")
                    raise HogangnonoAPIError(
                        error_msg, status_code=response.status_code, response_data=data
                    )

                logger.info("API request successful", url=url, status=response.status_code)

                return data

            except requests.RequestException as e:
                last_exception = e
                logger.warning("API request failed", url=url, attempt=attempt + 1, error=str(e))

                # Wait before retry (exponential backoff)
                if attempt < MAX_RETRIES - 1:
                    import time

                    time.sleep(RETRY_DELAY * (2**attempt))

        # All retries failed
        error_msg = f"Failed to complete request after {MAX_RETRIES} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"

        raise HogangnonoAPIError(error_msg)

    def fetch_popular_apartments(
        self, lat: Optional[float] = None, lng: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fetch popular apartment rankings.

        Args:
            lat: Latitude (currently not used by API)
            lng: Longitude (currently not used by API)

        Returns:
            Dictionary containing apartment ranking data

        Raises:
            HogangnonoAPIError: If API request fails
        """
        url = f"{self.base_url}{self.RANKINGS_ENDPOINT}"

        # Note: lat/lng parameters are not currently used by the API
        # but included for potential future use
        if lat is not None or lng is not None:
            logger.debug(
                "Location parameters provided but not used by current API", lat=lat, lng=lng
            )

        try:
            data = self._make_request(url)

            # Log success with count
            count = len(data.get("data", {}).get("rolling", []))
            logger.info(
                "Successfully fetched popular apartments", count=count, status=data.get("status")
            )

            return data

        except HogangnonoAPIError:
            raise
        except Exception as e:
            raise HogangnonoAPIError(f"Unexpected error: {str(e)}")

    def fetch_pois_in_area(
        self,
        bbox: Union[Dict[str, float], BoundingBox],
        level: int = DEFAULT_ZOOM_LEVEL,
        is_ignore_pin: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch points of interest within a bounding box.

        Args:
            bbox: Dictionary with keys startX, endX, startY, endY or BoundingBox object
            level: Zoom level (default: 17)
            is_ignore_pin: Whether to ignore pins (default: False)

        Returns:
            Dictionary containing POI data

        Raises:
            HogangnonoAPIError: If API request fails
            ValueError: If bbox is missing required keys or has invalid values
        """
        # Convert BoundingBox to dict if needed
        if isinstance(bbox, BoundingBox):
            bbox_dict = bbox.to_dict()
        else:
            bbox_dict = bbox

        # Validate bbox
        self._validate_bbox(bbox_dict)

        # Build request parameters
        params = {
            "level": level,
            "startX": bbox_dict["startX"],
            "endX": bbox_dict["endX"],
            "startY": bbox_dict["startY"],
            "endY": bbox_dict["endY"],
            "isIgnorePin": is_ignore_pin,
        }

        url = f"{self.base_url}{self.POIS_ENDPOINT}"

        try:
            logger.info(
                "Fetching POIs in area",
                url=url,
                bbox=bbox_dict,
                level=level,
                ignore_pin=is_ignore_pin,
            )

            data = self._make_request(url, params=params)

            # Log success with count
            count = len(data.get("data", []))
            logger.info("Successfully fetched POIs", count=count, status=data.get("status"))

            return data

        except HogangnonoAPIError:
            raise
        except Exception as e:
            raise HogangnonoAPIError(f"Unexpected error: {str(e)}")

    def _validate_bbox(self, bbox: Dict[str, float]) -> None:
        """
        Validate bounding box coordinates.

        Args:
            bbox: Dictionary with bounding box coordinates

        Raises:
            ValueError: If bbox is invalid
        """
        required_keys = ["startX", "endX", "startY", "endY"]
        missing_keys = [key for key in required_keys if key not in bbox]
        if missing_keys:
            raise ValueError(f"bbox missing required keys: {missing_keys}")

        # Validate coordinate values
        if bbox["startX"] >= bbox["endX"]:
            raise ValueError("startX must be less than endX")
        if bbox["startY"] >= bbox["endY"]:
            raise ValueError("startY must be less than endY")

        # Validate longitude range
        if not (-180 <= bbox["startX"] <= 180) or not (-180 <= bbox["endX"] <= 180):
            raise ValueError("Longitude values must be between -180 and 180")

        # Validate latitude range
        if not (-90 <= bbox["startY"] <= 90) or not (-90 <= bbox["endY"] <= 90):
            raise ValueError("Latitude values must be between -90 and 90")

    def parse_to_csv_format(self, data: Dict[str, Any], data_type: str) -> List[Dict[str, Any]]:
        """
        Parse API response data to CSV format.

        Args:
            data: API response data
            data_type: Type of data ('apartments' or 'pois')

        Returns:
            List of dictionaries suitable for CSV writing

        Raises:
            ValueError: If data_type is unknown
        """
        # Validate input
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        if data_type == "apartments":
            return self._parse_apartments_to_csv(data)
        elif data_type == "pois":
            return self._parse_pois_to_csv(data)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def _parse_apartments_to_csv(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse apartment ranking data to CSV format.

        Args:
            data: API response data for apartments

        Returns:
            List of apartment dictionaries in CSV format
        """
        csv_rows = []

        # Check response status
        if data.get("status") != "success":
            logger.warning(
                "API response status not success",
                status=data.get("status"),
                message=data.get("message"),
            )
            return csv_rows

        # Extract apartments array
        apartments = data.get("data", {}).get("rolling", [])
        if not apartments:
            logger.info("No apartments found in response")
            return csv_rows

        # Define field mappings for better maintainability
        field_mappings = {
            "rank": "순위",
            "prevRank": "이전순위",
            "name": "아파트명",
            "sidoName": "시도",
            "sigunguName": "시군구",
            "dongName": "동",
            "regionName": "지역명",
            "visitor": "방문자수",
            "rankType": "랭킹타입",
            "statusTag": "상태",
            "hash": "hash",
        }

        # Process each apartment
        for apt in apartments:
            if not isinstance(apt, dict):
                logger.warning("Invalid apartment data format", apartment=apt)
                continue

            # Map fields with proper defaults
            row = {}
            for api_field, csv_field in field_mappings.items():
                value = apt.get(api_field, "")
                # Special handling for numeric fields
                if api_field == "visitor":
                    value = value if value is not None else 0
                # Special handling for statusTag (None to empty string)
                elif api_field == "statusTag" and value is None:
                    value = ""
                row[csv_field] = value

            csv_rows.append(row)

        logger.info(
            "Parsed apartments to CSV format",
            count=len(csv_rows),
            total_in_response=len(apartments),
        )
        return csv_rows

    def _parse_pois_to_csv(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse POI data to CSV format.

        Args:
            data: API response data for POIs

        Returns:
            List of POI dictionaries in CSV format
        """
        csv_rows = []

        # Check response status
        if data.get("status") != "success":
            logger.warning(
                "API response status not success",
                status=data.get("status"),
                message=data.get("message"),
            )
            return csv_rows

        # Extract POIs array
        pois = data.get("data", [])
        if not pois:
            logger.info("No POIs found in response")
            return csv_rows

        # Define field mappings for better maintainability
        field_mappings = {
            "id": "ID",
            "category": "카테고리",
            "name": "이름",
            "description": "설명",
            "lat": "위도",
            "lng": "경도",
            "likes": "좋아요수",
            "isExpired": "만료여부",
            "dist": "거리(m)",
        }

        # Special fields that need None handling
        special_fields = {"address": "주소", "dong": "동", "content": "상세내용"}

        # Process each POI
        for poi in pois:
            if not isinstance(poi, dict):
                logger.warning("Invalid POI data format", poi=poi)
                continue

            # Map standard fields
            row = {}
            for api_field, csv_field in field_mappings.items():
                value = poi.get(api_field, 0)
                # Ensure numeric fields are numbers
                if api_field in ["lat", "lng", "likes", "isExpired", "dist"]:
                    value = value if value is not None else 0
                row[csv_field] = value

            # Handle special fields (convert None to empty string)
            for api_field, csv_field in special_fields.items():
                value = poi.get(api_field)
                row[csv_field] = value if value is not None else ""

            csv_rows.append(row)

        logger.info("Parsed POIs to CSV format", count=len(csv_rows), total_in_response=len(pois))
        return csv_rows

    def crawl_gangnam_area(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Crawl apartments and POIs for Gangnam area as an example.

        Returns:
            Dictionary with 'apartments' and 'pois' keys containing CSV data
        """
        logger.info("Starting Gangnam area crawl")
        results = {"apartments": [], "pois": []}

        # 1. Fetch popular apartments
        try:
            logger.info("Fetching popular apartments")
            popular_data = self.fetch_popular_apartments()
            results["apartments"] = self.parse_to_csv_format(popular_data, "apartments")
            logger.info(f"Successfully fetched {len(results['apartments'])} apartments")
        except HogangnonoAPIError as e:
            logger.error("Failed to fetch apartments", error=str(e), status_code=e.status_code)
        except Exception as e:
            logger.error("Unexpected error fetching apartments", error=str(e))

        # 2. Fetch POIs in Gangnam area
        # Gangnam-gu bounding box (approximate)
        gangnam_bbox = BoundingBox(
            start_x=127.03,  # West
            end_x=127.07,  # East
            start_y=37.48,  # South
            end_y=37.52,  # North
        )

        try:
            logger.info("Fetching POIs in Gangnam area", bbox=gangnam_bbox.to_dict())
            poi_data = self.fetch_pois_in_area(gangnam_bbox)
            results["pois"] = self.parse_to_csv_format(poi_data, "pois")
            logger.info(f"Successfully fetched {len(results['pois'])} POIs")
        except HogangnonoAPIError as e:
            logger.error("Failed to fetch POIs", error=str(e), status_code=e.status_code)
        except Exception as e:
            logger.error("Unexpected error fetching POIs", error=str(e))

        # Summary
        total_items = len(results["apartments"]) + len(results["pois"])
        logger.info(
            "Gangnam area crawl completed",
            apartments=len(results["apartments"]),
            pois=len(results["pois"]),
            total_items=total_items,
        )

        return results

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        if hasattr(self, "session"):
            self.session.close()
            logger.debug("Session closed")

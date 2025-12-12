"""호갱노노 API 전용 클라이언트

BaseAPIClient를 상속받아 중복 코드를 제거한 버전
"""

import types
from dataclasses import dataclass
from typing import Any, Optional, List, Dict

from structlog import get_logger

from crawler.config import Config, USER_AGENT
from ..utils.retry import retry_with_delay
from ..models.api_responses import (
    POIInfo,
    RankingInfo,
    poi_info_from_bounding_response,
    ranking_info_from_rolling_response,
)
from .base_api_client import BaseAPIClient, APIResponse

# Mock 객체 확인을 위한 임포트 (테스트 환경에서만 사용)
try:
    from unittest.mock import Mock
except ImportError:
    Mock = None

# Required headers per API guide
_REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hogangnono.com/",
    "Origin": "https://hogangnono.com",
}


@dataclass
class SearchParams:
    """호갱노노 API 검색 파라미터"""

    # 유효한 level 값 범위
    MIN_LEVEL = 1
    MAX_LEVEL = 18

    # 유효한 tradeType 값
    VALID_TRADE_TYPES = {0, 1, 2}

    # 유효한 aptType 값
    VALID_APT_TYPES = {-1, 0, 1, 2}

    startX: Optional[float] = None
    endX: Optional[float] = None
    startY: Optional[float] = None
    endY: Optional[float] = None
    level: Optional[int] = 17
    tradeType: Optional[int] = 0
    areaFrom: Optional[float] = None
    areaTo: Optional[float] = None
    priceFrom: Optional[int] = None
    priceTo: Optional[int] = None
    aptType: Optional[int] = -1
    priceType: Optional[int] = 0
    rentType: Optional[int] = 0
    map: str = "google"
    bbox: Optional[tuple[float, float, float, float]] = None

    def __post_init__(self):
        # bbox가 제공되면 startX/Y, endX/Y로 변환
        if self.bbox:
            lng_min, lat_min, lng_max, lat_max = self.bbox
            self.startX = lng_min
            self.endX = lng_max
            self.startY = lat_min
            self.endY = lat_max

        # 유효성 검사
        if self.level is not None and not (self.MIN_LEVEL <= self.level <= self.MAX_LEVEL):
            raise ValueError(
                f"level must be between {self.MIN_LEVEL} and {self.MAX_LEVEL}, got {self.level}"
            )
        if self.tradeType is not None and self.tradeType not in self.VALID_TRADE_TYPES:
            raise ValueError(
                f"tradeType must be one of {self.VALID_TRADE_TYPES}, got {self.tradeType}"
            )
        if self.aptType is not None and self.aptType not in self.VALID_APT_TYPES:
            raise ValueError(f"aptType must be one of {self.VALID_APT_TYPES}, got {self.aptType}")

    def to_dict(self) -> dict[str, Any]:
        """API 요청에 사용할 딕셔너리로 변환"""
        params: dict[str, Any] = {}

        # 필수 파라미터
        if self.startX is not None:
            params["startX"] = self.startX
        if self.endX is not None:
            params["endX"] = self.endX
        if self.startY is not None:
            params["startY"] = self.startY
        if self.endY is not None:
            params["endY"] = self.endY

        # 선택적 파라미터
        if self.level is not None:
            params["level"] = str(self.level)  # level은 문자열로 변환
        if self.tradeType is not None:
            params["tradeType"] = self.tradeType
        if self.areaFrom is not None:
            params["areaFrom"] = self.areaFrom
        if self.areaTo is not None:
            params["areaTo"] = self.areaTo
        if self.priceFrom is not None:
            params["priceFrom"] = self.priceFrom
        if self.priceTo is not None:
            params["priceTo"] = self.priceTo

        # 항상 포함
        params["map"] = self.map

        # aptType 포함
        if self.aptType is not None:
            params["aptType"] = self.aptType

        # priceType 포함
        if hasattr(self, "priceType") and self.priceType is not None:
            params["priceType"] = self.priceType

        # rentType 포함
        if hasattr(self, "rentType") and self.rentType is not None:
            params["rentType"] = self.rentType

        # 호갱노노 API 특정 파라미터
        params["screenWidth"] = 1200
        params["screenHeight"] = 924
        params["apt"] = ""  # 아파트 필터 (빈 문자열)

        return params


class HogangnonoAPIClient(BaseAPIClient):
    """호갱노노 API 클라이언트

    BaseAPIClient를 상속받아 중복을 제거하고 호갱노노 특화 기능만 구현
    """

    def __init__(self, config: Config):
        """클라이언트 초기화"""
        super().__init__(config=config, base_url="https://hogangnono.com")
        self.logger = get_logger().bind(component="HogangnonoAPIClient")

    def get_required_headers(self) -> Dict[str, str]:
        """호갱노노 API에 필요한 필수 헤더 반환"""
        return _REQUIRED_HEADERS

    def _initialize_session(self) -> bool:
        """호갱노노 세션 초기화 (재정의)"""
        if self._session_initialized:
            return True

        self.logger.info("Initializing session and getting cookies")

        # 메인 페이지 접속 헤더
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=self.config.TIMEOUT,
            )

            self.logger.info(
                "Session initialized",
                status_code=response.status_code,
                cookies=list(self.session.cookies.keys()),
            )

            self._session_initialized = True
            return response.status_code == 200

        except Exception as e:
            self.logger.error(
                "Failed to initialize session",
                error=str(e),
            )
            return False

    def _validate_response_data(self, api_response: APIResponse) -> APIResponse:
        """API 응답 데이터 검증

        데이터 구조 분석 및 유효성 검사
        """
        if not api_response.data:
            return api_response

        data = api_response.data

        try:
            # 데이터 정제 적용
            from ..validators import sanitize_api_data, validate_api_response

            # 데이터 정제
            sanitized_data = sanitize_api_data(data, "unknown")
            if sanitized_data != data:
                self.logger.warning("data_sanitized", changes="malformed data fixed")
                data = sanitized_data
                api_response.data = sanitized_data

            # 응답 데이터 구조 분석
            structure_info = {
                "data_type": type(data).__name__,
                "has_list": isinstance(data, list),
                "has_dict": isinstance(data, dict),
                "list_length": len(data) if isinstance(data, list) else None,
                "dict_keys": list(data.keys())[:10] if isinstance(data, dict) else None,
                "sample_items": None,
            }

            # 샘플 데이터 추출
            if isinstance(data, list) and data:
                structure_info["sample_items"] = data[:3]
            elif isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    structure_info["sample_items"] = data["data"][:3]
                elif "items" in data and isinstance(data["items"], list):
                    structure_info["sample_items"] = data["items"][:3]

            # 로깅
            self.logger.info(
                "api_response_structure",
                endpoint=api_response.status_code,
                structure=structure_info,
            )

            # 스키마 기반 검증
            response_type = self._detect_response_type(data)
            validation_report = validate_api_response(data, response_type)

            # 에러 처리 - 심각한 에러가 있는 경우 처리를 중단
            if validation_report.has_errors():
                errors = validation_report.get_errors()
                critical_errors = [e for e in errors if e.severity.value == "critical"]

                if critical_errors:
                    # Critical 에러가 있으면 응답을 실패로 처리
                    error_messages = [e.message for e in critical_errors]
                    self.logger.error(
                        "api_response_critical_validation_errors",
                        error_count=len(critical_errors),
                        errors=error_messages,
                    )
                    return APIResponse(
                        success=False,
                        error=f"Critical validation errors: {'; '.join(error_messages)}",
                        status_code=api_response.status_code,
                        data=None,
                    )

                # 일반 에러가 있으면 경고 로그와 함께 계속 진행
                non_critical_errors = [e for e in errors if e.severity.value != "critical"]
                if non_critical_errors:
                    self.logger.warning(
                        "api_response_validation_errors",
                        error_count=len(non_critical_errors),
                        errors=[e.message for e in non_critical_errors[:5]],  # 처음 5개 에러만
                    )

            # 경고 로깅
            warnings = validation_report.get_warnings()
            if warnings:
                self.logger.info(
                    "api_response_validation_warnings",
                    warning_count=len(warnings),
                    warnings=[w.message for w in warnings[:3]],  # 처음 3개 경고만
                )

            # POI 데이터 분석
            if isinstance(data, list):
                poi_analysis = self._analyze_poi_data(data)
                if poi_analysis:
                    self.logger.info("poi_data_analysis", **poi_analysis)
            elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                poi_analysis = self._analyze_poi_data(data["data"])
                if poi_analysis:
                    self.logger.info("poi_data_analysis", **poi_analysis)

        except Exception as e:
            # 검증 중 에러가 발생하면 응답을 실패로 처리
            self.logger.error(
                "response_validation_failed", error=str(e), error_type=type(e).__name__
            )
            return APIResponse(
                success=False,
                error=f"Response validation failed: {str(e)}",
                status_code=api_response.status_code,
                data=None,
            )

        return api_response

    def _detect_response_type(self, data: Any) -> str:
        """응답 타입 감지"""
        if not data:
            return "unknown"

        # 리스트 형태이면 POI
        if isinstance(data, list):
            # 첫 항목으로 POI인지 확인
            if data and isinstance(data[0], dict):
                first_item = data[0]
                if all(k in first_item for k in ["id", "lat", "lng"]):
                    return "poi"
            return "list"

        # 딕셔너리 형태
        if isinstance(data, dict):
            # 키로 응답 타입 추정
            if "data" in data:
                if isinstance(data["data"], list):
                    return "poi"
                elif isinstance(data["data"], dict):
                    # 단지 정보 특징
                    inner = data["data"]
                    if any(k in inner for k in ["complexNo", "complexName", "buildYear"]):
                        return "complex"
                    # 거래 정보 특징
                    elif any(k in inner for k in ["shortTermReport", "monthlyReport", "tradeType"]):
                        return "transaction"

            # 최상위 키로 판단
            if any(k in data for k in ["complexNo", "complexName", "name", "buildYear"]):
                return "complex"
            elif any(k in data for k in ["shortTermReport", "reports", "transactions"]):
                return "transaction"

        return "unknown"

    def _analyze_poi_data(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """POI 데이터 분석"""
        if not data_list:
            return {}

        analysis = {
            "total_items": len(data_list),
            "poi_types": {},
            "has_apartments": False,
            "has_transit": False,
            "has_facilities": False,
            "id_patterns": {},
        }

        # 첫 100개 항목만 분석 (성능 고려)
        sample_size = min(100, len(data_list))
        for item in data_list[:sample_size]:
            # ID 패턴 분석
            item_id = str(item.get("id", ""))
            if item_id:
                if item_id.isdigit():
                    analysis["id_patterns"]["numeric"] = (
                        analysis["id_patterns"].get("numeric", 0) + 1
                    )
                elif item_id.startswith("APT_"):
                    analysis["id_patterns"]["apt_prefixed"] = (
                        analysis["id_patterns"].get("apt_prefixed", 0) + 1
                    )
                else:
                    analysis["id_patterns"]["other"] = analysis["id_patterns"].get("other", 0) + 1

            # POI 타입 분석
            name = item.get("name", "").lower()
            category = item.get("category", "")

            if "역" in name or "station" in name or category == 2:
                analysis["has_transit"] = True
                analysis["poi_types"]["transit"] = analysis["poi_types"].get("transit", 0) + 1
            elif any(keyword in name for keyword in ["아파트", "apt"]) or category == 1:
                analysis["has_apartments"] = True
                analysis["poi_types"]["apartment"] = analysis["poi_types"].get("apartment", 0) + 1
            elif any(keyword in name for keyword in ["병원", "hospital", "마트", "mart"]):
                analysis["has_facilities"] = True
                analysis["poi_types"]["facility"] = analysis["poi_types"].get("facility", 0) + 1

        return analysis

    # API 메서드들 - BaseAPIClient의 _make_request를 사용하여 중복 제거
    def get_complex_list(
        self,
        cortar_no: str,
        bounds: Optional[str] = None,
    ) -> APIResponse:
        """단지 목록 조회"""
        params = {"cortarNo": cortar_no}
        if bounds:
            params["bounds"] = bounds

        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexList",
            params=params,
        )

    def get_complex_detail(self, complex_id: str) -> APIResponse:
        """단지 상세 정보 조회"""
        params = {"complexNo": complex_id}
        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexDetail",
            params=params,
        )

    def get_apartments_bounding(self, search_params: SearchParams) -> APIResponse:
        """아파트/매물 목록 조회 (Bounding box 기반)"""
        return self._make_request(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=search_params.to_dict(),
        )

    def get_ranking(self, rank_type: str = "daily", limit: int = 100) -> APIResponse:
        """인기 순위 조회"""
        params = {"type": rank_type, "limit": limit}
        return self._make_request(
            method="GET",
            endpoint="/api/v2/ranks/rolling",
            params=params,
        )

    def get_regions(self, region_code: Optional[str] = None) -> APIResponse:
        """시/도, 구/군 목록 조회"""
        params = {}
        if region_code:
            params["regionCode"] = region_code

        # regions API는 간단한 헤더 사용
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

        return self._make_request(
            method="GET",
            endpoint="/api/v2/regions",
            params=params,
            headers=headers,
        )

    # 데이터 처리 유틸리티 메서드들
    def parse_complexes_from_ranks(self, ranks_data: dict[str, Any]) -> List[RankingInfo]:
        """ranks/rolling 응답에서 단지 정보 파싱"""
        complexes = []

        if (
            not ranks_data
            or "data" not in ranks_data
            or "rolling" not in ranks_data.get("data", {})
        ):
            return complexes

        for item in ranks_data["data"]["rolling"]:
            ranking_info = ranking_info_from_rolling_response(item)
            complexes.append(ranking_info)

        return complexes

    def parse_pois_from_bounding(self, pois_data: dict[str, Any]) -> List[POIInfo]:
        """pois-bounding 응답에서 POI 정보 파싱"""
        pois = []

        if not pois_data or "data" not in pois_data:
            return pois

        for item in pois_data["data"]:
            poi_info = poi_info_from_bounding_response(item)
            if poi_info.validate_for_apartment_crawling():
                pois.append(poi_info)

        return pois

    def close(self) -> None:
        """세션 종료"""
        self.session.close()
        self.logger.info("API client session closed")

    def __enter__(self) -> "HogangnonoAPIClient":
        """Context manager 진입"""
        # Context manager 진입 시 자동으로 세션 초기화
        self._initialize_session()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager 종료

        Context manager에서 발생한 예외 정보는 무시하고 자원 정리만 수행합니다.

        Args:
            _exc_type: 발생한 예외의 타입 (사용하지 않음)
            _exc_val: 발생한 예외 객체 (사용하지 않음)
            _exc_tb: 예외의 traceback (사용하지 않음)
        """
        self.close()

    def fetch_ranks_rolling(self) -> dict[str, Any]:
        """인기 순위 롤링 데이터 조회

        Returns:
            API 응답 데이터
        """

        def _fetch():
            response = self._make_request(
                method="GET",
                endpoint="/api/v2/ranks/rolling",
            )

            if not response.success:
                raise Exception(f"Failed to fetch ranks/rolling: {response.error}")

            return response.data

        return retry_with_delay(_fetch, max_attempts=3, delay=1.0, logger=self.logger)

    def fetch_pois_bounding(self, bounds: dict[str, float]) -> dict[str, Any]:
        """POI 데이터 조회 (Bounding box 기반)

        Args:
            bounds: 좌표 정보 (startX, endX, startY, endY)

        Returns:
            API 응답 데이터
        """

        def _fetch():
            # 실제 API 파라미터 형식에 맞게 전달
            params = {
                "level": 17,
                "startX": bounds["startX"],
                "endX": bounds["endX"],
                "startY": bounds["startY"],
                "endY": bounds["endY"],
                "isIgnorePin": False,
            }

            response = self._make_request(
                method="GET",
                endpoint="/api/v2/pois-bounding",
                params=params,
            )

            if not response.success:
                raise Exception(f"Failed to fetch pois-bounding: {response.error}")

            return response.data

        return retry_with_delay(_fetch, max_attempts=3, delay=1.0, logger=self.logger)

    def to_csv_rows_complexes(self, complexes_data: dict[str, Any]) -> List[dict[str, Any]]:
        """단지 데이터를 CSV 행으로 변환

        Args:
            complexes_data: 단지 데이터

        Returns:
            CSV 행 리스트
        """
        from ..models.csv_models import RankingCSVRow

        rows = []
        complexes = self.parse_complexes_from_ranks(complexes_data)

        for complex_item in complexes:
            csv_row = RankingCSVRow.from_ranking_info(complex_item)
            rows.append(csv_row.to_dict())

        return rows

    def to_csv_rows_pois(self, pois_data: dict[str, Any]) -> List[dict[str, Any]]:
        """POI 데이터를 CSV 행으로 변환

        Args:
            pois_data: POI 데이터

        Returns:
            CSV 행 리스트
        """
        from ..models.csv_models import POICSVRow

        rows = []
        pois = self.parse_pois_from_bounding(pois_data)

        for poi in pois:
            csv_row = POICSVRow.from_poi_info(poi)
            rows.append(csv_row.to_dict())

        return rows

    def fetch_apartments_by_pois(self, pois_response: dict[str, Any]) -> list[dict[str, Any]]:
        """API 응답에서 아파트 데이터 추출

        Args:
            pois_response: API 응답 데이터 (get_apartments_bounding 결과)

        Returns:
            아파트 매물 정보 리스트
        """
        apartments = []

        # Parse POIs and filter for apartments only
        pois = self.parse_pois_from_bounding(pois_response)

        # Convert POIInfos to apartment dict format
        for poi in pois:
            # Only process valid apartments
            if not poi.validate_for_apartment_crawling():
                continue

            apartment_info = {
                "id": poi.id,
                "name": poi.name,
                "lat": poi.lat,
                "lng": poi.lng,
                "address": poi.address,
                "build_year": poi.build_date,  # POI uses build_date
                "households": poi.households,
                "floors": poi.floors,
                "raw_data": poi.__dict__,  # Store the POI object data
            }
            apartments.append(apartment_info)

        self.logger.info(
            "apartments_extracted_from_pois",
            total_pois=len(pois_response.get("data", [])),
            valid_apartments=len(apartments),
        )

        return apartments

    def search_apartments_by_location(
        self, center_lng: float, center_lat: float, delta: float = 0.02, level: int = 17
    ) -> dict[str, Any]:
        """위치 기반 아파트 검색

        Args:
            center_lng: 중심 경도
            center_lat: 중심 위도
            delta: 좌표 범위
            level: 줌 레벨

        Returns:
            검색 결과
        """

        def _search():
            # POI 데이터로부터 아파트 정보 조회
            bounds = {
                "startX": center_lng - delta,
                "endX": center_lng + delta,
                "startY": center_lat - delta,
                "endY": center_lat + delta,
            }

            # POI 데이터 가져오기
            pois_response = self.fetch_pois_bounding(bounds)

            if not pois_response or not pois_response.get("data"):
                return {"success": False, "error": "Failed to fetch POI data", "apartments": []}

            # POI에서 아파트 추출
            apartments = self.fetch_apartments_by_pois(pois_response)

            return {
                "success": True,
                "total_pois": len(pois_response.get("data", [])),
                "apartments": apartments,
                "bounds": bounds,
                "error": None,
            }

        return retry_with_delay(_search, max_attempts=3, delay=1.0, logger=self.logger)

    def _get_headers(self) -> dict[str, str]:
        """API 호출용 헤더 생성 (테스트용)

        Returns:
            API 요청 헤더 딕셔너리
        """
        # 테스트에서는 간단한 헤더만 반환
        return {
            "User-Agent": getattr(self.config, "user_agent", "Mozilla/5.0"),
            "Accept": "application/json",
            "x-hogangnono-app-name": "hogangnono",
            "x-hogangnono-api-version": "2.4.0",
            "x-hogangnono-platform": "desktop",
        }

    def fetch_dong_codes(
        self, district_name: str, lat: float = None, lng: float = None
    ) -> dict[str, str]:
        """API를 통해 동 코드 정보 가져오기

        Args:
            district_name: 구/군 이름
            lat: 위도 (선택사항)
            lng: 경도 (선택사항)

        Returns:
            동 이름과 코드의 매핑 딕셔너리
        """
        search_url = "https://hogangnono.com/api/v2/searches/new"
        params = {"query": district_name}
        if lat is not None:
            params["y"] = lat
        if lng is not None:
            params["x"] = lng

        try:
            response = self._make_request("GET", search_url, params=params, timeout=10)

            if not response.success or not response.data:
                self.logger.error(
                    "fetch_dong_codes_failed", district=district_name, error=response.error
                )
                return {}

            data = response.data

            if data.get("status") != "success":
                return {}

            dongs = {}
            # The matched data is nested inside data.data
            matched = data.get("data", {}).get("matched", {})

            if "region" in matched:
                for item in matched["region"].get("list", []):
                    if item.get("local_type") == "local3":  # 동 정보
                        dong_name = item.get("local3_name", "")
                        dong_code = item.get("local3_code", "")
                        if dong_name and dong_code:
                            dongs[dong_name] = dong_code

            return dongs

        except Exception as e:
            self.logger.error("fetch_dong_codes_error", district=district_name, error=str(e))
            return {}

"""아파트 데이터 유효성 검증기

POI 데이터 중 실제 아파트인지 검증하고 유효한 데이터만 필터링
"""

from typing import List, Optional, Dict, Any
from structlog import get_logger

from ..models.apartment_models import Apartment, RealEstateType, POICategory, ApartmentFilter
from ..models.api_responses import POIInfo

logger = get_logger(__name__)


class ApartmentValidator:
    """아파트 데이터 유효성 검증기"""

    # POI 카테고리 매핑
    _CATEGORY_MAP = {
        1: POICategory.SUBWAY,
        9: POICategory.HOSPITAL,
        10: POICategory.MART,
        # 다른 카테고리들도 필요시 추가
    }

    # 아파트로 간주할 수 있는 키워드
    _APARTMENT_KEYWORDS = [
        "아파트",
        "주상복합",
        "오피스텔",
        "빌딩",
        "타워",
        "프라자",
        "트리플",
        "스퀘어",
        "센트럴",
        "포레",
        "힐스",
        "파크",
        "밸리",
        "리버",
        "레이크",
        "시티",
        "메트로",
        "더샵",
        "래미안",
        "힐스테이트",
        "푸르지오",
        "이지더원",
        "자이",
        "SK뷰",
        "롯데캐슬",
        "한신",
        "극동",
        "삼성",
        "현대",
        "대우",
        "LG",
        "포스코",
        "한화",
        "금호",
        "동부",
        "성원",
        "중흥",
        "GS",
        "월드메르디앙",
    ]

    @classmethod
    def is_apartment_poi(cls, poi_info: POIInfo) -> bool:
        """POI가 아파트인지 확인

        Args:
            poi_info: POI 정보

        Returns:
            아파트 여부
        """
        # 1. ID 형식 확인 (APT_ 접두사)
        if poi_info.id and poi_info.id.startswith("APT_"):
            return True

        # 2. 이름으로 아파트인지 확인
        if poi_info.name:
            name_lower = poi_info.name.lower()
            for keyword in cls._APARTMENT_KEYWORDS:
                if keyword in name_lower:
                    return True

        # 3. households 필드 존재 확인 (아파트 특유 필드)
        if hasattr(poi_info, "households") and poi_info.households:
            if isinstance(poi_info.households, (int, float)) and poi_info.households > 0:
                return True

        # 4. floors 필드 존재 확인 (아파트 특유 필드)
        if hasattr(poi_info, "floors") and poi_info.floors:
            if isinstance(poi_info.floors, (int, float)) and poi_info.floors > 0:
                return True

        return False

    @classmethod
    def extract_apartment_from_poi(cls, poi_info: POIInfo) -> Optional[Apartment]:
        """POI 정보에서 아파트 데이터 추출

        Args:
            poi_info: POI 정보

        Returns:
            추출된 아파트 데이터 또는 None
        """
        if not cls.is_apartment_poi(poi_info):
            return None

        # ID 형식 보정
        complex_id = poi_info.id
        if not complex_id.startswith("APT_"):
            # 아파트 이름으로부터 ID 생성 (일관성을 위해)
            import hashlib

            name_hash = hashlib.md5(poi_info.name.encode()).hexdigest()[:4]
            complex_id = f"APT_{name_hash}"

        # 부동산 유형 결정
        real_estate_type = cls._determine_real_estate_type(poi_info.name)

        # 좌표 추출
        coordinates = None
        if hasattr(poi_info, "latitude") and hasattr(poi_info, "longitude"):
            if poi_info.latitude and poi_info.longitude:
                coordinates = (float(poi_info.latitude), float(poi_info.longitude))

        # 평형 정보 추출
        pyeong_types = None
        if hasattr(poi_info, "areaInfo") and poi_info.areaInfo:
            pyeong_types = str(poi_info.areaInfo)

        return Apartment(
            complex_id=complex_id,
            complex_name=poi_info.name or "",
            real_estate_type=real_estate_type,
            completion_year_month=getattr(poi_info, "completionDate", None),
            total_dong_count=getattr(poi_info, "dongCount", None),
            total_household_count=getattr(poi_info, "households", None),
            min_area=getattr(poi_info, "minArea", None),
            max_area=getattr(poi_info, "maxArea", None),
            pyeong_types=pyeong_types,
            address=getattr(poi_info, "address", None),
            coordinates=coordinates,
        )

    @classmethod
    def _determine_real_estate_type(cls, name: str) -> RealEstateType:
        """이름으로 부동산 유형 결정"""
        if not name:
            return RealEstateType.UNKNOWN

        name_lower = name.lower()
        if "주상복합" in name_lower or any(
            keyword in name_lower for keyword in ["타워", "프라자", "트리플", "스퀘어"]
        ):
            return RealEstateType.MIXED_USE
        elif "오피스텔" in name_lower:
            return RealEstateType.OFFICETEL
        else:
            return RealEstateType.APARTMENT

    @classmethod
    def filter_valid_apartments(
        cls, pois: List[POIInfo], apartment_filter: Optional[ApartmentFilter] = None
    ) -> List[Apartment]:
        """POI 리스트에서 유효한 아파트만 필터링

        Args:
            pois: POI 정보 리스트
            apartment_filter: 아파트 필터 (선택사항)

        Returns:
            필터링된 아파트 리스트
        """
        if apartment_filter is None:
            apartment_filter = ApartmentFilter()

        valid_apartments = []
        filtered_count = 0

        for poi in pois:
            apartment = cls.extract_apartment_from_poi(poi)

            if apartment is None:
                filtered_count += 1
                continue

            # 유효성 검증
            if not apartment.is_valid_apartment():
                logger.warning(
                    "invalid_apartment_skipped",
                    apartment_id=apartment.complex_id,
                    apartment_name=apartment.complex_name,
                    reason="Failed validation",
                )
                filtered_count += 1
                continue

            # 필터 조건 확인
            if not apartment_filter.is_valid(apartment):
                logger.debug(
                    "apartment_filtered",
                    apartment_id=apartment.complex_id,
                    apartment_name=apartment.complex_name,
                    reason="Does not meet filter criteria",
                )
                filtered_count += 1
                continue

            valid_apartments.append(apartment)

        logger.info(
            "apartment_filtering_completed",
            total_pois=len(pois),
            valid_apartments=len(valid_apartments),
            filtered_count=filtered_count,
            filter_rate=filtered_count / len(pois) if pois else 0,
        )

        return valid_apartments

    @classmethod
    def validate_csv_data_consistency(cls, apartments: List[Apartment]) -> Dict[str, Any]:
        """CSV 데이터 일관성 검증

        Args:
            apartments: 아파트 리스트

        Returns:
            검증 결과
        """
        validation_result = {
            "total_apartments": len(apartments),
            "valid_apartments": 0,
            "invalid_apartments": 0,
            "issues": [],
        }

        for apartment in apartments:
            if apartment.is_valid_apartment():
                validation_result["valid_apartments"] += 1
            else:
                validation_result["invalid_apartments"] += 1
                validation_result["issues"].append(
                    {
                        "apartment_id": apartment.complex_id,
                        "apartment_name": apartment.complex_name,
                        "issues": cls._get_validation_issues(apartment),
                    }
                )

        return validation_result

    @classmethod
    def _get_validation_issues(cls, apartment: Apartment) -> List[str]:
        """아파트 유효성 이슈 확인"""
        issues = []

        if not apartment.complex_id:
            issues.append("Missing complex_id")
        elif not apartment.complex_id.startswith("APT_"):
            issues.append("Invalid complex_id format")

        if not apartment.complex_name:
            issues.append("Missing complex_name")

        if apartment.total_household_count is None or apartment.total_household_count <= 0:
            issues.append("Invalid or missing household count")

        return issues

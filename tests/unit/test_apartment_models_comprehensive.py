"""아파트 모델 테스트

TDD 접근법으로 작성된 아파트 데이터 모델 테스트입니다.
"""

import pytest
from datetime import datetime

from src.crawler.models.apartment_models import (
    RealEstateType,
    POICategory,
    BoundingBox,
    Apartment,
    POI,
    ApartmentFilter,
)


class TestRealEstateType:
    """RealEstateType Enum 테스트"""

    def test_real_estate_type_values(self):
        """부동산 유형 값 확인"""
        assert RealEstateType.APARTMENT.value == "아파트"
        assert RealEstateType.MIXED_USE.value == "주상복합"
        assert RealEstateType.OFFICETEL.value == "오피스텔"
        assert RealEstateType.UNKNOWN.value == "알 수 없음"

    def test_real_estate_type_iteration(self):
        """부동산 유형 순회 테스트"""
        types = list(RealEstateType)
        assert len(types) == 4
        assert RealEstateType.APARTMENT in types
        assert RealEstateType.MIXED_USE in types
        assert RealEstateType.OFFICETEL in types
        assert RealEstateType.UNKNOWN in types


class TestPOICategory:
    """POICategory Enum 테스트"""

    def test_poi_category_values(self):
        """POI 카테고리 값 확인"""
        assert POICategory.SUBWAY.value == "지하철역"
        assert POICategory.HOSPITAL.value == "병원"
        assert POICategory.MART.value == "마트"
        assert POICategory.APARTMENT.value == "아파트"
        assert POICategory.SCHOOL.value == "학교"
        assert POICategory.ETC.value == "기타"

    def test_poi_category_iteration(self):
        """POI 카테고리 순회 테스트"""
        categories = list(POICategory)
        assert len(categories) == 6


class TestBoundingBox:
    """BoundingBox 데이터클래스 테스트"""

    def test_bounding_box_creation(self):
        """바운딩 박스 생성 테스트"""
        bbox = BoundingBox(min_x=126.0, max_x=127.0, min_y=37.0, max_y=38.0)

        assert bbox.min_x == 126.0
        assert bbox.max_x == 127.0
        assert bbox.min_y == 37.0
        assert bbox.max_y == 38.0

    def test_to_tuple(self):
        """튜플 변환 테스트"""
        bbox = BoundingBox(1.0, 2.0, 3.0, 4.0)
        result = bbox.to_tuple()
        assert result == (1.0, 2.0, 3.0, 4.0)
        assert isinstance(result, tuple)

    def test_bounding_box_immutability(self):
        """바운딩 박스 불변성 테스트"""
        bbox = BoundingBox(1.0, 2.0, 3.0, 4.0)

        # frozen=True 이므로 속성 변경 시도 시 에러 발생
        with pytest.raises(Exception):
            bbox.min_x = 5.0

    def test_invalid_bounding_box(self):
        """잘못된 바운딩 박스 테스트"""
        # min이 max보다 큰 경우 (유효하지 않지만 dataclass는 허용)
        bbox = BoundingBox(min_x=127.0, max_x=126.0, min_y=38.0, max_y=37.0)
        assert bbox.min_x == 127.0
        assert bbox.max_x == 126.0


class TestApartment:
    """Apartment 데이터클래스 테스트"""

    def test_apartment_creation_minimal(self):
        """최소 정보로 아파트 생성 테스트"""
        apartment = Apartment(
            complex_id="APT_001",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
        )

        assert apartment.complex_id == "APT_001"
        assert apartment.complex_name == "테스트 아파트"
        assert apartment.real_estate_type == RealEstateType.APARTMENT
        assert apartment.completion_year_month is None
        assert apartment.total_dong_count is None
        assert apartment.total_household_count is None
        assert apartment.min_area is None
        assert apartment.max_area is None
        assert apartment.deal_count == 0
        assert apartment.lease_count == 0
        assert apartment.rent_count == 0
        assert apartment.pyeong_types is None
        assert apartment.address is None
        assert apartment.coordinates is None
        assert isinstance(apartment.fetched_at, datetime)

    def test_apartment_creation_full(self):
        """전체 정보로 아파트 생성 테스트"""
        apartment = Apartment(
            complex_id="APT_002",
            complex_name="테스트 주상복합",
            real_estate_type=RealEstateType.MIXED_USE,
            completion_year_month="202001",
            total_dong_count=5,
            total_household_count=1000,
            min_area=59.5,
            max_area=128.8,
            deal_count=10,
            lease_count=5,
            rent_count=8,
            pyeong_types="18, 25, 33, 39",
            address="서울시 강남구 테헤란로",
            coordinates=(37.5172, 127.0473),
        )

        assert apartment.complex_id == "APT_002"
        assert apartment.complex_name == "테스트 주상복합"
        assert apartment.real_estate_type == RealEstateType.MIXED_USE
        assert apartment.completion_year_month == "202001"
        assert apartment.total_dong_count == 5
        assert apartment.total_household_count == 1000
        assert apartment.min_area == 59.5
        assert apartment.max_area == 128.8
        assert apartment.deal_count == 10
        assert apartment.lease_count == 5
        assert apartment.rent_count == 8
        assert apartment.pyeong_types == "18, 25, 33, 39"
        assert apartment.address == "서울시 강남구 테헤란로"
        assert apartment.coordinates == (37.5172, 127.0473)
        assert isinstance(apartment.fetched_at, datetime)

    def test_apartment_is_valid(self):
        """아파트 유효성 검증 테스트"""
        # 유효한 아파트
        valid_apartment = Apartment(
            complex_id="APT_001",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=100,
        )
        assert valid_apartment.is_valid_apartment()

        # APT_ 접두사가 없는 경우
        invalid_apartment = Apartment(
            complex_id="NOT_APT_001",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=100,
        )
        assert not invalid_apartment.is_valid_apartment()

        # 세대수가 없는 경우
        invalid_apartment = Apartment(
            complex_id="APT_001",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
        )
        assert not invalid_apartment.is_valid_apartment()

    def test_apartment_to_csv_row(self):
        """CSV 행 변환 테스트"""
        apartment = Apartment(
            complex_id="APT_001",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            completion_year_month="202001",
            total_dong_count=5,
            total_household_count=100,
            coordinates=(37.5172, 127.0473),
        )

        csv_row = apartment.to_csv_row()
        assert csv_row["complex_id"] == "APT_001"
        assert csv_row["complex_name"] == "테스트 아파트"
        assert csv_row["real_estate_type"] == "아파트"
        assert csv_row["completion_year_month"] == "202001"
        assert csv_row["latitude"] == 37.5172
        assert csv_row["longitude"] == 127.0473


class TestPOI:
    """POI 데이터클래스 테스트"""

    def test_poi_creation_minimal(self):
        """최소 정보로 POI 생성 테스트"""
        poi = POI(
            id="POI001",
            name="테스트 POI",
            category=POICategory.SUBWAY,
            coordinates=(37.5172, 127.0473),
        )

        assert poi.id == "POI001"
        assert poi.name == "테스트 POI"
        assert poi.category == POICategory.SUBWAY
        assert poi.coordinates == (37.5172, 127.0473)
        assert poi.address is None

    def test_poi_creation_full(self):
        """전체 정보로 POI 생성 테스트"""
        poi = POI(
            id="POI002",
            name="서울대병원",
            category=POICategory.HOSPITAL,
            coordinates=(37.5796, 127.0027),
            address="서울특별시 종로구 연건로 101",
        )

        assert poi.id == "POI002"
        assert poi.name == "서울대병원"
        assert poi.category == POICategory.HOSPITAL
        assert poi.address == "서울특별시 종로구 연건로 101"

    def test_poi_is_apartment(self):
        """아파트 POI 확인 테스트"""
        # 아파트 POI
        apartment_poi = POI(
            id="APT_001",
            name="테스트 아파트",
            category=POICategory.APARTMENT,
            coordinates=(37.5172, 127.0473),
        )
        assert apartment_poi.is_apartment()

        # 아파트가 아닌 POI
        subway_poi = POI(
            id="SUB001",
            name="테스트 역",
            category=POICategory.SUBWAY,
            coordinates=(37.5172, 127.0473),
        )
        assert not subway_poi.is_apartment()

        # APT_ 접두사가 없는 아파트
        invalid_poi = POI(
            id="APARTMENT001",
            name="테스트 아파트",
            category=POICategory.APARTMENT,
            coordinates=(37.5172, 127.0473),
        )
        assert not invalid_poi.is_apartment()


class TestApartmentFilter:
    """ApartmentFilter 데이터클래스 테스트"""

    def test_filter_initialization(self):
        """필터 초기화 테스트"""
        filter_obj = ApartmentFilter()
        assert filter_obj.min_household_count == 1
        assert filter_obj.max_household_count is None
        assert RealEstateType.APARTMENT in filter_obj.allowed_real_estate_types
        assert RealEstateType.MIXED_USE in filter_obj.allowed_real_estate_types
        assert RealEstateType.OFFICETEL not in filter_obj.allowed_real_estate_types

    def test_filter_is_valid(self):
        """필터 유효성 검증 테스트"""
        filter_obj = ApartmentFilter(min_household_count=100)

        # 유효한 아파트
        valid_apartment = Apartment(
            complex_id="APT_001",
            complex_name="테스트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=200,
        )
        assert filter_obj.is_valid(valid_apartment)

        # 세대수가 부족한 아파트
        small_apartment = Apartment(
            complex_id="APT_002",
            complex_name="작은 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=50,
        )
        assert not filter_obj.is_valid(small_apartment)

        # 허용되지 않는 유형
        officetel = Apartment(
            complex_id="APT_003",
            complex_name="오피스텔",
            real_estate_type=RealEstateType.OFFICETEL,
            total_household_count=200,
        )
        assert not filter_obj.is_valid(officetel)

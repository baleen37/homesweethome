"""네이버 부동산 매물 DTO"""

from pydantic import BaseModel, Field


class NaverAptDTO(BaseModel):
    """네이버 부동산 아파트 단지 정보"""

    complex_no: str = Field(description="단지 번호")
    complex_name: str = Field(description="단지 이름")
    article_count: int = Field(default=0, description="매물 수")
    build_year: int | None = Field(default=None, description="건축 연도")
    household_count: int | None = Field(default=None, description="세대수")
    latitude: float | None = Field(default=None, description="위도")
    longitude: float | None = Field(default=None, description="경도")
    address: str | None = Field(default=None, description="주소")
    area_code: str | None = Field(default=None, description="지역 코드")


class NaverListingDTO(BaseModel):
    """네이버 부동산 개별 매물 정보"""

    article_no: str = Field(description="매물 번호")
    complex_name: str = Field(description="단지 이름")
    complex_no: str = Field(description="단지 번호")
    trade_type: str = Field(description="거래 유형 (매매/전세/월세)")

    # 가격 정보
    deal_price: int | None = Field(default=None, description="매매가 (원)")
    jeonse_price: int | None = Field(default=None, description="전세가 (원)")
    monthly_price: int | None = Field(default=None, description="월세 (원)")

    # 상세 정보
    floor_info: str = Field(default="", description="층수 정보")
    area1: float | None = Field(default=None, description="면적 (㎡) - 공급면적")
    area2: float | None = Field(default=None, description="면적 (㎡) - 전용면적")
    direction: str = Field(default="", description="향")
    description: str = Field(default="", description="매물 설명")

    # 날짜 정보
    confirm_date: str | None = Field(default=None, description="확인일자")

    # 중개사 정보
    agent_name: str = Field(default="", description="중개사 이름")
    agent_office: str = Field(default="", description="중개사 상호")
    phone1: str = Field(default="", description="연락처1")
    phone2: str = Field(default="", description="연락처2")


class NaverSearchResultDTO(BaseModel):
    """네이버 부동산 검색 결과"""

    apartments: list[NaverAptDTO] = Field(default_factory=list, description="아파트 목록")
    listings: list[NaverListingDTO] = Field(default_factory=list, description="매물 목록")
    total_count: int = Field(default=0, description="전체 결과 수")

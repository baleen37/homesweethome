"""ASIL 실거래가 DTO"""

from pydantic import BaseModel, ConfigDict, Field


class AsilTradePriceDetailDTO(BaseModel):
    """ASIL 실거래가 상세 DTO

    일별 거래 상세 정보 (동, 층, 가격 등)
    """

    model_config = ConfigDict(extra="allow")

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking field names (including extra fields)"""
        return key in self.model_dump()

    money: str | None = Field(default=None, description="매매가 (Base64 암호화)")
    rent: str | None = Field(default=None, description="전세가 (Base64 암호화)")
    floor: str | None = Field(default=None, description="층")
    dong: str | None = Field(default=None, description="동 (Base64 암호화)")
    day: str | None = Field(default=None, description="거래 일")
    type: str | None = Field(default=None, description="거래 유형 코드")
    apt: str | None = Field(default=None, description="아파트 코드")


class AsilTradePriceDayDTO(BaseModel):
    """ASIL 실거래가 일별 DTO

    특정 일의 거래 정보 리스트
    """

    model_config = ConfigDict(extra="allow")

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking field names (including extra fields)"""
        return key in self.model_dump()

    day: int | None = Field(default=None, description="거래 일")
    val: list[AsilTradePriceDetailDTO] | None = Field(
        default=None, description="거래 상세 정보 리스트"
    )


class AsilTradePriceMonthDTO(BaseModel):
    """ASIL 실거래가 월별 DTO

    특정 월의 거래 정보 리스트
    """

    model_config = ConfigDict(extra="allow")

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking field names (including extra fields)"""
        return key in self.model_dump()

    yyyymm: str | None = Field(default=None, description="거래 연월 (YYYYMM)")
    val: list[AsilTradePriceDayDTO] | None = Field(
        default=None, description="일별 거래 정보 리스트"
    )


class AsilTradePriceDTO(BaseModel):
    """ASIL 실거래가 DTO

    ASIL API의 apt_price_m2_mjw_newver_6.jsp 엔드포인트에서 반환하는 실거래가 데이터
    """

    model_config = ConfigDict(extra="allow")

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking field names (including extra fields)"""
        return key in self.model_dump()

    val: list[AsilTradePriceMonthDTO] | None = Field(
        default=None, description="월별 거래 정보 리스트"
    )
    price_total: str | None = Field(default=None, description="총 거래 건수")
    is_more: str | None = Field(default=None, description="추가 데이터 존재 여부")
    max_m: str | None = Field(default=None, description="최고 매매가")
    max_j: str | None = Field(default=None, description="최고 전세가")
    date_m: str | None = Field(default=None, description="최근 매매일 (YY.MM)")
    date_j: str | None = Field(default=None, description="최근 전세일 (YY.MM)")

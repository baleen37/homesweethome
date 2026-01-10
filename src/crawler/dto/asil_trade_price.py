"""ASIL 실거래가 DTO"""

from pydantic import BaseModel, Field


class AsilTradePriceDTO(BaseModel):
    """ASIL 실거래가 DTO

    ASIL API의 apt_price_m2_mjw_newver_6.jsp 엔드포인트에서 반환하는 실거래가 데이터
    """

    deal_year: str | None = Field(default=None, description="거래 연도")
    deal_month: str | None = Field(default=None, description="거래 월")
    deal_day: str | None = Field(default=None, description="거래 일")
    price: str | None = Field(default=None, description="거래 가격 (만원)")
    area_m2: str | None = Field(default=None, description="전용면적 (m²)")
    floor: str | None = Field(default=None, description="층")
    deal_type: str | None = Field(default=None, description="거래 유형 (매매/전세/월세)")
    build_year: str | None = Field(default=None, description="건축 연도")
    apt_name: str | None = Field(default=None, description="아파트 이름")
    apt_code: str | None = Field(default=None, description="아파트 코드")
    sido_code: str | None = Field(default=None, description="시도 코드")
    dong_code: str | None = Field(default=None, description="법정동 코드")
    dong_name: str | None = Field(default=None, description="법정동 이름")

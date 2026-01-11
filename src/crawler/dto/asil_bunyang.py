"""ASIL 분양 목록 DTO"""

from pydantic import BaseModel, Field


class AsilBunyangListDTO(BaseModel):
    """ASIL 분양 목록 DTO

    ASIL API의 data_bunyang_list.jsp 엔드포인트에서 반환하는 분양 아파트 목록 데이터
    """

    seq: str | None = Field(default=None, description="분양 고유 코드")
    name: str | None = Field(default=None, description="단지 이름")
    area: str | None = Field(default=None, description="지역 코드")
    area_name: str | None = Field(default=None, description="지역 이름")
    dong: str | None = Field(default=None, description="법정동 코드")
    dongname: str | None = Field(default=None, description="법정동 이름")
    address: str | None = Field(default=None, description="주소")
    supply_type: str | None = Field(default=None, description="공급 유형")
    supply_count: str | None = Field(default=None, description="공급 세대수")
    total_count: str | None = Field(default=None, description="전체 세대수")
    bunyang_date: str | None = Field(default=None, description="분양일")
    announcement_date: str | None = Field(default=None, description="공고일")
    movein_date: str | None = Field(default=None, description="입주일")
    min_price: str | None = Field(default=None, description="최소 가격")
    max_price: str | None = Field(default=None, description="최대 가격")
    min_area: str | None = Field(default=None, description="최소 면적")
    max_area: str | None = Field(default=None, description="최대 면적")
    status: str | None = Field(default=None, description="분양 상태")
    constructor: str | None = Field(default=None, description="시공사")
    seller: str | None = Field(default=None, description="주택유형")
    phone: str | None = Field(default=None, description="문의전화")
    lat: str | None = Field(default=None, description="위도")
    lng: str | None = Field(default=None, description="경도")
    detail_url: str | None = Field(default=None, description="상세 페이지 URL")

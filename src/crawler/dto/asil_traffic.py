"""ASIL 교통정보 DTO"""

from pydantic import BaseModel, Field


class AsilTrafficInfoDTO(BaseModel):
    """ASIL 교통정보 DTO

    ASIL API에서 반환하는 교통정보 데이터 (지하철, GTX 등)
    """

    key: str = Field(description="교통수단 고유 코드")
    title: str = Field(description="교통수단 이름 (예: GTX B)")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    s_year: str = Field(description="개시 연도")
    e_year: str = Field(description="종료 연도")

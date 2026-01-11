"""asil.kr 지도 검색 API DTO"""

from pydantic import BaseModel, Field


class AsilMapSearchDTO(BaseModel):
    """asil.kr aptcount_ver_5_9.jsp API 응답 DTO

    지도 영역 내 아파트 갯수와 위치 정보를 반환
    """

    apt_code: str = Field(alias="seq", description="아파트 고유 코드")
    apt_name: str = Field(alias="name", description="아파트 이름")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    count: str = Field(description="아파트 매물 갯수")
    deal_count: str = Field(default="", description="매매 갯수")
    jeonse_count: str = Field(default="", description="전세 갯수")
    wolse_count: str = Field(default="", description="월세 갯수")

"""ASIL 조회수 통계 DTO"""

from pydantic import BaseModel, Field


class AsilVisitorStatsDTO(BaseModel):
    """ASIL 조회수 통계 DTO

    ASIL API에서 반환하는 매물별 조회수 통계 데이터
    """

    key: str = Field(description="매물 고유 코드 (중개법인 ID)")
    company: str = Field(description="중개법인명")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    photo: str = Field(description="중개법인 사진 경로")

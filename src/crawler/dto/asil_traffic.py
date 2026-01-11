"""ASIL 교통정보 DTO"""

from pydantic import BaseModel, Field


class AsilTrafficStationDTO(BaseModel):
    """ASIL 교통정보 역 DTO"""

    key: str = Field(description="역 고유 코드")
    name: str = Field(description="역 이름")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    time: str = Field(default="", description="시간 정보")


class AsilTrafficInfoDTO(BaseModel):
    """ASIL 교통정보 DTO

    ASIL API에서 반환하는 교통정보 데이터 (지하철, GTX 등)
    """

    key: str = Field(description="교통수단 고유 코드")
    title: str = Field(description="교통수단 이름 (예: GTX D)")
    subtitle: str = Field(default="", description="부제목 (예: 1. 운행계획표)")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    zoom: str = Field(default="", description="줌 레벨")
    distance: str = Field(default="", description="거리")
    color: str = Field(default="", description="색상 코드")
    position: str = Field(default="", description="위치")
    updown: str = Field(default="", description="방향 (up/down)")
    lane: list[list[float]] = Field(default_factory=list, description="노선 좌표 배열")
    type: int = Field(default=1, description="교통 유형")
    station: list[AsilTrafficStationDTO] = Field(default_factory=list, description="역 정보 배열")
    # 기존 필드 호환성을 위해 기본값 추가 (API 응답에는 없음)
    s_year: str = Field(default="", description="개시 연도 (API 응답에 없음)")
    e_year: str = Field(default="", description="종료 연도 (API 응답에 없음)")

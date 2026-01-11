"""ASIL 재개발 단지 DTO"""

from pydantic import BaseModel, Field


class AsilRedevelopPolygonCoordinate(BaseModel):
    """ASIL 재개발 구역 폴리곤 좌표 DTO

    GeoJSON Polygon 형식의 좌표 데이터
    """

    coordinates: list[list[list[float]]] = Field(
        description="폴리곤 좌표 배열 (경도, 위도 순서의 3중 중첩 구조)"
    )


class AsilRedevelopDTO(BaseModel):
    """ASIL 재개발 단지 DTO

    ASIL API에서 반환하는 재개발/재건축 구역 정보
    """

    key: str = Field(description="재개발 구역 고유 코드 (PB + 숫자)")
    title: str = Field(description="재개발 구역명")
    desc: str = Field(description="사업시행자 정보 또는 구역 설명")
    lat: str = Field(description="중심 위도 좌표")
    lng: str = Field(description="중심 경도 좌표")
    evt: str = Field(description="이벤트 여부 (Y=있음, N=없음)")
    evt_title: str = Field(default="", description="이벤트 제목")
    polygon: list[AsilRedevelopPolygonCoordinate] = Field(
        description="GeoJSON 형식의 폴리곤 좌표 데이터"
    )

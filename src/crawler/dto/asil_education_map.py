"""ASIL 학군 지도 정보 DTO"""

from pydantic import BaseModel, Field


class AsilEducationMapPolygonCoordinate(BaseModel):
    """학군 지도 폴리곤 좌표"""

    coordinates: list[list[list[float]]] = Field(description="폴리곤 좌표 리스트 (경도, 위도 쌍)")


class AsilEducationMapDTO(BaseModel):
    """ASIL 학군 지도 정보

    Attributes:
        title: 학군 정보 제목 (예: "학원수 72개")
        lat: 위도
        lng: 경도
        polygon: GeoJSON 형식의 폴리곤 데이터
    """

    title: str = Field(description="학군 정보 제목")
    lat: str = Field(description="위도")
    lng: str = Field(description="경도")
    polygon: list[AsilEducationMapPolygonCoordinate] | None = Field(
        default=None, description="GeoJSON 형식의 폴리곤 데이터"
    )

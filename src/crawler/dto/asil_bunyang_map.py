"""ASIL 분양 지도 DTO"""

from pydantic import BaseModel


class AsilSiguInfoDTO(BaseModel):
    """시도 정보 DTO"""

    seq: str
    name: str
    fullname: str
    lat: str
    lng: str
    zoom: str
    subtitle: str


class AsilBunyangMapResponse(BaseModel):
    """분양 지도 응답 DTO"""

    sigu: list[AsilSiguInfoDTO]
    schedule: str
    progress: str
    done: str

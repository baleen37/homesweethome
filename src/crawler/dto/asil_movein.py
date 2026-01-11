"""ASIL 입주 예정 물량 DTO"""

from pydantic import BaseModel


class AsilMoveinDTO(BaseModel):
    """ASIL 입주 예정 물량 데이터 모델

    ASIL API에서 반환하는 입주 예정 아파트 물량 정보
    """

    seq: str  # 고유 시퀀스 ID (아파트 코드)
    name: str  # 건물명
    location: str  # 위치 (지역 주소)
    movein_yyyymm: str  # 입주 예정년월 (YYYYMM 형식)
    household: str  # 세대수
    lat: str  # 위도
    lng: str  # 경도

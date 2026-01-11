"""ASIL 아파트 순위 DTO"""

from pydantic import BaseModel


class AsilRankingDTO(BaseModel):
    """ASIL 아파트 순위 데이터 모델"""

    idx: str  # 순위 인덱스
    seq: str  # 고유 시퀀스 ID (아파트 코드)
    name: str  # 건물명
    movein: str  # 입주년도
    lat: str  # 위도
    lng: str  # 경도
    price: str  # 가격 (예: "290억")
    yyyymm: str  # 년월 (예: "25년6월")
    m2: str  # 면적 (평, 예: "104평")
    floor: str  # 층 (예: "47층")
    addr: str  # 주소

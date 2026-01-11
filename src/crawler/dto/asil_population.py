"""ASIL 인구 통계 DTO"""

from pydantic import BaseModel


class AsilPopulationDTO(BaseModel):
    """ASIL 인구 통계 데이터 모델"""

    seq: str  # 지역 코드 (11=서울, 5자리=구)
    name: str  # 지역명
    v1: str  # 인구값 1 (포맷: "9,390,925명")
    v2: str  # 인구값 2 (포맷: "9,335,495명")
    v3: str  # 인구값 3 (포맷: "9,305,678명")
    v2_gap: str  # v1-v2 차이 (포맷: "55,430명")
    v3_gap: str  # v2-v3 차이 (포맷: "29,817명")
    v2_icon: str  # v2 추세 아이콘 ("up", "down")
    v3_icon: str  # v3 추세 아이콘 ("up", "down")

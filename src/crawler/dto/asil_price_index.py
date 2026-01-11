"""ASIL 가격 지수 DTO"""

from pydantic import BaseModel


class AsilPriceIndexRegionDTO(BaseModel):
    """지역 아파트 가격 지수 데이터"""

    seq: str  # 지역 코드
    name: str  # 지역명
    v1: str  # 기준 지수값
    v2: str  # 현재/1기 지수값
    v3: str  # 이전/2기 지수값
    v2_gap: str  # v2와 v1의 차이
    v3_gap: str  # v3와 v2의 차이
    v2_icon: str  # v2 추세 아이콘 (up, down 또는 빈 문자열)
    v3_icon: str  # v3 추세 아이콘 (up, down 또는 빈 문자열)


class AsilPriceIndexSummaryDTO(BaseModel):
    """가격 지수 요약 데이터 (배열의 마지막 항목)"""

    min: str  # 최소 차이값
    max: str  # 최대 차이값


AsilPriceIndexResponse = AsilPriceIndexRegionDTO | AsilPriceIndexSummaryDTO

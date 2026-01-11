"""ASIL 인구 유동 DTO"""

from pydantic import BaseModel, Field


class AsilTransferDTO(BaseModel):
    """ASIL 인구 유동 데이터 모델"""

    rank: int = Field(..., description="순위")
    from_: str = Field(..., alias="from", description="출발 지역")
    to: str = Field(..., description="도착 지역")
    total: str = Field(..., description='전체 이동 수 (포맷: "2,891")')
    value: str = Field(..., description='이동 수 (포맷: "451")')
    color: str = Field(..., description="색상 코드 (보통 빈 문자열)")

"""ASIL 동/호 정보 DTO"""

from pydantic import BaseModel, Field


class AsilDongInfoDTO(BaseModel):
    """ASIL 아파트 동/호 정보 DTO

    ASIL API의 data_apt_dong.jsp 엔드포인트에서 반환하는 동 정보
    """

    dong: str = Field(description="동 번호 (예: '101' = 101동)")

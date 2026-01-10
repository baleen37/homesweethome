"""ASIL 학교정보 DTO"""

from pydantic import BaseModel, Field


class AsilSchoolInfoDTO(BaseModel):
    """ASIL 학교정보 DTO

    ASIL API에서 반환하는 학교 정보 데이터
    """

    seq: str = Field(description="학교 고유 코드")
    name: str = Field(description="학교 전체 이름")
    name2: str = Field(description="학교 약어 (예: 경희초)")
    addr: str = Field(description="학교 주소")

"""ASIL 중개사 DTO"""

from pydantic import BaseModel, Field


class AsilAgentDTO(BaseModel):
    """ASIL 중개사 정보 모델"""

    seq: str  # 중개사 시퀀스 ID
    company: str  # 회사명
    name: str  # 중개사 이름
    tel: str  # 휴대폰 번호
    cel: str  # 사무실 전화번호
    addr: str  # 주소
    biz_no: str = Field(..., alias="bizNo")  # 사업자등록번호
    lat: str  # 위도
    lng: str  # 경도
    photo: str  # 사진 경로

    model_config = {"populate_by_name": True}


class AsilAgentInfoResponse(BaseModel):
    """ASIL 중개사 정보 응답 모델"""

    result: bool  # 성공 여부
    agent: AsilAgentDTO  # 중개사 정보

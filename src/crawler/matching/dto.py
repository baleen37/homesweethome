"""매칭 결과 DTO"""

from enum import Enum

from pydantic import BaseModel, Field


class MatchMethod(str, Enum):
    """매칭 방법"""

    DIRECT_ID = "direct_id"  # ASIL의 naver_uid로 직접 매칭
    COORDINATE = "coordinate"  # 좌표 기반 매칭
    FUZZY_NAME = "fuzzy_name"  # 퍼지 이름 매칭
    NO_MATCH = "no_match"  # 매칭 실패


class MatchResultDTO(BaseModel):
    """ASIL-Naver 매칭 결과"""

    asil_apt_code: str = Field(description="ASIL 아파트 코드 (mm_uid)")
    asil_apt_name: str = Field(description="ASIL 아파트 이름")
    naver_apt_code: str | None = Field(default=None, description="Naver 아파트 코드")
    naver_apt_name: str | None = Field(default=None, description="Naver 아파트 이름")
    confidence: float = Field(description="매칭 신뢰도 (0.0-1.0)")
    method: MatchMethod = Field(description="매칭 방법")
    distance_m: float | None = Field(default=None, description="거리 (미터, 좌표 매칭 시)")

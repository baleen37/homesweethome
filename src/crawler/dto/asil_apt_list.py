"""ASIL 아파트 목록 DTO"""

from pydantic import BaseModel, Field

from crawler.constants import get_gu_name


class AsilAptListDTO(BaseModel):
    """ASIL 아파트 목록 DTO

    ASIL API의 data_apt_list.jsp 엔드포인트에서 반환하는 아파트 목록 데이터
    """

    seq: str = Field(description="아파트 고유 코드")
    name: str = Field(description="아파트 이름")
    dong: str = Field(description="법정동 코드")
    dongname: str = Field(description="법정동 이름")
    bungi: str | None = Field(default=None, description="번지 주소")
    build_year: str | None = Field(default=None, alias="movein", description="건축 연도")
    household: str | None = Field(default=None, description="세대수")
    dong_count: str | None = Field(default=None, alias="total_dong", description="동 수")
    address: str | None = Field(default=None, description="주소")
    maemul_count: str | None = Field(default=None, description="매물 수")
    offer: str | None = Field(default=None, description="매물 정보")
    lat: str | None = Field(default=None, description="위도")
    lng: str | None = Field(default=None, description="경도")

    @property
    def gu_name(self) -> str | None:
        """구 이름

        법정동 코드 앞 5자리에서 구 코드를 추출하여 구 이름을 반환합니다.
        """
        gu_code = self.dong[:5]
        return get_gu_name(gu_code)

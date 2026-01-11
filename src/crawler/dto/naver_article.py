"""네이버 부동산 매물 Article DTO

jissp/naver-land-crawler ArticleItem 기반 DTO 모델입니다.
"""

from pydantic import BaseModel, Field


class NaverArticleItemDTO(BaseModel):
    """Cluster API 매물 아이템"""

    atcl_no: str = Field(description="매물번호")
    cortar_no: str = Field(description="법정동코드")
    atcl_nm: str = Field(description="매물명")
    atcl_stat_cd: str = Field(description="매물상태코드")
    rlet_tp_cd: str = Field(description="부동산유형코드 (A01=아파트, A02=오피스텔)")
    rlet_tp_nm: str = Field(description="부동산유형명")
    trad_tp_cd: str = Field(description="거래유형코드 (A1=매매, B1=전세, B2=월세)")
    trad_tp_nm: str = Field(description="거래유형명")
    prc: int | None = Field(default=None, description="매매가/보증금 (만원)")
    rent_prc: int | None = Field(default=None, description="월세 (만원)")
    flr_info: str = Field(default="", description="층정보")
    spc1: str = Field(default="", description="공급면적 (㎡)")
    spc2: str = Field(default="", description="전용면적 (㎡)")
    direction: str | None = Field(default=None, description="향")
    atcl_cfm_ymd: str | None = Field(default=None, description="확인일자")
    lat: float | None = Field(default=None, description="위도")
    lng: float | None = Field(default=None, description="경도")
    atcl_fetr_desc: str = Field(default="", description="매물설명")
    tag_list: list[str] = Field(default_factory=list, description="태그 리스트")
    bild_nm: str = Field(default="", description="동명")
    apt_seq: str | None = Field(default=None, description="아파트 고유 코드")


class NaverArticleKeyDTO(BaseModel):
    """매물 연관 키 (Front API)"""

    complex_number: int | None = Field(default=None, description="단지번호")
    pyeong_type_number: int | None = Field(default=None, description="평형번호")
    building_number: int | None = Field(default=None, description="동번호")
    ho_number: int | None = Field(default=None, description="호번호")
    real_estate_type: str = Field(default="", description="부동산유형")
    trade_type: str = Field(default="", description="거래유형")


class NaverArticleDetailDTO(BaseModel):
    """매물 상세 정보 (Front API)"""

    price_info: dict | None = Field(default=None, description="가격 정보")
    detail_info: dict | None = Field(default=None, description="상세 정보")
    space_info: dict | None = Field(default=None, description="공간 정보")
    size_info: dict | None = Field(default=None, description="면적 정보")


class NaverComplexDTO(BaseModel):
    """단지 정보"""

    complex_number: int = Field(description="단지번호")
    complex_name: str = Field(description="단지이름")
    address: str = Field(description="주소")
    total_household_number: int = Field(description="총세대수")
    construction_company: str = Field(description="시공사")
    approval_elapsed_year: int | None = Field(default=None, description="준입경과년차")

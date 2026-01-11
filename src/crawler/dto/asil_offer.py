"""ASIL 매물 DTO"""

from pydantic import BaseModel, Field


class AsilOfferDTO(BaseModel):
    """ASIL 매물 데이터 모델"""

    # 기본 정보
    mm_uid: str = Field(..., description="매물 고유 ID")
    RLSTTYPE_CD: str = Field(..., description="부동산 유형 코드 (A01=아파트)")
    RLSTTYPE_NM: str = Field(..., description="부동산 유형명")
    BLDNM: str = Field(..., description="건물명")
    DEALTYPE_CD: str = Field(..., description="거래유형코드 (A01=매매, B01=전세, B02=월세)")
    DEALTYPE_NM: str = Field(..., description="거래유형명")

    # 위치 정보
    MAP_X: str = Field(..., description="X 좌표 (경도)")
    MAP_Y: str = Field(..., description="Y 좌표 (위도)")
    CITY_NM: str = Field(..., description="시명")
    GUN_NM: str = Field(..., description="구명")
    BDONG_NM: str = Field(..., description="법정동명")
    DONG_NM: str = Field(..., description="동 번호")

    # 면적 정보
    SPLY_SPC: str = Field(..., description="공급면적 (㎡)")
    EXCLS_SPC: str = Field(..., description="전용면적 (㎡)")
    CTRT_SPC: str = Field(..., description="계약면적 (㎡)")
    spc_v1: str = Field(..., description="면적 변수1")
    spc_v2: str = Field(..., description="면적 변수2")
    grnd_spc: str = Field(..., description="대지면적")
    TOT_SPC: str = Field(..., description="총 면적")
    CNST_SPC: str = Field(..., description="건축면적")

    # 층수 정보
    TOT_FLR_CNT: str = Field(..., description="총 층수")
    CORES_FLR_CNT: str = Field(..., description="해당 층수")
    CORES_FLR_CNT_NM: str = Field(..., description="층수 표기명 (저/고/층수)")
    UNDER_FLR: str = Field(..., description="지하층 여부")
    flr_dp_mthd_cd: str = Field(..., description="층 표기 방법 코드")

    # 가격 정보
    DEAL_AMT: str = Field(..., description="매매가 (만원)")
    WRRNT_AMT: str = Field(..., description="보증금/전세금 (만원)")
    LEASE_AMT: str = Field(..., description="월세 (만원)")
    premium_price: str = Field(..., description="프리미엄 가격")
    prcl_price: str = Field(..., description="평당 가격")

    # 상세 정보
    FETR_DESC: str = Field(..., description="특징 설명")
    PHTO_PATH: str = Field(..., description="사진 경로")
    SVC_DATE_STRT: str = Field(..., description="서비스 시작일 (YY.MM.DD)")

    # 중개사 정보
    BRKG_NM: str = Field(..., description="중개업소명")
    BRKG_TEL: str = Field(..., description="중개업소 전화번호")
    PRTN_UID: str = Field(..., description="파트너 UID")

    # 기타 정보
    SUB_RLSTTYPE_CD: str = Field(..., description="세부 부동산 유형코드")
    SUB_RLSTTYPE_NM: str = Field(..., description="세부 부동산 유형명")
    PRCS_CD: str = Field(..., description="진행상태코드")
    MAP_LOC_YN: str = Field(..., description="지도 위치 여부")
    pre_flag: str = Field(..., description="프리미엄 플래그")
    f_option: str = Field(..., description="옵션 플래그")
    f_push: str = Field(..., description="푸시 플래그")
    user_id: str = Field(..., description="사용자 ID")

    # 페이지네이션
    now_page: str = Field(..., description="현재 페이지 번호")
    next_flag: str | None = Field(None, description="다음 페이지 존재 여부")


class AsilOffersListResponse(BaseModel):
    """ASIL 매물 목록 응답 모델"""

    list_result: list[AsilOfferDTO]

"""ASIL 매물 상세 DTO"""

# ruff: noqa: N815 - API 필드명이 camelCase인 경우가 많음 (실제 응답과 일치해야 함)

from pydantic import BaseModel, Field


class AsilOfferDetailDTO(BaseModel):  # noqa: N815
    """ASIL 매물 상세 정보 DTO"""

    # 기본 정보
    mm_uid: str = Field(..., description="매물 고유 ID")
    RLSTTYPE_CD: str = Field(..., description="부동산 유형 코드")
    RLSTTYPE_NM: str = Field(..., description="부동산 유형명")
    SUB_RLSTTYPE_CD: str = Field(default="", description="세부 부동산 유형 코드")
    SUB_RLSTTYPE_NM: str = Field(default="", description="세부 부동산 유형명")
    DEALTYPE_CD: str = Field(..., description="거래 유형 코드")
    DEALTYPE_NM: str = Field(..., description="거래 유형명")

    # 건물 정보
    BLDNM: str = Field(..., description="건물명")
    DONG_NM: str = Field(default="", description="동 번호")
    PRD_TOT_BLD_CNT: str = Field(default="", description="총 건물 동 수")
    TOT_FML_CNT: str = Field(default="", description="총 세대수")
    CNST_DATE: str = Field(default="", description="사용 승인일")

    # 층/방 정보
    flr_1_val: str = Field(default="", description="층 구분 (저/고/중)")
    flr_2_val: str = Field(default="", description="해당 층")
    TOT_FLR_CNT: str = Field(default="", description="총 층수")
    RM_CNT: str = Field(default="", description="방 개수")
    BTRM_CNT: str = Field(default="", description="화장실 개수")

    # 방향/구조
    directionBase_nm: str = Field(default="", description="방향 기준")
    DRCTN_TP_NM: str = Field(default="", description="방향 타입")

    # 난방/입주
    HEAT_MTD_CD: str = Field(default="", description="난방 방식 코드")
    HEAT_MTD_NM: str = Field(default="", description="난방 방식명")
    HEAT_FUL_CD: str = Field(default="", description="난방 연료 코드")
    HEAT_FUL_NM: str = Field(default="", description="난방 연료명")
    MVIN_PSBL_NM: str = Field(default="", description="입주 가능 일자")

    # 주차/기타
    prkg_cnt: str = Field(default="", description="총 주차 대수")
    perprkg_cnt: str = Field(default="", description="세대당 주차 대수")
    park_yn_dp: str = Field(default="", description="주차 여부")

    # 가격 정보
    DEAL_AMT: str = Field(default="", description="매매가")
    WRRNT_AMT: str = Field(default="", description="전세가")
    LEASE_AMT: str = Field(default="", description="월세 보증금")
    premium_price2: str = Field(default="", description="권리금")
    middle_payment: str = Field(default="", description="중도금")
    optionPrice: str = Field(default="", description="옵션가")

    # 면적 정보
    spc1: str = Field(default="", description="공급면적")
    spc2: str = Field(default="", description="전용면적")
    spc1_1: str = Field(default="", description="공급면적(평)")
    spc2_1: str = Field(default="", description="전용면적(평)")

    # 주소/위치
    mm_adr: str = Field(default="", description="매물 주소")
    MAP_X: str = Field(default="", description="위도")
    MAP_Y: str = Field(default="", description="경도")

    # 설명
    FETR_DESC: str = Field(default="", description="특징 설명")
    DTL_DESC: str = Field(default="", description="상세 설명")

    # 관리비
    MTNC_AMT: str = Field(default="", description="관리비")

    # 기타
    FNC_AMT: str = Field(default="", description="융자금")
    ERTC_TYPE_NM: str = Field(default="", description="기타 유형")
    SALES_TYPE_NM: str = Field(default="", description="판매 유형")
    PRD_CSCO_NM: str = Field(default="", description="물건 범위")
    mnexItems_val: str = Field(default="", description="기타 항목")
    AL_WRRNT_AMT: str = Field(default="", description="즉시 전세가")
    AL_LEASE_AMT: str = Field(default="", description="즉시 월세보증금")
    bldtype_nm: str = Field(default="", description="건물 유형명")
    CURR_USGE_CONT: str = Field(default="", description="현재 사용 내용")
    JIMOK_NM: str = Field(default="", description="지목명")
    RCMD_USGE_CONT: str = Field(default="", description="권장 사용 내용")
    USGE_AREA_NM: str = Field(default="", description="사용 면적명")
    land_yn_dp: str = Field(default="", description="토지 여부")
    build_yn_dp: str = Field(default="", description="건물 여부")
    road_yn_dp: str = Field(default="", description="도로 여부")
    RGHT_AMT: str = Field(default="", description="권리 금액")
    USE_PSBL_POWR: str = Field(default="", description="사용 가능 전력")
    ex_meter: str = Field(default="", description="전기 계량기")
    lawUsageCode_nm: str = Field(default="", description="법적 사용 코드명")

    # 서비스 정보
    SVC_DATE_STRT: str = Field(default="", description="서비스 시작일")
    SVC_DATE_END: str = Field(default="", description="서비스 종료일")

    # 중개사 정보
    user_id: str = Field(default="", description="중개사 ID")

    # 건물 코드
    asil_bldcode: str = Field(default="", description="ASIL 건물 코드")
    bldcode: str = Field(default="", description="건물 코드")
    hscp_no: str = Field(default="", description="사업장 번호")

    # 기타 코드
    MAP_LOC_YN: str = Field(default="", description="지도 위치 여부")
    PRCS_CD: str = Field(default="", description="진행 코드")
    org_ptp_nm: str = Field(default="", description="원본 평형명")
    naver_uid: str = Field(default="", description="네이버 UID")
    loanCode: str = Field(default="", description="대출 코드")
    vr_flag: str = Field(default="", description="VR 플래그")
    naver_status: str = Field(default="", description="네이버 상태")

    # 기SO 정보
    kiso_mm_uid: str = Field(default="", description="기SO 매물 UID")
    kiso_bizNo: str = Field(default="", description="기SO 사업자번호")
    kiso_rname: str = Field(default="", description="기SO 중개사명")
    kiso_rphone: str = Field(default="", description="기SO 연락처")
    kiso_raddr: str = Field(default="", description="기SO 주소")
    kiso_address1: str = Field(default="", description="기SO 주소1")
    kiso_address2: str = Field(default="", description="기SO 주소2")
    kiso_atclName: str = Field(default="", description="기SO 매물명")
    kiso_atclType: str = Field(default="", description="기SO 매물유형")
    kiso_tradeType: str = Field(default="", description="기SO 거래유형")
    kiso_atclExpsYmdt: str = Field(default="", description="기SO 노출일시")
    kiso_price: str = Field(default="", description="기SO 가격")
    kiso_space: str = Field(default="", description="기SO 면적")


class AsilOfferDetailOptionDTO(BaseModel):
    """ASIL 매물 상세 옵션 DTO"""

    option_code: str = Field(default="", description="옵션 코드")
    option_name: str = Field(default="", description="옵션명")


class AsilOfferDetailImageDTO(BaseModel):
    """ASIL 매물 상세 이미지 DTO"""

    image_url: str = Field(default="", description="이미지 URL")
    image_type: str = Field(default="", description="이미지 타입")


class AsilOfferDetailAdminCostDTO(BaseModel):
    """ASIL 매물 상세 관리비 DTO"""

    chargeCodeType: str = Field(default="", description="부과 코드 타입")
    chargeCodeType_nm: str = Field(default="", description="부과 코드 타입명")
    chargeCriteriaCode: str = Field(default="", description="부과 기준 코드")
    chargeCriteriaCode_nm: str = Field(default="", description="부과 기준 코드명")
    etcFeeDetails: dict | None = Field(default=None, description="기타 요금 상세")


class AsilOfferDetailRelatedDTO(BaseModel):
    """ASIL 매물 상세 관련 매물 DTO"""

    mm_uid: str = Field(..., description="매물 고유 ID")
    RLSTTYPE_CD: str = Field(..., description="부동산 유형 코드")
    RLSTTYPE_NM: str = Field(..., description="부동산 유형명")
    BLDNM: str = Field(..., description="건물명")
    DEALTYPE_CD: str = Field(..., description="거래 유형 코드")
    DEALTYPE_NM: str = Field(..., description="거래 유형명")
    MAP_X: str = Field(default="", description="위도")
    MAP_Y: str = Field(default="", description="경도")
    BDONG_NM: str = Field(default="", description="동 번호")
    SPLY_SPC: str = Field(default="", description="공급면적")
    EXCLS_SPC: str = Field(default="", description="전용면적")
    TOT_FLR_CNT: str = Field(default="", description="총 층수")
    CORES_FLR_CNT: str = Field(default="", description="해당 층")
    CORES_FLR_CNT_NM: str = Field(default="", description="해당 층명")
    FETR_DESC: str = Field(default="", description="특징 설명")
    DEAL_AMT: str = Field(default="", description="매매가")
    WRRNT_AMT: str = Field(default="", description="전세가")
    LEASE_AMT: str = Field(default="", description="월세 보증금")
    SUB_RLSTTYPE_NM: str = Field(default="", description="세부 부동산 유형명")
    PHTO_PATH: str = Field(default="", description="사진 경로")
    MM_IDX: str = Field(default="", description="매물 인덱스")
    SVC_DATE_STRT: str = Field(default="", description="서비스 시작일")
    BRKG_NM: str = Field(default="", description="중개사명")
    premium_price: str = Field(default="", description="프리미엄 가격")
    prcl_price: str = Field(default="", description="평당 가격")
    TOT_CNT: str = Field(default="", description="총 개수")
    spc_v1: str = Field(default="", description="면적 v1")
    spc_v2: str = Field(default="", description="면적 v2")
    spc_py_v1: str = Field(default="", description="면적(평) v1")
    spc_py_v2: str = Field(default="", description="면적(평) v2")
    PHTO_CNT: str = Field(default="", description="사진 개수")
    PRTN_IMG: str = Field(default="", description="파트너 이미지")
    f_option: str = Field(default="", description="옵션 플래그")
    f_push: str = Field(default="", description="푸시 플래그")
    city_nm: str = Field(default="", description="시명")
    gun_nm: str = Field(default="", description="군/구명")
    gu_nm: str = Field(default="", description="구명")
    bdong_nm: str = Field(default="", description="법정동명")
    FLR_DP_MTHD_CD: str = Field(default="", description="층 표시 방법 코드")
    optionPrice: str = Field(default="", description="옵션가")
    CTRT_SPC: str = Field(default="", description="계약면적")
    CNST_SPC: str = Field(default="", description="건축면적")
    grnd_spc: str = Field(default="", description="대지면적")
    TOT_SPC: str = Field(default="", description="총면적")
    SUB_RLSTTYPE_CD: str = Field(default="", description="세부 부동산 유형 코드")
    MAP_LOC_YN: str = Field(default="", description="지도 위치 여부")
    next_flag: bool = Field(default=False, description="다음 플래그")


class AsilOfferDetailResponse(BaseModel):
    """ASIL 매물 상세 응답 DTO"""

    mm_json: list[AsilOfferDetailDTO] = Field(default_factory=list, description="매물 상세 정보")
    builttin_option: list[AsilOfferDetailOptionDTO] = Field(
        default_factory=list, description="내장 옵션"
    )
    mm_img_list: list[AsilOfferDetailImageDTO] = Field(
        default_factory=list, description="이미지 리스트"
    )
    administrationCostInfo: AsilOfferDetailAdminCostDTO | None = Field(
        default=None, description="관리비 정보"
    )
    mm_json_list: list[AsilOfferDetailRelatedDTO] = Field(
        default_factory=list, description="관련 매물 리스트"
    )

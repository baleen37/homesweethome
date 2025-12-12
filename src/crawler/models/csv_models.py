"""Type-safe data classes for CSV output

These data classes ensure consistent structure and type safety for CSV exports,
preventing issues like missing fields, incorrect field order, and type errors.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .api_responses import ComplexInfo, POIInfo, RankingInfo


# Trade type constants
class TradeType:
    SALE = "A1"
    SALE_NAME = "매매"
    JEONSE = "B1"
    JEONSE_NAME = "전세"
    MONTHLY = "B2"
    MONTHLY_NAME = "월세"


@dataclass
class ComplexCSVRow:
    """CSV row format for complexes.csv

    Enhanced with POI type information and validation fields
    to better handle Hogangnono API responses.
    """

    단지ID: str
    단지명: str
    주소: str = ""
    위도: Optional[float] = None
    경도: Optional[float] = None
    건축년도: int = 0
    세대수: int = 0
    층수: int = 0
    승강기수: Optional[int] = None
    주차대수: Optional[int] = None
    난방방식: Optional[str] = None
    연면적: Optional[float] = None
    대지면적: Optional[float] = None
    구코드: Optional[str] = None
    동코드: Optional[str] = None
    구이름: Optional[str] = None
    동이름: Optional[str] = None

    # New fields for POI type and validation
    POI_유형: Optional[str] = None  # POI type from POICategory enum
    POI_분류: str = ""  # "아파트", "지하철역", "병원", "마트" etc.
    유효성_검증_결과: str = ""  # "VALID", "INVALID_APARTMENT_ID", "IS_TRANSIT", etc.
    유효성_검증_사유: str = ""  # Detailed reason for validation result
    데이터_소스: str = "HOGANGNONO"  # Source of the data

    @classmethod
    def from_complex_info(cls, complex: ComplexInfo) -> "ComplexCSVRow":
        """Create CSV row from ComplexInfo"""
        return cls(
            단지ID=complex.id,
            단지명=complex.name,
            주소=complex.address,
            위도=complex.latitude,
            경도=complex.longitude,
            건축년도=complex.build_year or 0,
            세대수=complex.households or 0,
            층수=complex.floors or 0,
            승강기수=complex.elevator_count,
            주차대수=complex.parking_count,
            난방방식=complex.heating_type,
            연면적=complex.total_floor_area,
            대지면적=complex.total_site_area,
            구코드=complex.gu_code,
            동코드=complex.dong_code,
            구이름=complex.gu_name,
            동이름=complex.dong_name,
            # POI type fields will be set by from_poi_info method
        )

    @classmethod
    def from_poi_info(
        cls, poi: POIInfo, validation_result: str = "", validation_reason: str = ""
    ) -> "ComplexCSVRow":
        """Create CSV row from POIInfo with validation information

        Args:
            poi: POI information from API response
            validation_result: Result of validation (VALID, INVALID, etc.)
            validation_reason: Detailed reason for validation result
        """
        # Determine POI classification
        poi_classification = ""
        if poi.is_apartment():
            poi_classification = "아파트"
        elif poi.is_transit():
            poi_classification = "대중교통"
        elif poi.is_facility():
            poi_classification = "공공시설"
        elif poi.is_education():
            poi_classification = "교육시설"
        else:
            poi_classification = "기타"

        return cls(
            단지ID=str(poi.id),
            단지명=poi.name,
            주소=poi.address or "",
            위도=poi.lat,
            경도=poi.lng,
            건축년도=int(poi.build_date[:4]) if poi.build_date and poi.build_date.isdigit() else 0,
            세대수=poi.households or 0,
            층수=poi.floors or 0,
            승강기수=poi.elevator_count,
            주차대수=poi.parking_count,
            난방방식=poi.heating_type,
            연면적=poi.total_floor_area,
            대지면적=poi.total_site_area,
            구코드=poi.region1,
            동코드=poi.region2,
            구이름="",
            동이름="",
            # New POI fields
            POI_유형=poi.category.value if poi.category else None,
            POI_분류=poi_classification,
            유효성_검증_결과=validation_result,
            유효성_검증_사유=validation_reason,
            데이터_소스="HOGANGNONO",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing"""
        return {
            "단지ID": self.단지ID,
            "단지명": self.단지명,
            "주소": self.주소,
            "위도": self.위도,
            "경도": self.경도,
            "건축년도": self.건축년도,
            "세대수": self.세대수,
            "층수": self.층수,
            "승강기수": self.승강기수,
            "주차대수": self.주차대수,
            "난방방식": self.난방방식,
            "연면적": self.연면적,
            "대지면적": self.대지면적,
            "구코드": self.구코드,
            "동코드": self.동코드,
            "구이름": self.구이름,
            "동이름": self.동이름,
            # New POI fields
            "POI_유형": self.POI_유형,
            "POI_분류": self.POI_분류,
            "유효성_검증_결과": self.유효성_검증_결과,
            "유효성_검증_사유": self.유효성_검증_사유,
            "데이터_소스": self.데이터_소스,
        }

    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get the field names for CSV header"""
        return [
            "단지ID",
            "단지명",
            "주소",
            "위도",
            "경도",
            "건축년도",
            "세대수",
            "층수",
            "승강기수",
            "주차대수",
            "난방방식",
            "연면적",
            "대지면적",
            "구코드",
            "동코드",
            "구이름",
            "동이름",
            # New POI fields
            "POI_유형",
            "POI_분류",
            "유효성_검증_결과",
            "유효성_검증_사유",
            "데이터_소스",
        ]


@dataclass
class TransactionCSVRow:
    """CSV row format for transactions.csv"""

    단지ID: str
    단지명: str
    평형번호: int = 0
    평형이름: str = ""
    거래유형: str = ""
    거래유형명: str = ""
    거래일: Optional[str] = None
    거래년도: int = 0
    층: str = ""
    매매가: int = 0
    전세가: int = 0
    월세: int = 0
    거래구분: str = ""
    삭제여부: str = "N"
    갱신여부: str = "N"

    @classmethod
    def from_complex_info(cls, complex: ComplexInfo) -> List["TransactionCSVRow"]:
        """Create transaction rows from ComplexInfo"""
        rows = []

        if complex.trade_info:
            # Convert trade type
            trade_type = complex.trade_info.trade_type
            if trade_type == "sale":
                trade_type_code = TradeType.SALE
                trade_type_name = TradeType.SALE_NAME
            elif trade_type == "jeonse":
                trade_type_code = TradeType.JEONSE
                trade_type_name = TradeType.JEONSE_NAME
            elif trade_type == "monthly":
                trade_type_code = TradeType.MONTHLY
                trade_type_name = TradeType.MONTHLY_NAME
            else:
                trade_type_code = TradeType.SALE
                trade_type_name = TradeType.SALE_NAME

            # Calculate pyeong area
            pyeong_type_number = 0
            pyeong_name = ""
            if complex.trade_info.exclusive_area:
                from .validators import SQM_TO_PYEONG_RATIO

                pyeong = complex.trade_info.exclusive_area / SQM_TO_PYEONG_RATIO
                pyeong_type_number = round(pyeong)
                pyeong_name = f"{pyeong_type_number}평형"

            # Extract trade year
            trade_year = 0
            if complex.trade_info.trade_date and len(complex.trade_info.trade_date) >= 4:
                year_str = complex.trade_info.trade_date[:4]
                if year_str.isdigit():
                    trade_year = int(year_str)

            row = cls(
                단지ID=complex.id,
                단지명=complex.name,
                평형번호=pyeong_type_number,
                평형이름=pyeong_name,
                거래유형=trade_type_code,
                거래유형명=trade_type_name,
                거래일=complex.trade_info.trade_date,
                거래년도=trade_year,
                층=complex.trade_info.floor or "",
                매매가=complex.trade_info.price or 0,
                전세가=complex.trade_info.deposit or 0,
                월세=complex.trade_info.monthly_rent or 0,
                거래구분=trade_type,
            )
            rows.append(row)

        return rows

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing"""
        return {
            "단지ID": self.단지ID,
            "단지명": self.단지명,
            "평형번호": self.평형번호,
            "평형이름": self.평형이름,
            "거래유형": self.거래유형,
            "거래유형명": self.거래유형명,
            "거래일": self.거래일,
            "거래년도": self.거래년도,
            "층": self.층,
            "매매가": self.매매가,
            "전세가": self.전세가,
            "월세": self.월세,
            "거래구분": self.거래구분,
            "삭제여부": self.삭제여부,
            "갱신여부": self.갱신여부,
        }

    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get the field names for CSV header"""
        return [
            "단지ID",
            "단지명",
            "평형번호",
            "평형이름",
            "거래유형",
            "거래유형명",
            "거래일",
            "거래년도",
            "층",
            "매매가",
            "전세가",
            "월세",
            "거래구분",
            "삭제여부",
            "갱신여부",
        ]


@dataclass
class POICSVRow:
    """CSV row format for POI data"""

    POI_ID: str
    명칭: str
    위도: Optional[float] = None
    경도: Optional[float] = None
    유형: Optional[str] = None
    시도코드: Optional[str] = None
    시군구코드: Optional[str] = None
    법정동코드: Optional[str] = None
    주소: Optional[str] = None
    건축년도: Optional[str] = None
    세대수: Optional[int] = None
    층수: Optional[int] = None
    승강기수: Optional[int] = None
    주차대수: Optional[int] = None
    난방방식: Optional[str] = None
    연면적: Optional[float] = None
    대지면적: Optional[float] = None

    @classmethod
    def from_poi_info(cls, poi: POIInfo) -> "POICSVRow":
        """Create CSV row from POIInfo"""
        return cls(
            POI_ID=str(poi.id),
            명칭=poi.name,
            위도=poi.lat,
            경도=poi.lng,
            유형=poi.type,
            시도코드=poi.region1,
            시군구코드=poi.region2,
            법정동코드=poi.region3,
            주소=poi.address,
            건축년도=poi.build_date,
            세대수=poi.households,
            층수=poi.floors,
            승강기수=poi.elevator_count,
            주차대수=poi.parking_count,
            난방방식=poi.heating_type,
            연면적=poi.total_floor_area,
            대지면적=poi.total_site_area,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing"""
        return {
            "POI_ID": self.POI_ID,
            "명칭": self.명칭,
            "위도": self.위도,
            "경도": self.경도,
            "유형": self.유형,
            "시도코드": self.시도코드,
            "시군구코드": self.시군구코드,
            "법정동코드": self.법정동코드,
            "주소": self.주소,
            "건축년도": self.건축년도,
            "세대수": self.세대수,
            "층수": self.층수,
            "승강기수": self.승강기수,
            "주차대수": self.주차대수,
            "난방방식": self.난방방식,
            "연면적": self.연면적,
            "대지면적": self.대지면적,
        }

    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get the field names for CSV header"""
        return [
            "POI_ID",
            "명칭",
            "위도",
            "경도",
            "유형",
            "시도코드",
            "시군구코드",
            "법정동코드",
            "주소",
            "건축년도",
            "세대수",
            "층수",
            "승강기수",
            "주차대수",
            "난방방식",
            "연면적",
            "대지면적",
        ]


@dataclass
class RankingCSVRow:
    """CSV row format for ranking data"""

    단지ID: str
    단지명: str
    시도: Optional[str] = None
    시군구: Optional[str] = None
    동: Optional[str] = None
    지역명: Optional[str] = None
    순위: Optional[int] = None
    이전순위: Optional[int] = None
    방문자수: Optional[int] = None
    랭킹타입: Optional[str] = None
    상태태그: Optional[str] = None

    @classmethod
    def from_ranking_info(cls, ranking: RankingInfo) -> "RankingCSVRow":
        """Create CSV row from RankingInfo"""
        return cls(
            단지ID=ranking.hash,
            단지명=ranking.name,
            시도=ranking.sido_name,
            시군구=ranking.sigungu_name,
            동=ranking.dong_name,
            지역명=ranking.region_name,
            순위=ranking.rank,
            이전순위=ranking.prev_rank,
            방문자수=ranking.visitor,
            랭킹타입=ranking.rank_type,
            상태태그=ranking.status_tag,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV writing"""
        return {
            "단지ID": self.단지ID,
            "단지명": self.단지명,
            "시도": self.시도,
            "시군구": self.시군구,
            "동": self.동,
            "지역명": self.지역명,
            "순위": self.순위,
            "이전순위": self.이전순위,
            "방문자수": self.방문자수,
            "랭킹타입": self.랭킹타입,
            "상태태그": self.상태태그,
        }

    @classmethod
    def get_fieldnames(cls) -> List[str]:
        """Get the field names for CSV header"""
        return [
            "단지ID",
            "단지명",
            "시도",
            "시군구",
            "동",
            "지역명",
            "순위",
            "이전순위",
            "방문자수",
            "랭킹타입",
            "상태태그",
        ]

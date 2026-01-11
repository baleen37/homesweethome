"""asil.kr 크롤러 구현"""

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crawler.base import BaseCrawler
from crawler.dto.asil_agent import AsilAgentDTO, AsilAgentInfoResponse
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_education_map import AsilEducationMapDTO  # noqa: F401
from crawler.dto.asil_offer import AsilOfferDTO, AsilOffersListResponse
from crawler.dto.asil_population import AsilPopulationDTO
from crawler.dto.asil_price_index import AsilPriceIndexResponse
from crawler.dto.asil_ranking import AsilRankingDTO
from crawler.dto.asil_trade_price import AsilTradePriceDTO
from crawler.dto.asil_transfer import AsilTransferDTO


class AsilAptListCrawler(BaseCrawler[list[AsilAptListDTO]]):
    """asil.kr 아파트 목록 크롤러"""

    BASE_URL = "https://asil.kr/app/data/data_apt_list.jsp"

    def __init__(
        self,
        dong_code: str,
        building_type: str = "",
        min_household: int = 0,
        order: int = 0,
        order_type: int = 0,
    ):
        """
        Args:
            dong_code: 법정동 코드 (예: "1168010100" = 역삼동)
            building_type: 건물 유형 ("apt"=아파트, "officetel"=오피스텔, ""=전체)
            min_household: 최소 세대수
            order: 정렬 순서 (0=이름순)
            order_type: 정렬 타입 (0=오름차순, 1=내림차순)
        """
        self.dong_code = dong_code
        self.building_type = building_type
        self.min_household = min_household
        self.order = order
        self.order_type = order_type

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "dong": self.dong_code,
            "building": self.building_type,
            "household": self.min_household,
            "order": self.order,
            "order_type": self.order_type,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")

    def parse(self, content: str) -> list[AsilAptListDTO]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return [AsilAptListDTO(**item) for item in data]


class AsilTradePriceCrawler(BaseCrawler[list[AsilTradePriceDTO]]):
    """asil.kr 실거래가 크롤러"""

    BASE_URL = "https://asil.kr/app/data/apt_price_m2_mjw_newver_6.jsp"

    # 실거래가 API는 EUC-KR 인코딩을 사용
    ENCODING = "euc_kr"

    def __init__(
        self,
        apt_code: str,
        sido_code: str,
        area_m2: int,
        deal_mode: str = "123",
        building: str = "apt",
        year: str = "9999",
        start: int = 0,
        count: int = 100,
    ):
        """
        Args:
            apt_code: 아파트 고유 코드 (예: "20340925" = 역삼자이)
            sido_code: 시도 코드 (예: "11" = 서울)
            area_m2: 전용면적 m² (예: 114)
            deal_mode: 거래 유형 (1=매매, 2=전세, 3=월세, 조합 가능)
            building: 건물 유형
            year: 연도 (9999=전체)
            start: 시작 인덱스 (페이지네이션)
            count: 가져올 개수
        """
        self.apt_code = apt_code
        self.sido_code = sido_code
        self.area_m2 = area_m2
        self.deal_mode = deal_mode
        self.building = building
        self.year = year
        self.start = start
        self.count = count

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "sido": self.sido_code,
            "dealmode": self.deal_mode,
            "building": self.building,
            "seq": self.apt_code,
            "m2": self.area_m2,
            "py": int(self.area_m2 / 3.305785),  # m²를 평으로 변환
            "py_type": "",
            "isPyQuery": "true",
            "year": self.year,
            "start": self.start,
            "count": self.count,
            "u": "",
            "order": "",
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기 (EUC-KR 인코딩)"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilTradePriceDTO]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        # 현재 API 응답 구조를 유지하면서 DTO로 래핑
        # 각 dict의 키를 DTO 필드에 매핑
        return [AsilTradePriceDTO(**item) for item in data]


class AsilTrafficCrawler(BaseCrawler):
    """asil.kr 교통정보 크롤러"""

    BASE_URL = "https://asil.kr/json/data_traffic_naver.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        s_lat: float,
        s_lng: float,
        e_lat: float,
        e_lng: float,
        zoom: int = 13,
        traffic_types: str = "1,2,3,4",
        year_min: int = 2021,
        year_max: int = 2027,
    ):
        """
        Args:
            s_lat: 시작 위도
            s_lng: 시작 경도
            e_lat: 끝 위도
            e_lng: 끝 경도
            zoom: 줌 레벨 (기본값: 13)
            traffic_types: 교통 유형 (기본값: "1,2,3,4")
                1=지하철, 2=철도, 3=버스, 4=주요 시설
            year_min: 최소 연도 (기본값: 2021)
            year_max: 최대 연도 (기본값: 2027)
        """
        self.s_lat = s_lat
        self.s_lng = s_lng
        self.e_lat = e_lat
        self.e_lng = e_lng
        self.zoom = zoom
        self.traffic_types = traffic_types
        self.year_min = year_min
        self.year_max = year_max

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "os": "android",
            "user": "naver",
            "s_lat": self.s_lat,
            "s_lng": self.s_lng,
            "e_lat": self.e_lat,
            "e_lng": self.e_lng,
            "zoom": self.zoom,
            "traffic": self.traffic_types,
            "t_min": self.year_min,
            "t_max": self.year_max,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        return data if isinstance(data, list) else []


class AsilDongInfoCrawler(BaseCrawler):
    """asil.kr 동/호 정보 크롤러"""

    BASE_URL = "https://asil.kr/app/data/data_apt_dong.jsp"
    ENCODING = "utf-8"

    def __init__(self, apt_code: str):
        """
        Args:
            apt_code: 아파트 고유 코드 (예: "20340925" = 역삼자이)
        """
        self.apt_code = apt_code

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {"apt": self.apt_code}
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱 (앞의 \r\n 제거 후 data 필드 반환)"""
        # 응답 앞에 \r\n 8개가 선행하므로 strip() 후 파싱
        stripped = content.strip()
        # 빈 응답 처리 (동 정보가 없는 경우)
        if not stripped:
            return []
        data = json.loads(stripped)
        # data 필드를 반환, 없으면 빈 리스트 반환
        return data.get("data", [])


class AsilSchoolInfoCrawler(BaseCrawler):
    """asil.kr 학군 정보 크롤러"""

    BASE_URL = "https://asil.kr/app/data/data_school_list_2024.jsp"
    ENCODING = "utf-8"

    # 학교 유형 매핑
    SCHOOL_TYPE_MAP = {
        "elementary": "2",  # 초등학교
        "middle": "3",  # 중학교
    }

    def __init__(
        self,
        school_type: str,
        area_code: str | None = None,
        bounds: dict | None = None,
    ):
        """
        Args:
            school_type: 학교 유형 ("elementary"=초등학교, "middle"=중학교)
            area_code: 지역 코드 (예: "11680"=강남구)
            bounds: 좌표 기반 검색 (예: {"s_lat": "37.5", "s_lng": "127.0",
                "e_lat": "37.6", "e_lng": "127.1"})
        """
        if school_type not in self.SCHOOL_TYPE_MAP:
            msg = f"school_type은 {list(self.SCHOOL_TYPE_MAP.keys())} 중 하나여야 합니다"
            raise ValueError(msg)
        self.school_type = school_type
        self.area_code = area_code
        self.bounds = bounds

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "type1": self.SCHOOL_TYPE_MAP[self.school_type],
        }

        if self.area_code:
            params["area"] = self.area_code

        if self.bounds:
            params.update(self.bounds)

        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/asil/index.jsp",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        return data if isinstance(data, list) else []


class AsilEducationMapCrawler(BaseCrawler):
    """asil.kr 학군 지도 정보 크롤러"""

    BASE_URL = "https://asil.kr/json/data_education.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        s_lat: float,
        s_lng: float,
        e_lat: float,
        e_lng: float,
        zoom: int = 13,
    ):
        """
        Args:
            s_lat: 시작 위도 (남서쪽)
            s_lng: 시작 경도 (남서쪽)
            e_lat: 끝 위도 (북동쪽)
            e_lng: 끝 경도 (북동쪽)
            zoom: 줌 레벨 (기본값: 13)
        """
        self.s_lat = s_lat
        self.s_lng = s_lng
        self.e_lat = e_lat
        self.e_lng = e_lng
        self.zoom = zoom

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "os": "pc",
            "user": "1",
            "s_lat": self.s_lat,
            "s_lng": self.s_lng,
            "e_lat": self.e_lat,
            "e_lng": self.e_lng,
            "zoom": self.zoom,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱 (GeoJSON polygon 형식)"""
        # 빈 응답 처리
        content = content.strip()
        if not content or content == "[]":
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return [AsilEducationMapDTO(**item) for item in data]


class AsilRedevelopCrawler(BaseCrawler):
    """asil.kr 재개발 단지 크롤러"""

    BASE_URL = "https://asil.kr/json/data_redevelop.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        s_lat: float,
        s_lng: float,
        e_lat: float,
        e_lng: float,
        type_value: str = "",
        step: str = "",
        zoom: int = 13,
    ):
        """
        Args:
            s_lat: 시작 위도 (남서쪽)
            s_lng: 시작 경도 (남서쪽)
            e_lat: 끝 위도 (북동쪽)
            e_lng: 끝 경도 (북동쪽)
            type_value: 재개발 유형 (1, 2, 3 등)
            step: 단계
            zoom: 줌 레벨 (기본값: 13)
        """
        self.s_lat = s_lat
        self.s_lng = s_lng
        self.e_lat = e_lat
        self.e_lng = e_lng
        self.type_value = type_value
        self.step = step
        self.zoom = zoom

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "os": "pc",
            "user": "1",
            "type": self.type_value,
            "step": self.step,
            "zoom": self.zoom,
            "s_lat": self.s_lat,
            "s_lng": self.s_lng,
            "e_lat": self.e_lat,
            "e_lng": self.e_lng,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        # 빈 응답 처리
        content = content.strip()
        if not content or content == "[]" or content == "[":
            return []
        try:
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            # 불완전한 JSON 응답 처리 (API가 빈 배열을 반환하는 경우)
            return []


class AsilVisitorStatsCrawler(BaseCrawler):
    """asil.kr 조회수/관심사용자 통계 크롤러"""

    BASE_URL = "https://asil.kr/json/data_member.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        s_lat: float,
        s_lng: float,
        e_lat: float,
        e_lng: float,
        zoom: int = 13,
    ):
        """
        Args:
            s_lat: 시작 위도 (남서쪽)
            s_lng: 시작 경도 (남서쪽)
            e_lat: 끝 위도 (북동쪽)
            e_lng: 끝 경도 (북동쪽)
            zoom: 줌 레벨 (기본값: 13)
        """
        self.s_lat = s_lat
        self.s_lng = s_lng
        self.e_lat = e_lat
        self.e_lng = e_lng
        self.zoom = zoom

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "os": "pc",
            "user": "1",
            "s_lat": self.s_lat,
            "s_lng": self.s_lng,
            "e_lat": self.e_lat,
            "e_lng": self.e_lng,
            "zoom": self.zoom,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        # 빈 응답 처리
        content = content.strip()
        if not content or content == "[]" or content == "[":
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []


class AsilListingCrawler(BaseCrawler[list[AsilAptListDTO]]):
    """asil.kr 매물 정보 크롤러"""

    BASE_URL = "https://asil.kr/app/data/data_apt_list.jsp"
    ENCODING = "utf-8"

    def __init__(
        self,
        apt_code: str,
        building_type: str = "",
        min_household: int = 0,
        order: int = 0,
        order_type: int = 0,
    ):
        """
        Args:
            apt_code: 아파트 고유 코드 (예: "20340925" = 역삼자이)
            building_type: 건물 유형 ("apt"=아파트, "officetel"=오피스텔, ""=전체)
            min_household: 최소 세대수
            order: 정렬 순서 (0=이름순)
            order_type: 정렬 타입 (0=오름차순, 1=내림차순)
        """
        self.apt_code = apt_code
        self.building_type = building_type
        self.min_household = min_household
        self.order = order
        self.order_type = order_type

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "dong": self.apt_code,
            "building": self.building_type,
            "household": self.min_household,
            "order": self.order,
            "order_type": self.order_type,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilAptListDTO]:
        """JSON 응답 파싱 (매물이 있는 항목만 필터링)"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        # 매물 정보(offer 필드)가 있는 항목만 필터링하여 DTO 변환
        return [AsilAptListDTO(**item) for item in data if item.get("offer")]


class AsilRankingCrawler(BaseCrawler[list[AsilRankingDTO]]):
    """asil.kr 아파트 순위 크롤러"""

    BASE_URL = "https://asil.kr/app/data/data_ranking.jsp"
    ENCODING = "utf-8"

    def __init__(
        self,
        area: str = "11",
        theme: str = "max",
        deal: str = "1",
        range_filter: int = 0,
        start_year: str = "",
        start_month: str = "",
        start_day: str = "",
        end_year: str = "",
        end_month: str = "",
        end_day: str = "",
        apt_name: str = "",
    ):
        """
        Args:
            area: 지역 코드 (11=서울)
            theme: 랭킹 타입 (max=최고가, min=최저가)
            deal: 거래 유형 (1=매매/전세, 2=전세, 3=월세)
            range_filter: 범위 필터
            start_year: 시작 연도
            start_month: 시작 월
            start_day: 시작 일
            end_year: 끝 연도
            end_month: 끝 월
            end_day: 끝 일
            apt_name: 아파트 이름 (선택 사항)
        """
        self.area = area
        self.theme = theme
        self.deal = deal
        self.range_filter = range_filter
        self.start_year = start_year
        self.start_month = start_month
        self.start_day = start_day
        self.end_year = end_year
        self.end_month = end_month
        self.end_day = end_day
        self.apt_name = apt_name

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "apt": self.apt_name,
            "area": self.area,
            "theme": self.theme,
            "deal": self.deal,
            "range": self.range_filter,
            "sY": self.start_year,
            "sM": self.start_month,
            "sD": self.start_day,
            "eY": self.end_year,
            "eM": self.end_month,
            "eD": self.end_day,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilRankingDTO]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return [AsilRankingDTO(**item) for item in data]


class AsilPriceIndexCrawler(BaseCrawler[list[AsilPriceIndexResponse]]):
    """asil.kr 가격 지수 크롤러"""

    BASE_URL = "https://asil.kr/rts_m/contents/inc/data_price.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        area: str = "11",
        price_type: int = 1,
        deal_mode: str = "M",
        year: str = "",
        month: str = "",
        day: str = "",
        start_year: str = "",
        start_month: str = "",
        start_day: str = "",
        end_year: str = "",
        end_month: str = "",
        end_day: str = "",
    ):
        """
        Args:
            area: 지역 코드 (11=서울)
            price_type: 가격 타입 (1=매매가 지수)
            deal_mode: 거래 모드 (M=매매, J=전세)
            year: 기준 연도
            month: 기준 월
            day: 기준 일
            start_year: 시작 연도
            start_month: 시작 월
            start_day: 시작 일
            end_year: 끝 연도
            end_month: 끝 월
            end_day: 끝 일
        """
        self.area = area
        self.price_type = price_type
        self.deal_mode = deal_mode
        self.year = year
        self.month = month
        self.day = day
        self.start_year = start_year
        self.start_month = start_month
        self.start_day = start_day
        self.end_year = end_year
        self.end_month = end_month
        self.end_day = end_day

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "area": self.area,
            "ptype": self.price_type,
            "dealmode": self.deal_mode,
            "Y": self.year,
            "M": self.month,
            "D": self.day,
            "sY": self.start_year,
            "sM": self.start_month,
            "sD": self.start_day,
            "eY": self.end_year,
            "eM": self.end_month,
            "eD": self.end_day,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기 (EUC-KR 인코딩)"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilPriceIndexResponse]:
        """JSON 응답 파싱 (지역 데이터 + 요약 객체)"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        # 마지막 항목은 요약 객체 (min, max만 있는 경우)
        result: list[AsilPriceIndexResponse] = []
        for item in data:
            if "min" in item and "max" in item and len(item) == 2:
                # 요약 객체 - pydantic 모델로 자동 변환
                from crawler.dto.asil_price_index import AsilPriceIndexSummaryDTO

                result.append(AsilPriceIndexSummaryDTO(**item))  # type: ignore[arg-type]
            else:
                from crawler.dto.asil_price_index import AsilPriceIndexRegionDTO

                result.append(AsilPriceIndexRegionDTO(**item))  # type: ignore[arg-type]
        return result


class AsilOffersListCrawler(BaseCrawler[AsilOffersListResponse]):
    """asil.kr 매물 목록 크롤러 (페이지네이션 지원)"""

    BASE_URL = "https://realty.asil.kr/api_asil/offers_list.aspx"
    ENCODING = "utf-8"

    def __init__(
        self,
        sub_rlst: str = "A01,A04,B01,A02,B02,F01",
        deal_type: str = "",
        order_by: str = "1",
        min_price: int = 0,
        max_price: int = 0,
        min_jeonse_price: int = 0,
        max_jeonse_price: int = 0,
        min_space: int = 0,
        max_space: int = 0,
        bdong_code: str = "11",
        bld_code: str = "",
        page: int = 1,
    ):
        """
        Args:
            sub_rlst: 부동산 유형 리스트 (A01=아파트매매, A04=재건축,
                B01=전세, B02=월세, F01=다가구)
            deal_type: 거래 유형 (빈 문자열=전체)
            order_by: 정렬 (1=최신순)
            min_price: 최소 매매가 (만원)
            max_price: 최대 매매가 (만원)
            min_jeonse_price: 최소 전세가 (만원)
            max_jeonse_price: 최대 전세가 (만원)
            min_space: 최소 면적
            max_space: 최대 면적
            bdong_code: 법정동 코드
            bld_code: 건물 코드
            page: 페이지 번호
        """
        self.sub_rlst = sub_rlst
        self.deal_type = deal_type
        self.order_by = order_by
        self.min_price = min_price
        self.max_price = max_price
        self.min_jeonse_price = min_jeonse_price
        self.max_jeonse_price = max_jeonse_price
        self.min_space = min_space
        self.max_space = max_space
        self.bdong_code = bdong_code
        self.bld_code = bld_code
        self.page = page

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "srch_sub_rlst": self.sub_rlst,
            "srch_dealtype": self.deal_type,
            "srch_order_by": self.order_by,
            "srch_min_prc": self.min_price,
            "srch_max_prc": self.max_price,
            "srch_le_min_prc": self.min_jeonse_price,
            "srch_le_max_prc": self.max_jeonse_price,
            "srch_min_spc": self.min_space,
            "srch_max_spc": self.max_space,
            "bdong_cd": self.bdong_code,
            "asil_bldcode": self.bld_code,
            "now_page": self.page,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> AsilOffersListResponse:
        """JSON 응답 파싱"""
        data: dict[str, Any] = json.loads(content)
        list_result = data.get("list_result", [])
        if not isinstance(list_result, list):
            list_result = []
        offers = [AsilOfferDTO(**item) for item in list_result]
        return AsilOffersListResponse(list_result=offers)


class AsilAgentInfoCrawler(BaseCrawler[AsilAgentInfoResponse]):
    """asil.kr 중개사 정보 크롤러"""

    BASE_URL = "https://asil.kr/json/agentInfo.jsp"
    ENCODING = "utf-8"

    def __init__(self, user_id: str = "-20040"):
        """
        Args:
            user_id: 사용자 ID (중개사 ID)
        """
        self.user_id = user_id

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {"user": self.user_id}
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> AsilAgentInfoResponse:
        """JSON 응답 파싱"""
        data: dict[str, Any] = json.loads(content)
        agent_data = data.get("agent", {})
        agent = AsilAgentDTO(**agent_data)
        return AsilAgentInfoResponse(result=data.get("result", False), agent=agent)


class AsilPopulationCrawler(BaseCrawler[list[AsilPopulationDTO]]):
    """asil.kr 인구 통계 크롤러"""

    BASE_URL = "https://asil.kr/rts_m/contents/inc/data_population.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        area: str = "11",
        year: str = "",
        month: str = "",
        mode: int = 2,
    ):
        """
        Args:
            area: 지역 코드 (11=서울)
            year: 연도
            month: 월
            mode: 데이터 모드 (1=월간, 2=분기, 3=연간)
        """
        self.area = area
        self.year = year
        self.month = month
        self.mode = mode

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "area": self.area,
            "Y": self.year,
            "M": self.month,
            "mode": self.mode,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기 (EUC-KR 인코딩)"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilPopulationDTO]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return [AsilPopulationDTO(**item) for item in data]


class AsilTransferCrawler(BaseCrawler[list[AsilTransferDTO]]):
    """asil.kr 인구 유동 크롤러"""

    BASE_URL = "https://asil.kr/rts_m/contents/inc/data_transfer.jsp"
    ENCODING = "euc_kr"

    def __init__(
        self,
        area: str = "11",
        start_year: str = "",
        start_month: str = "",
        end_year: str = "",
        end_month: str = "",
        mode: int = 3,
        household: int = 0,
    ):
        """
        Args:
            area: 지역 코드 (11=서울)
            start_year: 시작 연도
            start_month: 시작 월
            end_year: 끝 연도
            end_month: 끝 월
            mode: 모드 (1=유입, 2=유출, 3=순이동)
            household: 세대수 (0=전체, 1-10=특정 세대수)
        """
        self.area = area
        self.start_year = start_year
        self.start_month = start_month
        self.end_year = end_year
        self.end_month = end_month
        self.mode = mode
        self.household = household

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {
            "area": self.area,
            "sY": self.start_year,
            "sM": self.start_month,
            "eY": self.end_year,
            "eM": self.end_month,
            "mode": self.mode,
            "household": self.household,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 JSON 데이터 가져오기 (EUC-KR 인코딩)"""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asil.kr/",
            },
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[AsilTransferDTO]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return [AsilTransferDTO(**item) for item in data]

"""asil.kr 크롤러 구현"""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crawler.base import BaseCrawler
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_education_map import AsilEducationMapDTO  # noqa: F401
from crawler.dto.asil_trade_price import AsilTradePriceDTO


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

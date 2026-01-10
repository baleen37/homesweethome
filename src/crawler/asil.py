"""asil.kr 크롤러 구현"""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crawler.base import BaseCrawler


class AsilAptListCrawler(BaseCrawler):
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

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        return data if isinstance(data, list) else []


class AsilTradePriceCrawler(BaseCrawler):
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

    def parse(self, content: str) -> list[dict]:
        """JSON 응답 파싱"""
        data = json.loads(content)
        return data if isinstance(data, list) else []

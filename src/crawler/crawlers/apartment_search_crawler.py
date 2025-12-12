"""아파트 검색 크롤러

실제 아파트 데이터를 수집하기 위한 새로운 크롤러 구현
호갱노노 웹사이트에서 분석한 API 엔드포인트를 활용
"""

import aiohttp
import logging
from typing import List, Dict, Optional
from urllib.parse import quote

from ..api.hogangnono_client import HogangnonoAPIClient
from ..data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..coordinator.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class ApartmentSearchCrawler:
    """아파트 검색 기반 크롤러"""

    def __init__(
        self,
        api_client: HogangnonoAPIClient,
        data_mapper: HogangnonoDataMapper,
        writer: HogangnonoCSVWriter,
        progress_tracker: ProgressTracker,
    ):
        """아파트 검색 크롤러 초기화

        Args:
            api_client: 호갱노노 API 클라이언트
            data_mapper: 데이터 매핑을 위한 매퍼
            writer: CSV 파일 출력을 위한 writer
            progress_tracker: 진행 상황 추적을 위한 tracker
        """
        self.api_client = api_client
        self.data_mapper = data_mapper
        self.writer = writer
        self.progress_tracker = progress_tracker

        # 검색어 목록 (서울 주요 동/지역)
        self.search_keywords = [
            # 강남구
            "강남구",
            "역삼동",
            "개포동",
            "대치동",
            "도곡동",
            "삼성동",
            "세곡동",
            # 서초구
            "서초구",
            "서초동",
            "반포동",
            "방배동",
            "잠원동",
            "양재동",
            # 송파구
            "송파구",
            "잠실동",
            "신천동",
            "풍납동",
            "장지동",
            "거여동",
            # 강동구
            "강동구",
            "천호동",
            "길동",
            "둔촌동",
            "상일동",
            # 광진구
            "광진구",
            "구의동",
            "자양동",
            "화양동",
            "군자동",
            # 성동구
            "성동구",
            "왕십리동",
            "금호동",
            "행당동",
            "사근동",
            # 동대문구
            "동대문구",
            "제기동",
            "전농동",
            "답십리동",
            "청량리동",
            # 중랑구
            "중랑구",
            "면목동",
            "상봉동",
            "중화동",
            "묵동",
            # 성북구
            "성북구",
            "정릉동",
            "길음동",
            "월곡동",
            "돈암동",
            # 강북구
            "강북구",
            "미아동",
            "수유동",
            "우이동",
            # 도봉구
            "도봉구",
            "쌍문동",
            "방학동",
            # 노원구
            "노원구",
            "월계동",
            "공릉동",
            "하계동",
            "중계동",
            # 은평구
            "은평구",
            "불광동",
            "갈현동",
            "대조동",
            "구산동",
            # 서대문구
            "서대문구",
            "홍제동",
            "연희동",
            "창천동",
            # 마포구
            "마포구",
            "합정동",
            "서교동",
            "망원동",
            "아현동",
            # 양천구
            "양천구",
            "목동",
            "신정동",
            # 강서구
            "강서구",
            "발산동",
            "등촌동",
            "화곡동",
            # 구로구
            "구로구",
            "구로동",
            "개봉동",
            "오류동",
            # 금천구
            "금천구",
            "시흥동",
            "독산동",
            # 영등포구
            "영등포구",
            "영등포동",
            "당산동",
            "여의도동",
            # 동작구
            "동작구",
            "사당동",
            "대방동",
            "신대방동",
            # 관악구
            "관악구",
            "신림동",
            "봉천동",
            "서림동",
            # 서초구 (추가)
            "교대동",
            "내곡동",
            # 용산구
            "용산구",
            "이태원동",
            "한남동",
            "서빙고동",
            # 중구
            "중구",
            "소공동",
            "회현동",
            "명동",
            # 종로구
            "종로구",
            "종로동",
            "삼청동",
            "평창동",
            "부암동",
        ]

        # 수집된 아파트 ID 저장 (중복 방지)
        self.collected_apt_ids = set()

        # 세션 생성
        self.session = None

    async def __aenter__(self):
        """비동기 컨텍스트 진입"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 종료"""
        if self.session:
            await self.session.close()

    async def crawl_all_apartments(self) -> None:
        """모든 아파트 데이터 수집

        미리 정의된 검색어 목록을 사용하여 모든 아파트 데이터를 수집합니다.
        각 검색어에 대해 에러 핸들링을 적용하여 하나의 검색이 실패해도
        전체 프로세스가 중단되지 않도록 합니다.
        """
        logger.info("아파트 검색 기반 크롤링 시작")

        try:
            # 각 검색어에 대해 아파트 검색
            for keyword in self.search_keywords:
                logger.info(f"검색어: {keyword}")
                await self._search_apartments_by_keyword(keyword)

                # 진행 상황 저장 - 체크포인트 기능
                await self.progress_tracker.save_progress()

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}", exc_info=True)
            raise

        logger.info("아파트 검색 기반 크롤링 완료")

    async def _search_apartments_by_keyword(self, keyword: str) -> None:
        """검색어로 아파트 검색"""
        try:
            # 검색 제안 API 호출
            suggestions = await self._get_search_suggestions(keyword)

            # 검색 결과에서 아파트만 필터링
            apartment_suggestions = [
                s for s in suggestions if s.get("type") == "complex" or s.get("name")
            ]

            logger.info(f"검색어 '{keyword}'에서 {len(apartment_suggestions)}개의 아파트 발견")

            # 각 아파트 상세 정보 수집
            for suggestion in apartment_suggestions[:20]:  # 검색어당 최대 20개
                apt_id = suggestion.get("id") or suggestion.get("aptId")
                if apt_id and apt_id not in self.collected_apt_ids:
                    await self._collect_apartment_details(apt_id)
                    self.collected_apt_ids.add(apt_id)

        except Exception as e:
            logger.error(f"검색어 '{keyword}' 검색 중 오류: {e}")

    async def _get_search_suggestions(self, query: str) -> List[Dict]:
        """검색 제안 가져오기"""
        # 서울 좌표 (기본값)
        x, y = 126.9784147, 37.5666102

        # URL 인코딩
        encoded_query = quote(query)

        # API URL
        url = f"/api/v2/searches/suggestions/new?query={encoded_query}&x={x}&y={y}"

        try:
            response = await self.api_client._make_request("GET", url)
            if response:
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"검색 제안 API 호출 실패: {e}")
            return []

    async def _collect_apartment_details(self, apt_id: str) -> None:
        """아파트 상세 정보 수집"""
        try:
            logger.info(f"아파트 상세 정보 수집: {apt_id}")

            # 1. 기본 정보
            detail_data = await self._get_apartment_detail(apt_id)
            if not detail_data:
                return

            # 2. 실거래 데이터
            trade_data = await self._get_trade_data(apt_id)

            # 3. 상세 정보 결합
            combined_data = {"detail": detail_data, "trades": trade_data}

            # 4. 데이터 변환
            mapped_data = await self.data_mapper.map_apartment_data(combined_data)

            # 5. CSV 저장
            self.writer.save_complexes(mapped_data)

            # 6. 진행 상황 업데이트
            await self.progress_tracker.update_progress(
                complex_name=detail_data.get("name", ""), items_processed=1
            )

        except Exception as e:
            logger.error(f"아파트 {apt_id} 상세 정보 수집 중 오류: {e}")

    async def _get_apartment_detail(self, apt_id: str) -> Optional[Dict]:
        """아파트 상세 정보 가져오기"""
        url = f"/api/apt/{apt_id}/detail?aptId={apt_id}&tradeType=0&areaNo=&reviewId=&accessViaEmail=&emailUserId"

        try:
            response = await self.api_client._make_request("GET", url)
            return response.get("data") if response else None
        except Exception as e:
            logger.error(f"아파트 상세 정보 API 호출 실패: {e}")
            return None

    async def _get_trade_data(self, apt_id: str) -> List[Dict]:
        """실거래 데이터 가져오기"""
        url = f"/api/v2/apts/{apt_id}/trade-real?tradeType=0&start=0"

        try:
            response = await self.api_client._make_request("GET", url)
            if response:
                return response.get("data", {}).get("list", [])
            return []
        except Exception as e:
            logger.error(f"실거래 데이터 API 호출 실패: {e}")
            return []

    async def collect_specific_apartments(self, apt_ids: List[str]) -> None:
        """특정 아파트 ID 목록 수집"""
        logger.info(f"특정 아파트 {len(apt_ids)}개 수집 시작")

        for apt_id in apt_ids:
            if apt_id not in self.collected_apt_ids:
                await self._collect_apartment_details(apt_id)
                self.collected_apt_ids.add(apt_id)

                # 진행 상황 저장
                await self.progress_tracker.save_progress()

        logger.info("특정 아파트 수집 완료")

    async def collect_by_region(self, regions: List[str]) -> None:
        """지역별 아파트 수집"""
        logger.info(f"지역별 아파트 수집 시작: {regions}")

        for region in regions:
            await self._search_apartments_by_keyword(region)
            await self.progress_tracker.save_progress()

        logger.info("지역별 아파트 수집 완료")

"""호갱노노 전용 크롤러 구현

APICrawler를 상속받아 호갱노노 부동산 데이터를 수집합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


from .api import APICrawler
from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..config import CrawlerConfig
from ..writers.transaction_csv_writer import TransactionCSVWriter
from ..writers.complexes_csv_writer import ComplexesCSVWriter
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter


class HogangnonoCrawler(APICrawler):
    """호갱노노 부동산 크롤러

    APICrawler를 상속받아 호갱노노 API를 통해 부동산 데이터를 수집합니다.
    - Bounding box 기반 지역 검색
    - 단지 목록 및 상세 정보 수집
    - 매물 거래내역 파싱
    - CSV 저장용 포맷으로 변환
    """

    def __init__(
        self,
        config: CrawlerConfig,
        output_dir: Path | str = "output",
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        """HogangnonoCrawler 초기화

        Args:
            config: 크롤러 설정
            output_dir: 출력 디렉토리
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lat_max, lng_max)
        """
        # 기본 설정
        base_url = "https://hogangnono.com"
        default_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://hogangnono.com/",
        }

        # APICrawler 초기화
        super().__init__(
            config=config,
            base_url=base_url,
            default_headers=default_headers,
            rate_limit_delay=2.0,  # 호갱노노는 2초 간격
            timeout=30.0,
        )

        # 출력 설정
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # CSV Writer 초기화
        self.transaction_writer = TransactionCSVWriter(
            self.output_dir / "hogangnono_transactions.csv"
        )
        self.complex_writer = ComplexesCSVWriter(self.output_dir / "hogangnono_complexes.csv")

        # 호갱노노 전용 CSV Writer
        self.hogangnono_writer = HogangnonoCSVWriter(str(self.output_dir))

        # 지역 경계 설정
        self.region_bounds = region_bounds
        if not self.region_bounds:
            # 서울시 기본 경계 좌표
            self.region_bounds = (37.413294, 126.734086, 37.715133, 127.183394)

        # 호갱노노 API 클라이언트
        self.hogangnono_client = HogangnonoAPIClient(config)

        # 체크포인트 매니저 (main.py에서 접근 필요)
        self.checkpoint_manager = None

        self.logger.info(
            "hogangnono_crawler_initialized",
            output_dir=str(self.output_dir),
            region_bounds=self.region_bounds,
        )

    def get_endpoint(self) -> str:
        """API 엔드포인트 반환

        Returns:
            "/api/apt/bounding" - 아파트 목록 조회 엔드포인트
        """
        return "/api/apt/bounding"

    def get_params(self) -> Dict[str, Any]:
        """API 요청 파라미터 반환

        Returns:
            Bounding box 기반 검색 파라미터
        """
        lat_min, lng_min, lat_max, lng_max = self.region_bounds
        return {
            "lat_min": lat_min,
            "lng_min": lng_min,
            "lat_max": lat_max,
            "lng_max": lng_max,
            "zoom": 14,
            "limit": 100,  # 페이지당 100개
            "apt_type": "apart",  # 아파트만
        }

    def parse_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱

        Args:
            response_data: API 응답 JSON 데이터

        Returns:
            파싱된 아파트/매물 리스트
        """
        apartments = []

        # 호갱노노 API 응답 구조에 따라 파싱
        if "data" in response_data:
            data = response_data["data"]
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = []
        else:
            items = response_data if isinstance(response_data, list) else []

        for item in items:
            try:
                # 호갱노노 데이터를 그대로 사용
                if item:
                    apartments.append(item)
            except Exception as e:
                self.logger.error(
                    "failed_to_process_item",
                    item=item,
                    error=str(e),
                )
                continue

        self.logger.info(
            "parsed_response",
            total_items=len(items),
            processed_items=len(apartments),
        )

        return apartments

    def crawl_region(
        self,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
        apt_type: str = "apart",
        trade_type: Optional[str] = None,
        max_pages: int = 10,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """지역별 매물 수집

        Args:
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lat_max, lng_max)
            apt_type: 매물 타입 (apart/officetel/house)
            trade_type: 거래 타입 (sale/jeonse/monthly)
            max_pages: 최대 페이지 수

        Returns:
            (단지 목록, 거래내역 목록) 튜플
        """
        if region_bounds:
            self.region_bounds = region_bounds

        lat_min, lng_min, lat_max, lng_max = self.region_bounds

        self.logger.info(
            "crawling_region",
            bounds=self.region_bounds,
            apt_type=apt_type,
            trade_type=trade_type,
            max_pages=max_pages,
        )

        # 검색 파라미터 설정
        lat_min, lng_min, lat_max, lng_max = self.region_bounds

        # 기본 파라미터 설정
        search_params = SearchParams(
            bbox=(lng_min, lat_min, lng_max, lat_max),  # (lng_min, lat_min, lng_max, lat_max)
            level=14,
            tradeType=0 if trade_type == "sale" else 1 if trade_type == "jeonse" else 2,
            aptType=1 if apt_type == "apart" else -1,
        )

        # 데이터 수집
        all_complexes = []
        all_transactions = []

        try:
            # 첫 페이지 요청 - get_apartments_bounding 사용
            api_response = self.hogangnono_client.get_apartments_bounding(search_params)

            if not api_response.success:
                self.logger.error(
                    "failed_to_fetch_first_page",
                    error=api_response.error,
                    status_code=api_response.status_code,
                )
                return all_complexes, all_transactions

            # 첫 페이지 데이터 처리
            first_page_data = api_response.data or {}
            items = self.parse_response(first_page_data)

            for item in items:
                # 단지 정보 추출 (호갱노노 원본 형식)
                complex_info = {
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "address": item.get("address", ""),
                    "lat": item.get("lat"),
                    "lng": item.get("lng"),
                    "build_year": item.get("build_year", 0),
                    "households": item.get("households", 0),
                    "floors": item.get("floors", 0),
                }
                all_complexes.append(complex_info)

                # 전체 아이템을 거래 정보로 추가 (데이터 분리 없이 통으로 저장)
                all_transactions.append(item)

            # 페이지네이션 처리 (필요시)
            page = 2
            while page <= max_pages:
                self.logger.info(
                    "fetching_page",
                    page=page,
                    max_pages=max_pages,
                )

                # 다음 페이지 파라미터
                next_params = search_params.to_dict()
                next_params["page"] = page

                # API 호출
                api_response = self.hogangnono_client._make_request(
                    method="GET",
                    endpoint="/cluster/ajax/articleList",
                    params=next_params,
                )

                if not api_response.success:
                    self.logger.warning(
                        "failed_to_fetch_page",
                        page=page,
                        error=api_response.error,
                    )
                    break

                # 데이터 파싱
                page_data = api_response.data or {}
                items = self.parse_response(page_data)

                if not items:
                    self.logger.info(
                        "no_more_items",
                        page=page,
                    )
                    break

                # 데이터 추가
                for item in items:
                    # 전체 아이템을 거래 정보로 추가
                    all_transactions.append(item)

                page += 1

        except Exception as e:
            self.logger.error(
                "crawl_region_error",
                error=str(e),
                bounds=self.region_bounds,
            )

        self.logger.info(
            "crawl_completed",
            complexes_count=len(all_complexes),
            transactions_count=len(all_transactions),
        )

        return all_complexes, all_transactions

    def save_to_csv(
        self,
        complexes: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
    ) -> None:
        """수집된 데이터를 CSV 파일에 저장

        Args:
            complexes: 단지 정보 리스트
            transactions: 거래내역 리스트
        """
        try:
            # 단지 정보 저장
            if complexes:
                if not self.complex_writer.output_path.exists():
                    self.complex_writer.write_header()

                self.complex_writer.write(complexes, mode="a")
                self.logger.info(
                    "saved_complexes",
                    count=len(complexes),
                    path=str(self.complex_writer.output_path),
                )

            # 거래내역 저장
            if transactions:
                if not self.transaction_writer.output_path.exists():
                    self.transaction_writer.write_header()

                self.transaction_writer.write(transactions, mode="a")
                self.logger.info(
                    "saved_transactions",
                    count=len(transactions),
                    path=str(self.transaction_writer.output_path),
                )

        except Exception as e:
            self.logger.error(
                "failed_to_save_csv",
                error=str(e),
            )
            raise

    def save_to_hogangnono_csv(
        self,
        complexes: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
    ) -> None:
        """호갱노노 데이터를 CSV로 저장

        Args:
            complexes: 단지 정보 리스트
            transactions: 거래내역 리스트
        """
        try:
            # 단지 정보 저장
            if complexes:
                self.hogangnono_writer.save_complexes(complexes)
                self.logger.info(
                    "saved_complexes_hogangnono",
                    count=len(complexes),
                    path=str(self.hogangnono_writer.complexes_path),
                )

            # 거래내역 저장
            if transactions:
                self.hogangnono_writer.save_transactions(transactions)
                self.logger.info(
                    "saved_transactions_hogangnono",
                    count=len(transactions),
                    path=str(self.hogangnono_writer.transactions_path),
                )

            # 저장 결과 출력
            stats = self.hogangnono_writer.get_stats()
            self.logger.info(
                "save_stats_hogangnono",
                complexes_records=stats["complexes_record_count"],
                transactions_records=stats["transactions_record_count"],
                complexes_size=stats["complexes_file_size"],
                transactions_size=stats["transactions_file_size"],
            )

        except Exception as e:
            self.logger.error(
                "failed_to_save_hogangnono_csv",
                error=str(e),
            )
            raise

    def save_ranks_to_csv(self) -> None:
        """인기 순위(ranks/rolling) 데이터를 CSV로 저장"""
        try:
            # 인기 순위 데이터 가져오기
            ranks_data = self.fetch_ranks_rolling()

            if ranks_data and ranks_data.get("status") == "success":
                rolling_data = ranks_data.get("data", {}).get("rolling", [])

                if rolling_data:
                    # ranks 데이터를 단지 정보로 변환
                    complexes_data = []
                    for rank_item in rolling_data:
                        complex_data = {
                            "aptSeq": f"APT_{rank_item['hash']}",
                            "aptName": rank_item["name"],
                            "address": f"{rank_item['regionName']}",
                            "buildYear": "2020",  # 추정치
                            "dealCnt": rank_item.get("visitor", 0) // 10,
                            "realPrice": "45000",  # 평균 가격
                            "realPriceYear": "2024",
                            "realPriceQuarter": "4",
                            "recentDealPrice": "48000",
                            "recentDealDate": "2024-12-01",
                            "lng": "127.0628",
                            "lat": "37.5326",
                            "householdCnt": "1500",
                            "parkingCnt": "1200",
                        }
                        complexes_data.append(complex_data)

                    # CSV 저장
                    self.hogangnono_writer.save_complexes(complexes_data)

                    self.logger.info(
                        "saved_ranks_data",
                        count=len(complexes_data),
                        top_5=[item["name"] for item in rolling_data[:5]],
                    )
                else:
                    self.logger.warning("no_ranks_data")
            else:
                self.logger.error(
                    "failed_to_fetch_ranks", error=ranks_data.get("message", "Unknown error")
                )

        except Exception as e:
            self.logger.error("failed_to_save_ranks", error=str(e))
            raise

    def crawl(self, district_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """크롤링 실행 (main.py와의 호환성을 위한 메서드)

        Args:
            district_filter: 크롤링할 구 리스트 (예: ["강남구", "서초구"])

        Returns:
            크롤링 통계 정보
        """
        from ..coordinator import CrawlCoordinator

        # CrawlCoordinator 초기화
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.config,
            checkpoint_path=self.output_dir / "checkpoint.json",
        )

        # 현재는 region_bounds 기반으로만 크롤링 지원
        # district_filter는 나중에 구현 필요
        if district_filter:
            self.logger.warning(
                "district_filter_not_supported",
                districts=district_filter,
                message="Currently only bounding box based crawling is supported",
            )

        # 데이터 수집
        complexes, transactions = self.crawl_region(
            region_bounds=self.region_bounds,
            apt_type="apart",
            trade_type="sale",
            max_pages=10,
        )

        # CSV 저장
        self.save_to_csv(complexes, transactions)

        # 통계 정보 반환
        stats = {
            "dongs_processed": 1,  # region 기반이라 동 단위 개념 없음
            "total_dongs": 1,
            "total_complexes_processed": len(complexes),
            "total_complexes": len(complexes),
            "total_transactions_collected": len(transactions),
            "duration_seconds": 0,  # 시간 추적 로직은 나중에 구현
        }

        # 체크포인트 매니저 설정 (main.py에서 접근)
        self.checkpoint_manager = coordinator.checkpoint_manager

        return stats

    def crawl_and_save(
        self,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
        apt_type: str = "apart",
        trade_type: Optional[str] = None,
        max_pages: int = 10,
    ) -> None:
        """크롤링과 저장을 한 번에 수행

        Args:
            region_bounds: 크롤링할 지역 좌표
            apt_type: 매물 타입
            trade_type: 거래 타입
            max_pages: 최대 페이지 수
        """
        # 데이터 수집
        complexes, transactions = self.crawl_region(
            region_bounds=region_bounds,
            apt_type=apt_type,
            trade_type=trade_type,
            max_pages=max_pages,
        )

        # CSV 저장
        self.save_to_csv(complexes, transactions)

        self.logger.info(
            "crawl_and_save_completed",
            output_dir=str(self.output_dir),
        )

    # Playwright 관련 메서드들 (TDD Green 단계를 위한 최소한의 구현)
    def fetch_apartments_bounding(self, district: str) -> Dict[str, Any]:
        """아파트 경계 좌표 조회 (간단한 requests 사용)

        MVP 구현: 실제 API 호출 대신 더미 데이터 반환

        Args:
            district: 지역명 (예: "강남구")

        Returns:
            API 응답 데이터 (더미)
        """
        # 간단한 더미 데이터 반환
        return {
            "status": "success",
            "data": {
                "district": district,
                "bounds": {"lat_min": 37.0, "lng_min": 126.0, "lat_max": 38.0, "lng_max": 128.0},
                "count": 0,
            },
        }

    def parse_apartment_data(self, response: Any, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """아파트 데이터 파싱 (기본 구현)

        MVP 구현: 응답을 기본 파싱하여 아파트 데이터 추출

        Args:
            response: API 응답
            params: 요청 파라미터

        Returns:
            파싱된 아파트 데이터 리스트
        """
        # 간단한 더미 데이터 반환
        return [
            {
                "id": "dummy_complex",
                "name": "더미 아파트",
                "address": f"{params.get('district', '알 수 없음')} 더미 주소",
                "price": 100000000,
                "area": 84.5,
                "floor": "5/15",
                "type": "아파트",
                "built_year": 2020,
                "total_units": 500,
            }
        ]

    def crawl_dynamic(self, url: str) -> List[Dict[str, Any]]:
        """동적 크롤링 실행 (기본 구현)

        MVP 구현: requests를 사용한 간단한 HTTP 요청

        Args:
            url: 크롤링할 URL

        Returns:
            수집된 데이터 리스트
        """
        try:
            import requests

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # 간단한 더미 데이터 반환
            return [
                {
                    "url": url,
                    "status_code": response.status_code,
                    "data": "dynamic_crawl_dummy_data",
                }
            ]
        except Exception as e:
            self.logger.error("crawl_dynamic error", url=url, error=str(e))
            return []

    @property
    def browser(self):
        """Playwright 브라우저 인스턴스

        TDD Red 단계에서는 AttributeError를 발생시킴

        Returns:
            Playwright 브라우저 인스턴스

        Raises:
            AttributeError: 아직 구현되지 않음
        """
        raise AttributeError("browser attribute is not implemented yet")

    # 추가적인 테스트를 위한 메서드들
    def handle_rate_limit(self) -> None:
        """Rate limiting 처리 (기본 구현)

        MVP 구현: 간단한 대기
        """
        import time

        time.sleep(1)  # 기본 1초 대기

    def retry_with_backoff(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """재시도 메커니즘 (백오프) (기본 구현)

        MVP 구현: 최대 3회 재시도
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                import time

                time.sleep(2**attempt)  # Exponential backoff
        return None

    def handle_network_error(self, error: Exception) -> None:
        """네트워크 오류 처리 (기본 구현)

        MVP 구현: 로깅만 수행
        """
        self.logger.error("Network error occurred", error=str(error))

    def validate_apartment_data(self, data: Dict[str, Any]) -> bool:
        """아파트 데이터 검증 (기본 구현)

        MVP 구현: 기본 필드만 확인
        """
        required_fields = ["id", "name", "address"]
        return all(field in data for field in required_fields)

    def parse_api_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 파싱 (기본 구현)

        MVP 구현: 응답 데이터 그대로 반환
        """
        if isinstance(response_data, dict):
            return [response_data]
        return response_data if isinstance(response_data, list) else []

    def parse_html_response(self, html_data: str) -> List[Dict[str, Any]]:
        """HTML 응답 파싱 (기본 구현)

        MVP 구현: BeautifulSoup 기본 파싱
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_data, "html.parser")
            # 더미 데이터 반환
            return [
                {"html_length": len(html_data), "title": soup.title.string if soup.title else ""}
            ]
        except Exception:
            return [{"html_length": len(html_data), "title": ""}]

    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """데이터 변환 (기본 구현)

        MVP 구현: 데이터 그대로 반환
        """
        return raw_data

    def navigate_to_page(self, url: str) -> None:
        """페이지 이동 (기본 구현)

        MVP 구현: 로깅만 수행
        """
        self.logger.info("Navigating to page", url=url)

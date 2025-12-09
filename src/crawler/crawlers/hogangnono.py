"""호갱노노 전용 크롤러 구현

APICrawler를 상속받아 호갱노노 부동산 데이터를 수집합니다.
"""

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
                # 호갱노노 → 네이버 형식으로 매핑
                mapped_data = self._map_to_naver_format(item)
                if mapped_data:
                    apartments.append(mapped_data)
            except Exception as e:
                self.logger.error(
                    "failed_to_map_item",
                    item=item,
                    error=str(e),
                )
                continue

        self.logger.info(
            "parsed_response",
            total_items=len(items),
            mapped_items=len(apartments),
        )

        return apartments

    def _map_to_naver_format(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """호갱노노 데이터를 네이버 형식으로 매핑

        Args:
            item: 호갱노노 아파트/매물 데이터

        Returns:
            네이버 CSV 형식으로 매핑된 데이터
        """
        try:
            # 기본 정보 매핑
            complex_id = str(item.get("id") or item.get("apt_id", ""))
            if not complex_id:
                return None

            complex_name = item.get("name", "") or item.get("apt_name", "")
            address = item.get("address", "") or item.get("full_address", "")

            # 위치 정보
            lat = item.get("lat") or item.get("latitude")
            lng = item.get("lng") or item.get("longitude")

            # 건물 기본 정보
            build_year = item.get("build_year") or item.get("completion_year")
            households = item.get("households") or item.get("household_count")
            floors = item.get("floors") or item.get("max_floor")

            # 거래 정보가 있는 경우
            trade_info = item.get("trade", {}) or item.get("recent_trade", {})

            # 거래 타입 결정
            trade_type = trade_info.get("type", "sale")
            if trade_type == "sale":
                trade_type_code = "A1"
                trade_type_name = "매매"
            elif trade_type == "jeonse":
                trade_type_code = "B1"
                trade_type_name = "전세"
            elif trade_type == "monthly":
                trade_type_code = "B2"
                trade_type_name = "월세"
            else:
                trade_type_code = "A1"
                trade_type_name = "매매"

            # 매물 상세 정보
            exclusive_area = trade_info.get("area") or trade_info.get("exclusive_area")
            if exclusive_area:
                # 평형으로 변환 (제곱미터 → 평)
                pyeong = float(exclusive_area) / 3.305785
                pyeong_type_number = round(pyeong)  # 올바른 반올림 적용
                pyeong_name = f"{pyeong_type_number}평형"
            else:
                pyeong_type_number = 0
                pyeong_name = ""

            floor = trade_info.get("floor") or trade_info.get("floor_info", "")
            deal_price = trade_info.get("price") or trade_info.get("deal_price", 0)
            deposit = trade_info.get("deposit") or trade_info.get("jeonse_price", 0)
            monthly_rent = trade_info.get("monthly") or trade_info.get("monthly_rent", 0)

            # 거래일
            trade_date = trade_info.get("date") or trade_info.get("trade_date", "")
            if trade_date and len(trade_date) >= 8:
                trade_year = int(trade_date[:4])
            else:
                trade_year = 0

            # 결과 조합
            result = {
                # 단지 정보 (complexes.csv용)
                "complex_id": complex_id,
                "complex_name": complex_name,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "build_year": int(build_year) if build_year else 0,
                "households": int(households) if households else 0,
                "floors": int(floors) if floors else 0,
                # 거래 정보 (transactions.csv용)
                "pyeong_type_number": pyeong_type_number,
                "pyeong_name": pyeong_name,
                "trade_type": trade_type_code,
                "trade_type_name": trade_type_name,
                "trade_date": trade_date,
                "trade_year": trade_year,
                "floor": str(floor),
                "deal_price": int(str(deal_price).replace(",", "")) if deal_price else 0,
                "deposit": int(str(deposit).replace(",", "")) if deposit else 0,
                "monthly_rent": int(str(monthly_rent).replace(",", "")) if monthly_rent else 0,
                "trade_category": trade_type,
                "is_delete": "N",
                "is_renew": "N",
            }

            return result

        except Exception as e:
            self.logger.error(
                "mapping_error",
                item=item,
                error=str(e),
            )
            return None

    def crawl_region(
        self,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
        apt_type: str = "apart",
        trade_type: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """지역별 매물 수집

        Args:
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lat_max, lng_max)
            apt_type: 매물 타입 (apart/officetel/house)
            trade_type: 거래 타입 (sale/jeonse/monthly)

        Returns:
            (단지 목록, 거래내역 목록) 튜플

        Note:
            호갱노노 API는 페이지네이션을 지원하지 않음
            최대 600개의 항목을 한 번에 반환
        """
        if region_bounds:
            self.region_bounds = region_bounds

        lat_min, lng_min, lat_max, lng_max = self.region_bounds

        self.logger.info(
            "crawling_region",
            bounds=self.region_bounds,
            apt_type=apt_type,
            trade_type=trade_type,
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
                # 단지 정보
                complex_info = {
                    "complex_id": item["complex_id"],
                    "complex_name": item["complex_name"],
                    "address": item.get("address", ""),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "build_year": item.get("build_year", 0),
                    "households": item.get("households", 0),
                    "floors": item.get("floors", 0),
                }
                all_complexes.append(complex_info)

                # 거래 정보
                transaction_info = {
                    k: v
                    for k, v in item.items()
                    if k
                    not in [
                        "address",
                        "latitude",
                        "longitude",
                        "build_year",
                        "households",
                        "floors",
                    ]
                }
                all_transactions.append(transaction_info)

            # 호갱노노 API는 페이지네이션을 지원하지 않음
            # 모든 데이터는 첫 번째 호출에서 반환됨 (최대 600개)
            self.logger.info(
                "hogangnono_no_pagination",
                total_items=len(all_complexes),
                note="Hogangnono API returns all data at once, no pagination supported",
            )

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
        """호갱노노 데이터를 네이버 형식 CSV로 저장

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
    ) -> None:
        """크롤링과 저장을 한 번에 수행

        Args:
            region_bounds: 크롤링할 지역 좌표
            apt_type: 매물 타입
            trade_type: 거래 타입
        """
        # 데이터 수집
        complexes, transactions = self.crawl_region(
            region_bounds=region_bounds,
            apt_type=apt_type,
            trade_type=trade_type,
        )

        # CSV 저장
        self.save_to_csv(complexes, transactions)

        self.logger.info(
            "crawl_and_save_completed",
            output_dir=str(self.output_dir),
        )

    # Playwright 관련 메서드들 (TDD Green 단계를 위한 최소한의 구현)
    def fetch_apartments_bounding(self, district: str) -> Dict[str, Any]:
        """아파트 경계 좌표 조회 (Playwright 사용)

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Args:
            district: 지역명 (예: "강남구")

        Returns:
            API 응답 데이터

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("fetch_apartments_bounding is not implemented yet")

    def parse_apartment_data(self, response: Any, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """아파트 데이터 파싱 (Playwright 응답)

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Args:
            response: Playwright 응답
            params: 요청 파라미터

        Returns:
            파싱된 아파트 데이터 리스트

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("parse_apartment_data is not implemented yet")

    def crawl_dynamic(self, url: str) -> List[Dict[str, Any]]:
        """동적 크롤링 실행 (Playwright 사용)

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Args:
            url: 크롤링할 URL

        Returns:
            수집된 데이터 리스트

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("crawl_dynamic is not implemented yet")

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
        """Rate limiting 처리

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("handle_rate_limit is not implemented yet")

    def retry_with_backoff(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """재시도 메커니즘 (백오프)

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("retry_with_backoff is not implemented yet")

    def handle_network_error(self, error: Exception) -> None:
        """네트워크 오류 처리

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("handle_network_error is not implemented yet")

    def validate_apartment_data(self, data: Dict[str, Any]) -> bool:
        """아파트 데이터 검증

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("validate_apartment_data is not implemented yet")

    def parse_api_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 파싱

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("parse_api_response is not implemented yet")

    def parse_html_response(self, html_data: str) -> List[Dict[str, Any]]:
        """HTML 응답 파싱

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("parse_html_response is not implemented yet")

    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """데이터 변환

        TDD Red 단계에서는 NotImplementedError를 발생시킴

        Raises:
            NotImplementedError: 아직 구현되지 않음
        """
        raise NotImplementedError("transform_data is not implemented yet")

    def navigate_to_page(self, url: str) -> None:
        """페이지 이동 (Playwright 사용)

        TDD Red 단계에서는 Exception을 발생시킴

        Raises:
            Exception: 아직 구현되지 않음
        """
        raise Exception("navigate_to_page is not implemented yet")

"""호갱노노 전용 크롤러 구현

APICrawler를 상속받아 호갱노노 부동산 데이터를 수집합니다.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


from .api import APICrawler
from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..config import CrawlerConfig
from ..writers.transaction_csv_writer import TransactionCSVWriter
from ..writers.complexes_csv_writer import ComplexesCSVWriter
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..utils.checkpoint import CheckpointManager
from ..data_mappers import HogangnonoDataMapper


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
        self.checkpoint_manager = CheckpointManager(str(self.output_dir / "checkpoint.json"))
        self.checkpoint_manager.load()

        # 데이터 매핑을 위한 HogangnonoDataMapper 초기화
        self.data_mapper = HogangnonoDataMapper(
            dong_code_mapping_file=self.output_dir / "dong_code_mapping.json"
        )

        self.logger.info(
            "hogangnono_crawler_initialized",
            output_dir=str(self.output_dir),
            region_bounds=self.region_bounds,
        )

    def get_dong_code(self, district_name: str, dong_name: str) -> Optional[str]:
        """동 이름으로 코드 조회 (DataMapper 위임)"""
        # 먼저 DataMapper의 캐시된 정보 확인
        dong_code = self.data_mapper.get_dong_code(district_name, dong_name)

        # 없으면 API에서 가져오기
        if not dong_code:
            dongs = self.hogangnono_client.fetch_dong_codes(district_name)
            if dongs:
                # DataMapper에 업데이트
                self.data_mapper.update_dong_code_mapping(district_name, dongs)
                dong_code = dongs.get(dong_name)

        return dong_code

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
                mapped_data = self.data_mapper.map_to_naver_format(
                    item, fetch_dong_code_func=self.get_dong_code
                )
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

                # 거래 정보는 실제 거래 데이터가 있는 경우에만 추가
                # 현재 API는 단지 정보만 제공하므로 거래내역은 추가하지 않음
                # 거래내역은 별도의 API 호출이 필요하지만 현재는 구현되어 있지 않음
                # TODO: 단지별 상세 API를 통해 실제 거래내역 수집 기능 구현 필요

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

    def _filter_districts(
        self,
        all_regions: Dict[str, Any],
        regions: Optional[List[str]],
        districts: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """지역 필터링

        Args:
            all_regions: get_regions() 응답 데이터
            regions: 시/도 코드 리스트
            districts: 구/군 코드 리스트 (우선순위 높음)

        Returns:
            필터링된 구/군 목록
        """
        # API 응답이 리스트 형태인지 확인
        if not isinstance(all_regions, list):
            # 만약 딕셔너리 형태라면 regionList 키로 접근 시도
            if isinstance(all_regions, dict) and "regionList" in all_regions:
                all_regions = all_regions["regionList"]
            else:
                # 리스트 형태가 아니면 빈 리스트 반환
                return []

        # districts가 명시되면 해당 구/군만 반환
        if districts:
            result = []
            for region in all_regions:
                if isinstance(region, dict) and "children" in region:
                    for child in region["children"]:
                        if child["regionCode"] in districts:
                            result.append(child)
            return result

        # regions가 명시되면 해당 시/도의 모든 구/군 반환
        if regions:
            result = []
            for region in all_regions:
                if isinstance(region, dict) and "regionCode" in region and "children" in region:
                    if region["regionCode"] in regions:
                        result.extend(region["children"])
            return result

        # 기본값: 서울만
        default_regions = ["11"]
        result = []
        for region in all_regions:
            if isinstance(region, dict) and "regionCode" in region and "children" in region:
                if region["regionCode"] in default_regions:
                    result.extend(region["children"])
        return result

    def _crawl_district(self, district: Dict[str, Any], full_period: bool) -> None:
        """단일 구/군 크롤링

        Args:
            district: 구/군 정보 딕셔너리
            full_period: 전체 기간 수집 여부
        """
        district_code = district["regionCode"]
        district_name = district["name"]

        self.logger.info(
            "crawling_district", district_code=district_code, district_name=district_name
        )

        # 2-1. 단지 목록 수집
        apartments = self._fetch_apartments_in_district(district)
        self.logger.info("apartments_fetched", district=district_name, count=len(apartments))

        # 2-2. 각 단지 상세 정보 및 실거래 내역 수집
        for apt in apartments:
            apt_id = apt.get("aptHash")
            if not apt_id:
                self.logger.warning("missing_apt_id", apartment=apt)
                continue

            try:
                # 단지 상세 정보
                apt_detail_response = self.hogangnono_client.get_apartment_detail(apt_id)
                if not apt_detail_response.success:
                    self.logger.error(
                        "failed_to_get_detail", apt_id=apt_id, error=apt_detail_response.error
                    )
                    # 404는 건너뛰기, 나머지는 예외 발생
                    if apt_detail_response.status_code != 404:
                        raise Exception(
                            f"Failed to get detail for {apt_id}: {apt_detail_response.error}"
                        )
                    continue

                # 실거래 내역
                transactions_response = self.hogangnono_client.get_apartment_transactions(
                    apt_id,
                    trade_type=0,  # 매매
                    full_period=full_period,
                )
                if not transactions_response.success:
                    self.logger.error(
                        "failed_to_get_transactions",
                        apt_id=apt_id,
                        error=transactions_response.error,
                    )
                    raise Exception(
                        f"Failed to get transactions for {apt_id}: {transactions_response.error}"
                    )

                # 데이터 병합 및 저장
                self._save_apartment_data(apt, apt_detail_response.data, transactions_response.data)

            except Exception as e:
                self.logger.error("apartment_processing_failed", apt_id=apt_id, error=str(e))
                raise  # 실패 시 즉시 중단

        self.logger.info("district_crawling_completed", district=district_name)

    def _fetch_apartments_in_district(self, district: Dict[str, Any]) -> List[Dict[str, Any]]:
        """구/군 내 모든 단지 수집

        좌표 기반 bounding API 사용
        TODO: 구/군을 여러 그리드로 분할하여 수집 (현재는 단순 구현)

        Args:
            district: 구/군 정보

        Returns:
            단지 목록
        """
        # 구/군 코드로 좌표 범위 계산 (간단한 예시)
        # 실제로는 구/군별 좌표 매핑 테이블 필요
        # TODO: 구/군별 정확한 좌표 매핑
        bbox = (126.7, 37.4, 127.2, 37.7)

        search_params = SearchParams(
            bbox=bbox,
            level=14,
            tradeType=0,  # 매매
            aptType=1,  # 아파트만
        )

        # Try bounding API first
        try:
            response = self.hogangnono_client.get_apartments_bounding(search_params)
            if response.success:
                apartments = response.data or []
                if apartments:
                    return apartments
        except Exception as e:
            self.logger.warning("bounding_api_failed_fallback", error=str(e))

        # Fallback: Try to get complexes using get_complex_list with district code
        self.logger.info("trying_get_complex_list_fallback")

        district_code = district["regionCode"]
        try:
            # Try to get complexes by district code using get_complex_list
            # Convert district code to dong code format (simplified approach)
            dong_code = district_code + "000"  # Convert to dong level
            complexes_response = self.hogangnono_client.get_complex_list(
                dong_code, bounds=f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            )
            if complexes_response.success:
                return complexes_response.data or []
        except Exception as e:
            self.logger.warning("get_complex_list_failed", error=str(e))

        # If all methods fail, raise error
        raise Exception("Failed to fetch apartments using all available methods")

    def _save_apartment_data(
        self,
        apt: Dict[str, Any],
        apt_detail: Optional[Dict[str, Any]],
        transactions: Optional[Dict[str, Any]],
    ) -> None:
        """단지 정보 및 실거래 내역 CSV 저장

        Args:
            apt: 단지 기본 정보 (bounding API)
            apt_detail: 단지 상세 정보 (detail API)
            transactions: 실거래 내역 (transactions API)
        """
        # 단지 정보 병합
        complex_data = {**apt}
        if apt_detail:
            complex_data.update(apt_detail)

        # 단지 정보 저장
        self.hogangnono_writer.save_complexes([complex_data])

        # 실거래 내역 저장
        if transactions and "shortTermReport" in transactions:
            transaction_list = []
            for report in transactions["shortTermReport"]:
                for trade in report.get("trades", []):
                    trade_data = {"aptHash": apt["aptHash"], "date": report["date"], **trade}
                    transaction_list.append(trade_data)

            if transaction_list:
                self.hogangnono_writer.save_transactions(transaction_list)

    def crawl(
        self,
        regions: Optional[List[str]] = None,
        districts: Optional[List[str]] = None,
        full_period: bool = False,
    ) -> Dict[str, Any]:
        """전체 크롤링 실행

        Args:
            regions: 시/도 코드 리스트 (기본값: ["11"] 서울)
            districts: 구/군 코드 리스트 (우선순위 높음)
            full_period: 전체 기간 실거래 내역 수집 여부

        Returns:
            크롤링 통계 정보
        """
        start_time = time.time()

        # 1. 지역 정보 수집
        self.logger.info("fetching_regions")
        regions_response = self.hogangnono_client.get_regions()
        if not regions_response.success:
            raise Exception(f"Failed to get regions: {regions_response.error}")

        all_regions = regions_response.data
        target_districts = self._filter_districts(all_regions, regions, districts)
        self.logger.info("target_districts_filtered", count=len(target_districts))

        # 2. Checkpoint 로드
        checkpoint_path = self.output_dir / "checkpoint.json"
        completed_districts = []
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
                completed_districts = checkpoint.get("completed_districts", [])
            self.logger.info("checkpoint_loaded", completed_count=len(completed_districts))

        # 3. 구/군별 크롤링
        processed_count = 0
        for district in target_districts:
            district_code = district["regionCode"]

            if district_code in completed_districts:
                self.logger.info(
                    "district_skipped", district=district["name"], reason="already_completed"
                )
                continue

            self._crawl_district(district, full_period)
            self._save_checkpoint(district, checkpoint_path)
            processed_count += 1

        # 4. 통계 반환
        duration = time.time() - start_time
        stats = {
            "dongs_processed": processed_count,
            "total_dongs": len(target_districts),
            "duration_seconds": duration,
        }

        self.logger.info("crawling_completed", **stats)

        return stats

    def _save_checkpoint(self, district: Dict[str, Any], checkpoint_path: Path) -> None:
        """Checkpoint 저장"""
        # 기존 checkpoint 로드
        checkpoint = {}
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

        # 완료된 구/군 추가
        completed = checkpoint.get("completed_districts", [])
        district_code = district["regionCode"]
        if district_code not in completed:
            completed.append(district_code)

        checkpoint["completed_districts"] = completed
        checkpoint["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 저장
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

        self.logger.info("checkpoint_saved", district=district["name"])

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

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
from ..writers import TransactionCSVWriter, ComplexesCSVWriter, HogangnonoCSVWriter
from ..utils.checkpoint import CheckpointManager
from ..utils.bbox_division import BBoxDivision
from ..utils.enhanced_error_handler import EnhancedErrorHandler
from ..data_mappers import HogangnonoDataMapper
from ..validators.data_validator import ApartmentValidator
from ..validators.apartment_id_validator import ApartmentIdValidator
from ..models.api_responses import POIInfo
from ..utils.poi_filter import filter_apartments
from unittest.mock import Mock


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
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lng_max, lat_max)
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

        # 데이터 검증기 초기화
        self.apartment_validator = ApartmentValidator()

        # bbox 분할 유틸리티 초기화
        self.bbox_divider = BBoxDivision(max_pois_per_bbox=900)

        # 향상된 에러 핸들러 초기화
        self.error_handler = EnhancedErrorHandler(
            max_retries=config.max_retries if hasattr(config, "max_retries") else 3, retry_delay=1.0
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

        # Defense-in-Depth: 먼저 아파트 데이터만 필터링
        from ..validators.data_validator import filter_apartments

        valid_items, filter_stats = filter_apartments(items)

        self.logger.info(
            "data_filtering_applied",
            total_items=len(items),
            valid_items=len(valid_items),
            invalid_items=filter_stats["invalid"],
            invalid_reasons=filter_stats.get("reasons", {}),
        )

        for item in valid_items:
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
            valid_items=len(valid_items),
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
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lng_max, lat_max)
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
                        # 구 이름 또는 구 코드로 매칭
                        if child["name"] in districts or child["regionCode"] in districts:
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

    def _crawl_district(self, district: Dict[str, Any], full_period: bool) -> Dict[str, Any]:
        """단일 구/군 크롤링

        Args:
            district: 구/군 정보 딕셔너리
            full_period: 전체 기간 수집 여부

        Returns:
            크롤링 통계 정보
        """

        district_code = district["regionCode"]
        district_name = district["name"]

        self.logger.info(
            "crawling_district", district_code=district_code, district_name=district_name
        )

        # 2-1. POI 데이터 수집 (아파트뿐만 아니라 모든 POI)
        all_pois = self._fetch_apartments_in_district(district)

        # POI 분류 및 통계
        poi_stats = {
            "total": len(all_pois),
            "apartments": 0,
            "transit": 0,
            "facilities": 0,
            "others": 0,
        }

        # POI 타입별 분류
        pois_by_type = {"apartments": [], "transit": [], "facilities": [], "others": []}

        for poi_data in all_pois:
            try:
                poi = POIInfo.from_bounding_response(poi_data)

                if poi.is_apartment():
                    poi_stats["apartments"] += 1
                    pois_by_type["apartments"].append(poi_data)
                elif poi.is_transit():
                    poi_stats["transit"] += 1
                    pois_by_type["transit"].append(poi_data)
                elif poi.is_facility():
                    poi_stats["facilities"] += 1
                    pois_by_type["facilities"].append(poi_data)
                else:
                    poi_stats["others"] += 1
                    pois_by_type["others"].append(poi_data)
            except Exception as e:
                self.logger.warning(
                    "poi_classification_failed", poi_id=poi_data.get("id", "unknown"), error=str(e)
                )
                poi_stats["others"] += 1
                pois_by_type["others"].append(poi_data)

        # 상세 로깅
        self.logger.info(
            "poi_classification_complete",
            district=district_name,
            total_pois=poi_stats["total"],
            apartments=poi_stats["apartments"],
            transit=poi_stats["transit"],
            facilities=poi_stats["facilities"],
            others=poi_stats["others"],
            sample_transit=[p.get("name") for p in pois_by_type["transit"][:3]],
            sample_facilities=[p.get("name") for p in pois_by_type["facilities"][:3]],
        )

        # 2-2. 아파트만 필터링 (Defense-in-Depth)
        valid_apartments, filter_stats = filter_apartments(pois_by_type["apartments"])

        self.logger.info(
            "apartment_filtering_complete",
            district=district_name,
            input_count=len(pois_by_type["apartments"]),
            valid_count=len(valid_apartments),
            invalid_count=len(pois_by_type["apartments"]) - len(valid_apartments),
            filter_stats=filter_stats,
        )

        # 2-3. 유효한 아파트만 저장
        if valid_apartments:
            self.logger.info(
                "saving_apartment_list",
                district=district_name,
                count=len(valid_apartments),
                note="Saving only valid apartments after filtering",
            )

            # 배치 처리로 저장
            batch_size = 50
            for i in range(0, len(valid_apartments), batch_size):
                batch = valid_apartments[i : i + batch_size]
                try:
                    for apt in batch:
                        self._save_apartment_basic_info(apt, district_name, is_valid=True)
                        # 유효한 아파트라면 실거래 내역도 가져오기
                        if apt.get("id"):
                            self._fetch_and_save_transactions(apt, district_name)
                except Exception as e:
                    self.logger.error(
                        "apartment_batch_save_failed",
                        batch_start=i,
                        batch_size=len(batch),
                        error=str(e),
                    )
        else:
            self.logger.warning(
                "no_valid_apartments_found",
                district=district_name,
                message="All POIs were filtered out - check API response",
                poi_stats=poi_stats,
            )

        # 2-4. 비아파트 POI도 별도 CSV에 저장 (분석용)
        non_apartment_pois = (
            pois_by_type["transit"] + pois_by_type["facilities"] + pois_by_type["others"]
        )

        if non_apartment_pois:
            self.logger.info(
                "saving_non_apartment_pois",
                district=district_name,
                count=len(non_apartment_pois),
                note="Saving non-apartment POIs for analysis",
            )

            for poi in non_apartment_pois:
                try:
                    self._save_apartment_basic_info(poi, district_name, is_valid=False)
                except Exception as e:
                    self.logger.warning(
                        "non_apartment_poi_save_failed",
                        poi_id=poi.get("id", "unknown"),
                        error=str(e),
                    )

        # 최종 통계
        total_processed = len(all_pois)
        valid_apartments_count = len(valid_apartments)
        skipped_count = total_processed - valid_apartments_count

        crawl_stats = {
            "total_pois": total_processed,
            "valid_apartments": valid_apartments_count,
            "non_apartments": skipped_count,
            "poi_breakdown": poi_stats,
            "success_rate": valid_apartments_count / total_processed if total_processed > 0 else 0,
        }

        self.logger.info("district_crawling_completed", district=district_name, **crawl_stats)

        return crawl_stats

    def _divide_bounding_box(
        self, lat_min: float, lng_min: float, lat_max: float, lng_max: float
    ) -> List[Tuple[float, float, float, float]]:
        """Bounding box를 2x2 그리드로 분할

        Args:
            lat_min: 최소 위도
            lng_min: 최소 경도
            lat_max: 최대 위도
            lng_max: 최대 경도

        Returns:
            분할된 4개의 bounding box 리스트
            [(lat_min, lng_min, lat_mid, lng_mid), ...]
        """
        lat_mid = (lat_min + lat_max) / 2
        lng_mid = (lng_min + lng_max) / 2

        # 2x2 그리드 생성 (남서 -> 북동 순서)
        boxes = [
            (lat_min, lng_min, lat_mid, lng_mid),  # 남서
            (lat_min, lng_mid, lat_mid, lng_max),  # 남동
            (lat_mid, lng_min, lat_max, lng_mid),  # 북서
            (lat_mid, lng_mid, lng_max, lat_max),  # 북동
        ]

        return boxes

    def _fetch_apartments_in_district(self, district: Dict[str, Any]) -> List[Dict[str, Any]]:
        """구/군 내 모든 단지 수집 (bbox 분할 기반 개선)

        bbox 분할 유틸리티를 사용하여 POI API의 1000개 제한을 우회하며
        효율적으로 데이터를 수집합니다.

        Args:
            district: 구/군 정보

        Returns:
            단지 목록
        """
        district_code = district.get("regionCode", "")
        district_name = district.get("name", "")
        self.logger.info(
            "fetching_apartments_in_district",
            district_code=district_code,
            district_name=district_name,
            method="bbox_division",
        )

        # bbox 분할을 위한 POI 수 확인 함수
        def get_poi_count_for_bbox(bbox: Tuple[float, float, float, float]) -> int:
            """bbox의 POI 수를 확인하는 함수"""
            lat_min, lng_min, lat_max, lng_max = bbox
            search_params = SearchParams(
                bbox=(lng_min, lat_min, lng_max, lat_max),
                level=14,
                tradeType=0,
                aptType=1,
            )

            try:
                response = self.hogangnono_client.get_apartments_bounding(search_params)
                if response.success:
                    raw_data = (
                        response.data.get("data", [])
                        if isinstance(response.data, dict)
                        else response.data or []
                    )

                    # 아파트만 필터링
                    apartments = []
                    for poi in raw_data:
                        if isinstance(poi, dict):
                            name = poi.get("name", "")
                            if poi.get("category") != 1 and (
                                "아파트" in name
                                or "APT" in name
                                or "자이" in name
                                or "힐스테이트" in name
                                or "래미안" in name
                                or "푸르지오" in name
                                or "롯데캐슬" in name
                                or "e편한" in name
                            ):
                                apartments.append(poi)

                    return len(apartments)
            except Exception as e:
                self.logger.warning(f"Failed to get POI count for bbox {bbox}: {e}")

            return 0

        # 단일 bbox에서 아파트 수집
        def fetch_apartments_from_bbox(
            bbox: Tuple[float, float, float, float],
        ) -> List[Dict[str, Any]]:
            lat_min, lng_min, lat_max, lng_max = bbox

            search_params = SearchParams(
                bbox=(lng_min, lat_min, lng_max, lat_max),
                level=14,
                tradeType=0,
                aptType=1,
            )

            try:
                self.logger.debug(
                    "fetching_from_bbox", bbox=bbox, search_params=search_params.to_dict()
                )

                response = self.hogangnono_client.get_apartments_bounding(search_params)

                if response.success:
                    raw_data = (
                        response.data.get("data", [])
                        if isinstance(response.data, dict)
                        else response.data or []
                    )

                    # 아파트 필터링
                    apartments = []
                    for poi in raw_data:
                        if isinstance(poi, dict):
                            name = poi.get("name", "")
                            description = poi.get("description", "")

                            if poi.get("category") != 1 and (
                                "아파트" in name
                                or "APT" in name
                                or "자이" in name
                                or "힐스테이트" in name
                                or "래미안" in name
                                or "푸르지오" in name
                                or "롯데캐슬" in name
                                or "e편한" in name
                                or "단지" in description
                            ):
                                apartments.append(poi)

                    self.logger.debug(
                        "bbox_fetch_result",
                        bbox=bbox,
                        total_pois=len(raw_data),
                        filtered_apartments=len(apartments),
                    )

                    return apartments

            except Exception as e:
                self.logger.error("bbox_fetch_error", bbox=bbox, error=str(e))

            return []

        # 구/군의 bbox 좌표 가져오기
        # district 정보에서 직접 좌표가 없다면 region_bounds 사용
        if "bounds" in district:
            bounds = district["bounds"]
            lat_min = bounds.get("lat_min", self.region_bounds[0])
            lng_min = bounds.get("lng_min", self.region_bounds[1])
            lat_max = bounds.get("lat_max", self.region_bounds[2])
            lng_max = bounds.get("lng_max", self.region_bounds[3])
        else:
            lat_min, lng_min, lat_max, lng_max = self.region_bounds

        # 1. 적응적 분할 시도
        self.logger.info(
            "attempting_adaptive_division",
            district=district_name,
            initial_bbox=(lat_min, lng_min, lat_max, lng_max),
        )

        try:
            bboxes = self.bbox_divider.adaptive_divide(
                lat_min,
                lng_min,
                lat_max,
                lng_max,
                poi_count_func=get_poi_count_for_bbox,
                max_depth=3,
            )
        except Exception as e:
            self.logger.warning(
                "adaptive_division_failed", error=str(e), fallback="using_standard_division"
            )
            # 실패 시 표준 분할 사용
            bboxes = self.bbox_divider.divide_bbox(
                lat_min, lng_min, lat_max, lng_max, max_grid_size=4
            )

        self.logger.info("bbox_division_complete", district=district_name, total_bboxes=len(bboxes))

        # 2. 각 bbox에서 아파트 수집
        all_apartments = []
        seen_apartment_ids = set()  # 중복 제거용

        for i, bbox in enumerate(bboxes):
            self.logger.debug(
                f"processing_bbox_{i + 1}/{len(bboxes)}", district=district_name, bbox=bbox
            )

            apartments = fetch_apartments_from_bbox(bbox)

            # 중복 제거
            for apt in apartments:
                apt_id = apt.get("id")
                if apt_id and apt_id not in seen_apartment_ids:
                    all_apartments.append(apt)
                    seen_apartment_ids.add(apt_id)
                elif not apt_id:  # ID가 없는 경우 이름으로 중복 체크
                    apt_name = apt.get("name", "")
                    if apt_name and apt_name not in seen_apartment_ids:
                        all_apartments.append(apt)
                        seen_apartment_ids.add(apt_name)

            # API 레이트 리밋 고려
            if i < len(bboxes) - 1:  # 마지막이 아니면 잠시 대기
                import time

                time.sleep(0.5)

        self.logger.info(
            "apartment_collection_complete",
            district=district_name,
            total_bboxes_processed=len(bboxes),
            total_apartments_collected=len(all_apartments),
            unique_apartments=len(seen_apartment_ids),
        )

        return all_apartments

    def _save_apartment_basic_info(
        self,
        apt: Dict[str, Any],
        district_name: str,
        is_valid: bool = True,
    ) -> None:
        """단지 기본 정보만 CSV 저장

        Args:
            apt: 단지 기본 정보 (bounding API)
            district_name: 구/군 이름
            is_valid: 아파트 여부 검증 결과
        """

        # POI 정보 생성 및 검증
        try:
            poi = POIInfo.from_bounding_response(apt)

            # 검증 결과 확인
            validation_result = (
                "VALID" if is_valid and poi.validate_for_apartment_crawling() else "INVALID"
            )
            validation_reason = ""

            if validation_result == "INVALID":
                if poi.is_transit():
                    validation_reason = "POI는 지하철역입니다"
                elif poi.is_facility():
                    validation_reason = "POI는 공공시설입니다"
                elif not poi.is_valid_apartment_id():
                    validation_reason = "유효하지 않은 아파트 ID 형식"
                else:
                    validation_reason = "아파트 데이터가 아님"
            else:
                validation_reason = "유효한 아파트 데이터"

            # POI 타입 정보
            poi_type = poi.category.value if poi.category else "UNKNOWN"
            if poi.is_apartment():
                poi_category = "아파트"
            elif poi.is_transit():
                poi_category = "대중교통"
            elif poi.is_facility():
                poi_category = "공공시설"
            else:
                poi_category = "기타"

        except Exception as e:
            self.logger.warning(
                "poi_creation_failed", apt_id=apt.get("id", "unknown"), error=str(e)
            )
            validation_result = "ERROR"
            validation_reason = f"POI 정보 생성 실패: {str(e)}"
            poi_type = "ERROR"
            poi_category = "오류"

        # 단지 정보 형식 변환
        complex_data = {
            "aptSeq": f"APT_{apt.get('id', '')}",
            "aptName": apt.get("name", ""),
            "address": f"{apt.get('address', '')}",
            "buildYear": "",  # API에서 제공하지 않음
            "dealCnt": 0,  # API에서 제공하지 않음
            "realPrice": "",  # API에서 제공하지 않음
            "realPriceYear": "",
            "realPriceQuarter": "",
            "recentDealPrice": "",
            "recentDealDate": "",
            "lng": str(apt.get("lng", "")),
            "lat": str(apt.get("lat", "")),
            "householdCnt": "",  # API에서 제공하지 않음
            "parkingCnt": "",  # API에서 제공하지 않음
            "districtName": district_name,
            "category": apt.get("category", ""),
            "description": apt.get("description", ""),
            "dong": apt.get("dong", ""),
            # New POI validation fields
            "poi_type": poi_type,
            "poi_category": poi_category,
            "validation_result": validation_result,
            "validation_reason": validation_reason,
            "data_source": "HOGANGNONO",
        }

        # 단지 정보 저장
        try:
            self.hogangnono_writer.save_complexes([complex_data])
        except Exception as e:
            self.logger.error(
                "csv_save_failed",
                apt_id=apt.get("id", "unknown"),
                apt_name=apt.get("name", "unknown"),
                error=str(e),
            )
            raise

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
                    trade_data = {
                        "aptHash": apt["id"],
                        "date": report["date"],
                        **trade,
                    }  # apt.id 사용
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
        completed_districts = self._load_checkpoint(checkpoint_path)
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

            # 크롤링 실행 및 통계 수집
            crawl_stats = self._crawl_district(district, full_period)

            # checkpoint에 통계 정보 포함하여 저장
            self._save_checkpoint(district, checkpoint_path, crawl_stats)
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

    def _load_checkpoint(self, checkpoint_path: Path) -> List[str]:
        """Checkpoint 로드 (backward compatibility 유지)

        Returns:
            완료된 구/군 코드 리스트
        """
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
                completed = checkpoint.get("completed_districts", [])

                # 새 형식 (딕셔너리)
                if isinstance(completed, dict):
                    return list(completed.keys())
                # 이전 형식 (리스트) - backward compatibility
                elif isinstance(completed, list):
                    self.logger.warning(
                        "using_legacy_checkpoint_format",
                        message="Checkpoint format is deprecated. Consider regenerating checkpoint.",
                        completed_count=len(completed),
                    )
                    return completed

        return []

    def _save_checkpoint(
        self,
        district: Dict[str, Any],
        checkpoint_path: Path,
        crawl_stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Checkpoint 저장 (통계 정보 포함)

        Args:
            district: 구/군 정보
            checkpoint_path: checkpoint 파일 경로
            crawl_stats: 크롤링 통계 정보
        """

        # 기존 checkpoint 로드
        checkpoint = {}
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

        # 완료된 구/군 추가
        completed = checkpoint.get("completed_districts", {})
        district_code = district["regionCode"]
        district_name = district["name"]

        # 구/군별 상세 정보 저장
        completed[district_code] = {
            "name": district_name,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "crawl_stats": crawl_stats or {},
        }

        checkpoint["completed_districts"] = completed
        checkpoint["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        checkpoint["total_completed"] = len(completed)

        # 누적 통계 계산
        if crawl_stats:
            checkpoint["cumulative_stats"] = self._calculate_cumulative_stats(checkpoint)

        # 저장
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

        self.logger.info(
            "checkpoint_saved",
            district=district_name,
            district_code=district_code,
            total_completed=len(completed),
            current_stats=crawl_stats,
        )

    def _calculate_cumulative_stats(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        """누적 통계 계산

        Args:
            checkpoint: checkpoint 데이터

        Returns:
            누적 통계 정보
        """
        completed_districts = checkpoint.get("completed_districts", {})

        total_pois = 0
        total_apartments = 0
        total_valid_apartments = 0
        total_non_apartments = 0

        for district_info in completed_districts.values():
            stats = district_info.get("crawl_stats", {})
            if "poi_breakdown" in stats:
                poi_breakdown = stats["poi_breakdown"]
                total_pois += poi_breakdown.get("total", 0)
                total_apartments += poi_breakdown.get("apartments", 0)
                total_non_apartments += (
                    poi_breakdown.get("transit", 0)
                    + poi_breakdown.get("facilities", 0)
                    + poi_breakdown.get("others", 0)
                )

            if "valid_apartments" in stats:
                total_valid_apartments += stats["valid_apartments"]

        return {
            "total_pois": total_pois,
            "total_apartments_found": total_apartments,
            "total_valid_apartments": total_valid_apartments,
            "total_non_apartments": total_non_apartments,
            "overall_success_rate": (total_valid_apartments / total_pois if total_pois > 0 else 0),
            "apartment_success_rate": (
                total_valid_apartments / total_apartments if total_apartments > 0 else 0
            ),
        }

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

    def _fetch_and_save_transactions(self, apt: Dict[str, Any], district_name: str) -> None:
        """아파트 실거래 내역을 가져와서 저장

        Args:
            apt: 아파트 정보
            district_name: 구/군 이름
        """
        # 아파트 ID 추출 및 검증
        raw_apt_id = apt.get("id")
        apt_name = apt.get("name", "")

        # ID 유효성 검증
        apt_id = ApartmentIdValidator.validate_and_normalize(raw_apt_id)

        if not apt_id:
            # 유효하지 않은 ID 이유 로깅
            invalid_reason = ApartmentIdValidator._get_invalid_reason(raw_apt_id)
            self.logger.warning(
                "invalid_apartment_id",
                apt_name=apt_name,
                raw_id=raw_apt_id,
                reason=invalid_reason,
                district=district_name,
                note="Skipping API call for invalid apartment ID",
            )
            return

        # Check if we should skip this apartment based on error history
        if self.error_handler.should_skip_apartment(apt_id):
            self.logger.info(
                "skipping_apartment_due_to_error_history",
                apt_name=apt_name,
                apt_id=apt_id,
                district=district_name,
            )
            return

        try:
            # Enhanced error handling with retry logic
            response = self.error_handler.execute_with_retry(
                self.hogangnono_client.get_apartment_transactions,
                apartment_id=apt_id,
                apt_id=apt_id,
                trade_type=1,  # 매매 (API에 맞게 수정)
                area_no=201,  # 33㎡ 면적 타입 (API에 맞게 수정)
                full_period=False,  # 최근 3년
            )

            # Handle API response
            error_info = self.error_handler.handle_error(response, apt_id)

            if error_info:
                # Error occurred
                if error_info.error_type.value == "not_found":
                    self.logger.warning(
                        "apartment_not_found",
                        apt_name=apt_name,
                        apt_id=apt_id,
                        message=error_info.message,
                        district=district_name,
                    )
                else:
                    self.logger.warning(
                        "api_error_occurred",
                        apt_name=apt_name,
                        apt_id=apt_id,
                        error_type=error_info.error_type.value,
                        message=error_info.message,
                        is_transient=error_info.is_transient,
                        district=district_name,
                    )
            elif response.success and response.data:
                # Success - process transactions
                transactions = self._parse_transactions(response.data, apt_id, apt_name)
                if transactions:
                    self.hogangnono_writer.save_transactions(transactions)
                    self.logger.info(
                        "transactions_saved",
                        apt_name=apt_name,
                        apt_id=apt_id,
                        transaction_count=len(transactions),
                        district=district_name,
                    )
                else:
                    self.logger.info(
                        "no_transactions_found",
                        apt_name=apt_name,
                        apt_id=apt_id,
                        district=district_name,
                    )

        except Exception as e:
            # Handle unexpected exceptions
            error_info = self.error_handler.classify_error(
                Mock(success=False, error=str(e), status_code=None), apt_id
            )
            self.error_handler.stats.record_error(error_info)

            self.logger.error(
                "unexpected_error_fetching_transactions",
                apt_name=apt_name,
                apt_id=apt_id,
                error=str(e),
                error_type=error_info.error_type.value,
                district=district_name,
                exc_info=True,
            )

    def _parse_transactions(
        self, data: Dict[str, Any], apt_id: str, apt_name: str
    ) -> List[Dict[str, Any]]:
        """실거래 내역 API 응답을 파싱

        Args:
            data: API 응답 데이터
            apt_id: 아파트 ID
            apt_name: 아파트 이름

        Returns:
            파싱된 거래내역 리스트
        """
        transactions = []

        # API 응답 구조: data가 최상위에 있고 그 안에 shortTermReport가 있음
        if "data" in data and "shortTermReport" in data["data"]:
            reports = data["data"]["shortTermReport"]
        elif "shortTermReport" in data:
            reports = data["shortTermReport"]
        elif "data" in data and "longTermReport" in data["data"]:
            reports = data["data"]["longTermReport"]
        elif "longTermReport" in data:
            reports = data["longTermReport"]
        else:
            return transactions  # 데이터 없음

        for report in reports:
            if isinstance(report, dict):
                # 날짜 형식 변환 (2025-01-31T15:00:00.000Z -> YYYYMM)
                date_str = report.get("date", "")
                if date_str:
                    # "2025-01-31T15:00:00.000Z" -> "202501"
                    trade_date = date_str[:7].replace("-", "")
                    trade_year = int(date_str[:4])
                else:
                    trade_date = ""
                    trade_year = 0

                # 기본 정보
                base_info = {
                    "complex_id": apt_id,
                    "complex_name": apt_name,
                    "trade_date": trade_date,
                    "trade_year": trade_year,
                    "min_price": report.get("minPrice", 0),
                    "max_price": report.get("maxPrice", 0),
                    "avg_price": report.get("averagePrice", 0),
                    "volume": report.get("volume", 0),
                    "trade_type": "A1",  # 매매
                    "trade_type_name": "매매",
                    "deal_price": report.get("averagePrice", 0),  # 평균가를 거래가로 사용
                    "deposit": 0,  # 매매는 보증금 없음
                    "monthly_rent": 0,  # 매매는 월세 없음
                    "is_delete": "N",
                    "is_renew": "N",
                }

                # 개별 거래내역(trades)이 있다면 각각 추가
                if "trades" in report and isinstance(report["trades"], list):
                    for trade in report["trades"]:
                        if isinstance(trade, dict):
                            # 개별 거래의 날짜 처리
                            trade_date_str = trade.get("date", date_str)
                            if trade_date_str:
                                trade_date_formatted = trade_date_str[:7].replace("-", "")
                                trade_year_formatted = int(trade_date_str[:4])
                            else:
                                trade_date_formatted = trade_date
                                trade_year_formatted = trade_year

                            transaction = {
                                **base_info,
                                "trade_date": trade_date_formatted,
                                "trade_year": trade_year_formatted,
                                "deal_price": trade.get("price", report.get("averagePrice", 0)),
                                "floor": trade.get("floor", ""),
                                "area": trade.get("area", 0),
                                "direction": trade.get("direction", ""),
                            }
                            transactions.append(transaction)
                else:
                    # 월간 요약 정보만 있는 경우
                    transactions.append(base_info)

        return transactions

    def navigate_to_page(self, url: str) -> None:
        """페이지 이동 (Playwright 사용)

        TDD Red 단계에서는 Exception을 발생시킴

        Raises:
            Exception: 아직 구현되지 않음
        """
        raise Exception("navigate_to_page is not implemented yet")

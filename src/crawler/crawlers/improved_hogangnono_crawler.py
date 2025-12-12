"""
호갱노노 크롤러 통합 리팩토링 버전

이 모듈은 다음과 같은 개선 사항을 통합합니다:
1. 에러 핸들러 통합 및 404 에러 자동 스킵
2. API 호출 전 유효성 검증
3. 의존성 주입 방식 개선
4. 단순한 순차 처리
5. 환경별 설정 지원
"""

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime

from .api import APICrawler
from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..config import Config
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..utils.bbox_division import BBoxDivision
from ..utils.simple_error_handler import SimpleErrorHandler
from ..data_mappers import HogangnonoDataMapper
from ..validators.data_validator import ApartmentValidator, filter_apartments
from ..models.api_responses import POIInfo


@dataclass
class CrawlerDependencies:
    """크롤러 의존성 주입을 위한 데이터 클래스"""

    config: Config
    api_client: HogangnonoAPIClient
    data_mapper: HogangnonoDataMapper
    validator: ApartmentValidator
    error_handler: SimpleErrorHandler
    bbox_divider: BBoxDivision
    csv_writer: HogangnonoCSVWriter
    logger: logging.Logger


class ImprovedHogangnonoCrawler(APICrawler):
    """개선된 호갱노노 부동산 크롤러

    개선 사항:
    - 에러 핸들러 통합으로 404 에러 자동 스킵
    - API 호출 전 유효성 검증
    - 의존성 주입 방식으로 모듈화
    - 단순한 순차 처리
    - 환경별 설정 지원
    """

    def __init__(
        self,
        dependencies: CrawlerDependencies,
        output_dir: Union[Path, str] = "output",
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        """개선된 HogangnonoCrawler 초기화

        Args:
            dependencies: 주입된 의존성 객체들
            output_dir: 출력 디렉토리
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lat_max, lng_max)
        """
        # 의존성 저장
        self.deps = dependencies

        # 기본 설정
        base_url = dependencies.config.BASE_URL
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
            "User-Agent": dependencies.config.USER_AGENT,
        }

        # APICrawler 초기화
        super().__init__(
            config=dependencies.config,
            base_url=base_url,
            default_headers=default_headers,
            rate_limit_delay=dependencies.config.RATE_LIMIT_DELAY,
            timeout=dependencies.config.TIMEOUT,
        )

        # 출력 설정
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # CSV Writer (의존성 주입)
        self.csv_writer = dependencies.csv_writer

        # 지역 경계 설정
        self.region_bounds = region_bounds
        if not self.region_bounds:
            # 서울시 기본 경계 좌표
            self.region_bounds = (37.413294, 126.734086, 37.715133, 127.183394)

        self.logger.info(
            "improved_hogangnono_crawler_initialized",
            output_dir=str(self.output_dir),
            region_bounds=self.region_bounds,
        )

    def get_dong_code(self, district_name: str, dong_name: str) -> Optional[str]:
        """동 이름으로 코드 조회"""
        # DataMapper에서 정보 확인
        dong_code = self.deps.data_mapper.get_dong_code(district_name, dong_name)

        # 없으면 API에서 가져오기
        if not dong_code:
            try:
                dongs = self.deps.api_client.fetch_dong_codes(district_name)
                if dongs:
                    # DataMapper에 업데이트
                    self.deps.data_mapper.update_dong_code_mapping(district_name, dongs)
                    dong_code = dongs.get(dong_name)
            except Exception as e:
                self.logger.error(
                    "failed_to_fetch_dong_codes", district=district_name, error=str(e)
                )

        return dong_code

    def validate_apartment_before_request(self, apt_id: str, apt_name: str) -> bool:
        """API 호출 전 아파트 유효성 검증

        Args:
            apt_id: 아파트 ID
            apt_name: 아파트 이름

        Returns:
            True: 요청 진행, False: 스킵
        """
        # 에러 핸들러를 통해 스킵 여부 확인
        if self.deps.error_handler.should_skip_apartment(apt_id):
            self.logger.info(
                "apartment_skipped_by_error_handler",
                apt_id=apt_id,
                apt_name=apt_name,
                reason="previous_error_history",
            )
            return False

        # ID 형식 검증
        if not apt_id or not str(apt_id).isdigit():
            self.logger.warning("invalid_apartment_id_format", apt_id=apt_id, apt_name=apt_name)
            # 에러 핸들러에 등록
            self.deps.error_handler.mark_apartment_invalid(apt_id)
            return False

        # 이름에 아파트 관련 키워드 있는지 확인 (Defense-in-Depth)
        apt_keywords = [
            "아파트",
            "APT",
            "자이",
            "힐스테이트",
            "래미안",
            "푸르지오",
            "롯데캐슬",
            "e편한",
        ]
        if not any(keyword in apt_name for keyword in apt_keywords):
            self.logger.debug("suspicious_apartment_name", apt_id=apt_id, apt_name=apt_name)
            # 바로 스킵하지는 않고 경고만 로깅

        return True

    def fetch_apartment_data(
        self, apt_id: str, apt_name: str, fetch_func: callable, *args, **kwargs
    ) -> Optional[Any]:
        """아파트 데이터 조회

        Args:
            apt_id: 아파트 ID
            apt_name: 아파트 이름
            fetch_func: 데이터 조회 함수
            *args, **kwargs: 조회 함수에 전달할 인자

        Returns:
            조회된 데이터 또는 None
        """
        # API 호출 전 유효성 검증
        if not self.validate_apartment_before_request(apt_id, apt_name):
            return None

        # 데이터 조회
        try:
            # 에러 핸들러와 함께 실행
            response = self.deps.error_handler.execute_with_retry(
                fetch_func, *args, apartment_id=apt_id, **kwargs
            )

            # 성공 처리
            if hasattr(response, "success") and response.success:
                if hasattr(response, "data") and response.data:
                    return response.data

                return response.data
            else:
                # 404 에러 확인
                if hasattr(response, "status_code") and response.status_code == 404:
                    self.logger.info(
                        "apartment_not_found",
                        apt_id=apt_id,
                        apt_name=apt_name,
                    )
                else:
                    error_msg = getattr(response, "error", "Unknown error")
                    self.logger.warning(
                        "api_error_for_apartment",
                        apt_id=apt_id,
                        apt_name=apt_name,
                        error=error_msg,
                    )

                return None

        except Exception as e:
            self.logger.error(
                "unexpected_error_fetching_apartment",
                apt_id=apt_id,
                apt_name=apt_name,
                error=str(e),
                exc_info=True,
            )

            # 예외 처리 시 404 에러 확인
            if "404" in str(e).lower() and apt_id:
                self.deps.error_handler.mark_apartment_invalid(apt_id)

            return None

    def process_apartments_sequentially(
        self, apartments: List[Dict[str, Any]], process_func: callable, district_name: str = ""
    ) -> Dict[str, Any]:
        """아파트들을 순차적으로 처리

        Args:
            apartments: 처리할 아파트 리스트
            process_func: 아파트 처리 함수
            district_name: 구/군 이름

        Returns:
            처리 통계
        """
        stats = {
            "total": len(apartments),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
        }

        self.logger.info(
            "processing_apartments_sequentially",
            total_count=len(apartments),
            district=district_name,
        )

        for apt in apartments:
            apt_id = str(apt.get("id", ""))
            apt_name = apt.get("name", "")

            # 에러 핸들러로 스킵 확인
            if self.deps.error_handler.should_skip_apartment(apt_id):
                stats["skipped"] += 1
                continue

            try:
                # 처리 함수 실행
                result = process_func(apt, district_name)
                if result:
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                self.logger.error(
                    "sequential_processing_failed", apt_id=apt_id, apt_name=apt_name, error=str(e)
                )

        return stats

    def get_endpoint(self) -> str:
        """API 엔드포인트 반환"""
        return "/api/apt/bounding"

    def get_params(self) -> Dict[str, Any]:
        """API 요청 파라미터 반환"""
        lat_min, lng_min, lat_max, lng_max = self.region_bounds
        return {
            "lat_min": lat_min,
            "lng_min": lng_min,
            "lat_max": lat_max,
            "lng_max": lng_max,
            "zoom": 14,
            "limit": 100,
            "apt_type": "apart",
        }

    def parse_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱"""
        apartments = []

        # 응답 구조 파싱
        if "data" in response_data:
            data = response_data["data"]
            items = data if isinstance(data, list) else data.get("items", [])
        else:
            items = response_data if isinstance(response_data, list) else []

        # Defense-in-Depth: 아파트 데이터만 필터링
        valid_items, filter_stats = filter_apartments(items)

        self.logger.info(
            "data_filtering_applied",
            total_items=len(items),
            valid_items=len(valid_items),
            invalid_items=filter_stats["invalid"],
            invalid_reasons=filter_stats.get("reasons", {}),
        )

        # 데이터 매핑
        for item in valid_items:
            try:
                mapped_data = self.deps.data_mapper.map_to_naver_format(
                    item, fetch_dong_code_func=self.get_dong_code
                )
                if mapped_data:
                    apartments.append(mapped_data)
            except Exception as e:
                self.logger.error("failed_to_map_item", item=item, error=str(e))

        return apartments

    def crawl_and_save(
        self,
        regions: Optional[List[str]] = None,
        districts: Optional[List[str]] = None,
        full_period: bool = False,
    ) -> Dict[str, Any]:
        """크롤링과 저장 실행

        Args:
            regions: 시/도 코드 리스트
            districts: 구/군 코드 리스트
            full_period: 전체 기간 수집 여부

        Returns:
            크롤링 통계
        """
        start_time = datetime.now()

        try:
            # 1. 지역 정보 수집
            self.logger.info("fetching_regions")
            regions_response = self.deps.api_client.get_regions()
            if not regions_response.success:
                raise Exception(f"Failed to get regions: {regions_response.error}")

            all_regions = regions_response.data
            target_districts = self._filter_districts(all_regions, regions, districts)

            # 2. 구/군별 크롤링
            total_stats = {
                "districts_total": len(target_districts),
                "districts_completed": 0,
                "apartments_found": 0,
                "apartments_processed": 0,
                "transactions_found": 0,
                "errors": 0,
            }

            for district in target_districts:
                # 구/군 크롤링
                district_stats = self._crawl_district_improved(district, full_period)

                # 통계 집계
                total_stats["districts_completed"] += 1
                total_stats["apartments_found"] += district_stats.get("apartments_found", 0)
                total_stats["apartments_processed"] += district_stats.get("apartments_processed", 0)
                total_stats["transactions_found"] += district_stats.get("transactions_found", 0)
                total_stats["errors"] += district_stats.get("errors", 0)

            # 최종 통계
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            final_stats = {
                **total_stats,
                "duration_seconds": duration,
            }

            self.logger.info("crawling_completed", **final_stats)
            return final_stats

        except Exception as e:
            self.logger.error("crawling_failed", error=str(e), exc_info=True)
            raise

    def _filter_districts(
        self,
        all_regions: Dict[str, Any],
        regions: Optional[List[str]],
        districts: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """지역 필터링"""
        if not isinstance(all_regions, list):
            if isinstance(all_regions, dict) and "regionList" in all_regions:
                all_regions = all_regions["regionList"]
            else:
                return []

        # districts가 명시되면 해당 구/군만 반환
        if districts:
            result = []
            for region in all_regions:
                if isinstance(region, dict) and "children" in region:
                    for child in region["children"]:
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

    def _crawl_district_improved(
        self, district: Dict[str, Any], full_period: bool = False
    ) -> Dict[str, Any]:
        """개선된 구/군 크롤링

        Args:
            district: 구/군 정보
            full_period: 전체 기간 수집 여부

        Returns:
            구/군 크롤링 통계
        """
        district_code = district["regionCode"]
        district_name = district["name"]

        self.logger.info(
            "crawling_district_improved", district_code=district_code, district_name=district_name
        )

        stats = {
            "apartments_found": 0,
            "apartments_processed": 0,
            "transactions_found": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat(),
        }

        try:
            # 1. bbox 분할을 통한 아파트 수집
            apartments = self._fetch_apartments_with_bbox_division(district)
            stats["apartments_found"] = len(apartments)

            if apartments:
                # 2. 순차 처리로 아파트 데이터 수집
                def process_apartment(apt, district_name):
                    return self._process_single_apartment_improved(apt, district_name, full_period)

                sequential_stats = self.process_apartments_sequentially(
                    apartments, process_apartment, district_name
                )

                stats["apartments_processed"] = sequential_stats["processed"]
                stats["errors"] += sequential_stats["failed"]

        except Exception as e:
            stats["errors"] += 1
            self.logger.error(
                "district_crawling_failed", district=district_name, error=str(e), exc_info=True
            )

        stats["end_time"] = datetime.now().isoformat()
        return stats

    def _fetch_apartments_with_bbox_division(
        self, district: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """bbox 분할을 통한 아파트 수집"""
        district_name = district.get("name", "")

        # bbox 좌표 가져오기
        if "bounds" in district:
            bounds = district["bounds"]
            lat_min = bounds.get("lat_min", self.region_bounds[0])
            lng_min = bounds.get("lng_min", self.region_bounds[1])
            lat_max = bounds.get("lat_max", self.region_bounds[2])
            lng_max = bounds.get("lng_max", self.region_bounds[3])
        else:
            lat_min, lng_min, lat_max, lng_max = self.region_bounds

        # 적응적 분할 실행
        try:
            bboxes = self.deps.bbox_divider.adaptive_divide(
                lat_min,
                lng_min,
                lat_max,
                lng_max,
                poi_count_func=self._count_pois_in_bbox,
                max_depth=3,
            )
        except Exception as e:
            self.logger.warning("adaptive_division_failed", district=district_name, error=str(e))
            # 표준 분할로 fallback
            bboxes = self.deps.bbox_divider.divide_bbox(
                lat_min, lng_min, lat_max, lng_max, max_grid_size=4
            )

        # 각 bbox에서 아파트 수집
        all_apartments = []
        seen_ids = set()

        for bbox in bboxes:
            apartments = self._fetch_from_bbox(bbox)

            # 중복 제거
            for apt in apartments:
                apt_id = apt.get("id")
                if apt_id and apt_id not in seen_ids:
                    all_apartments.append(apt)
                    seen_ids.add(apt_id)

            # API 레이트 리밋
            time.sleep(1.0)

        return all_apartments

    def _count_pois_in_bbox(self, bbox: Tuple[float, float, float, float]) -> int:
        """bbox 내 POI 수 확인"""
        lat_min, lng_min, lat_max, lng_max = bbox

        search_params = SearchParams(
            bbox=(lng_min, lat_min, lng_max, lat_max),
            level=14,
            tradeType=0,
            aptType=1,
        )

        try:
            response = self.deps.api_client.get_apartments_bounding(search_params)
            if response.success:
                data = (
                    response.data.get("data", [])
                    if isinstance(response.data, dict)
                    else response.data or []
                )
                return len([poi for poi in data if isinstance(poi, dict)])
        except Exception as e:
            self.logger.warning(f"Failed to count POIs in bbox {bbox}: {e}")

        return 0

    def _fetch_from_bbox(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """단일 bbox에서 아파트 조회"""
        lat_min, lng_min, lat_max, lng_max = bbox

        search_params = SearchParams(
            bbox=(lng_min, lat_min, lng_max, lat_max),
            level=14,
            tradeType=0,
            aptType=1,
        )

        try:
            response = self.deps.api_client.get_apartments_bounding(search_params)
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
                        if poi.get("category") != 1 and (
                            "아파트" in name
                            or any(
                                keyword in name
                                for keyword in [
                                    "APT",
                                    "자이",
                                    "힐스테이트",
                                    "래미안",
                                    "푸르지오",
                                    "롯데캐슬",
                                    "e편한",
                                ]
                            )
                        ):
                            apartments.append(poi)

                return apartments
        except Exception as e:
            self.logger.error("bbox_fetch_error", bbox=bbox, error=str(e))

        return []

    def _process_single_apartment_improved(
        self, apt: Dict[str, Any], district_name: str, full_period: bool = False
    ) -> bool:
        """개선된 단일 아파트 처리

        Args:
            apt: 아파트 정보
            district_name: 구/군 이름
            full_period: 전체 기간 수집 여부

        Returns:
            처리 성공 여부
        """
        apt_id = str(apt.get("id", ""))
        apt_name = apt.get("name", "")

        # 1. 기본 정보 저장
        try:
            self._save_apartment_basic_info(apt, district_name)
        except Exception as e:
            self.logger.error(
                "failed_to_save_basic_info", apt_id=apt_id, apt_name=apt_name, error=str(e)
            )
            return False

        # 2. 실거래 내역 조회 (유효한 아파트만)
        if apt_id and apt_id.isdigit():
            transactions_data = self.fetch_apartment_data(
                apt_id,
                apt_name,
                self.deps.api_client.get_apartment_transactions,
                apartment_id=apt_id,
                apt_id=apt_id,
                trade_type=1,
                area_no=201,
                full_period=full_period,
            )

            if transactions_data:
                transactions = self._parse_transactions(transactions_data, apt_id, apt_name)
                if transactions:
                    try:
                        self.csv_writer.save_transactions(transactions)
                        self.logger.debug(
                            "transactions_saved", apt_id=apt_id, count=len(transactions)
                        )
                    except Exception as e:
                        self.logger.error(
                            "failed_to_save_transactions", apt_id=apt_id, error=str(e)
                        )

        return True

    def _save_apartment_basic_info(
        self,
        apt: Dict[str, Any],
        district_name: str,
        is_valid: bool = True,
    ) -> None:
        """아파트 기본 정보 저장"""
        # POI 정보 생성
        try:
            poi = POIInfo.from_bounding_response(apt)

            # 검증 결과
            validation_result = (
                "VALID" if is_valid and poi.validate_for_apartment_crawling() else "INVALID"
            )

            # POI 타입 확인
            if poi.is_apartment():
                poi_category = "아파트"
            elif poi.is_transit():
                poi_category = "대중교통"
            elif poi.is_facility():
                poi_category = "공공시설"
            else:
                poi_category = "기타"

        except Exception:
            validation_result = "ERROR"
            poi_category = "오류"

        # 단지 정보 변환
        complex_data = {
            "aptSeq": f"APT_{apt.get('id', '')}",
            "aptName": apt.get("name", ""),
            "address": f"{apt.get('address', '')}",
            "buildYear": "",
            "dealCnt": 0,
            "realPrice": "",
            "realPriceYear": "",
            "realPriceQuarter": "",
            "recentDealPrice": "",
            "recentDealDate": "",
            "lng": str(apt.get("lng", "")),
            "lat": str(apt.get("lat", "")),
            "householdCnt": "",
            "parkingCnt": "",
            "districtName": district_name,
            "category": apt.get("category", ""),
            "description": apt.get("description", ""),
            "dong": apt.get("dong", ""),
            "poi_category": poi_category,
            "validation_result": validation_result,
            "data_source": "HOGANGNONO",
        }

        # 저장
        self.csv_writer.save_complexes([complex_data])

    def _parse_transactions(
        self, data: Dict[str, Any], apt_id: str, apt_name: str
    ) -> List[Dict[str, Any]]:
        """실거래 내역 파싱"""
        transactions = []

        # 응답 구조 확인
        if "data" in data and "shortTermReport" in data["data"]:
            reports = data["data"]["shortTermReport"]
        elif "shortTermReport" in data:
            reports = data["shortTermReport"]
        else:
            return transactions

        for report in reports:
            if not isinstance(report, dict):
                continue

            # 날짜 처리
            date_str = report.get("date", "")
            if date_str:
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
                "deal_price": report.get("averagePrice", 0),
                "min_price": report.get("minPrice", 0),
                "max_price": report.get("maxPrice", 0),
                "volume": report.get("volume", 0),
                "trade_type": "A1",
                "trade_type_name": "매매",
            }

            # 개별 거래내역
            if "trades" in report and isinstance(report["trades"], list):
                for trade in report["trades"]:
                    if isinstance(trade, dict):
                        transaction = {
                            **base_info,
                            "deal_price": trade.get("price", report.get("averagePrice", 0)),
                            "floor": trade.get("floor", ""),
                            "area": trade.get("area", 0),
                            "direction": trade.get("direction", ""),
                        }
                        transactions.append(transaction)
            else:
                transactions.append(base_info)

        return transactions

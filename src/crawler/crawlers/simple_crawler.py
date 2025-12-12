"""
단순화된 호갱노노 크롤러

의존성 주입을 제거하고 직접 의존성을 생성하여 단순화한 버전입니다.
- 복잡한 캐싱 제거
- 통계 수집 제거
- 에러 핸들러 단순화
- 기본 크롤링 기능만 유지
"""

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..config import Config
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..utils.checkpoint import CheckpointManager
from ..data_mappers import HogangnonoDataMapper


class SimpleCrawler:
    """단순화된 호갱노노 부동산 크롤러

    기본 기능만 유지하고 복잡한 기능을 모두 제거:
    - 직접 의존성 생성 (DI 제거)
    - 간단한 bbox 분할 (고정 4x4 그리드)
    - 기본 체크포인트 기능
    - 단순화된 에러 처리
    """

    def __init__(
        self,
        output_dir: str = "output",
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        """SimpleCrawler 초기화

        Args:
            output_dir: 출력 디렉토리
            region_bounds: 크롤링할 지역 좌표 (lat_min, lng_min, lat_max, lng_max)
        """
        # 설정
        self.config = Config()
        self.base_url = self.config.BASE_URL

        # 출력 디렉토리
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 지역 경계
        if region_bounds:
            self.region_bounds = region_bounds
        else:
            # 서울시 기본 경계
            self.region_bounds = (37.413294, 126.734086, 37.715133, 127.183394)

        # 로거
        self.logger = logging.getLogger("simple_crawler")

        # 의존성 직접 생성
        self.api_client = HogangnonoAPIClient(self.config)
        self.data_mapper = HogangnonoDataMapper(
            dong_code_mapping_file=self.output_dir / "dong_code_mapping.json"
        )
        self.csv_writer = HogangnonoCSVWriter(output_dir=str(self.output_dir))
        self.checkpoint_manager = CheckpointManager(
            checkpoint_path=self.output_dir / "checkpoint.json"
        )

        # 간단한 상태 추적
        self.invalid_apartments = set()

        self.logger.info(
            f"SimpleCrawler initialized - output_dir: {self.output_dir}, "
            f"region_bounds: {self.region_bounds}"
        )

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

    def divide_bbox_simple(
        self, lat_min: float, lng_min: float, lat_max: float, lng_max: float, grid_size: int = 4
    ) -> List[Tuple[float, float, float, float]]:
        """단순한 고정 그리드로 bbox 분할"""
        lat_step = (lat_max - lat_min) / grid_size
        lng_step = (lng_max - lng_min) / grid_size

        bboxes = []
        for i in range(grid_size):
            for j in range(grid_size):
                bboxes.append(
                    (
                        lat_min + i * lat_step,
                        lng_min + j * lng_step,
                        lat_min + (i + 1) * lat_step,
                        lng_min + (j + 1) * lng_step,
                    )
                )

        return bboxes

    def fetch_apartments_from_bbox(
        self, bbox: Tuple[float, float, float, float]
    ) -> List[Dict[str, Any]]:
        """단일 bbox에서 아파트 조회"""
        lat_min, lng_min, lat_max, lng_max = bbox

        search_params = SearchParams(
            bbox=(lng_min, lat_min, lng_max, lat_max),
            level=14,
            tradeType=0,
            aptType=1,
        )

        try:
            response = self.api_client.get_apartments_bounding(search_params)
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
                        # 카테고리가 1이 아니거나 아파트 관련 키워드가 있는 경우
                        if poi.get("category") != 1 and "아파트" in name:
                            apartments.append(poi)

                return apartments
        except Exception as e:
            self.logger.error(f"bbox fetch error: {e}")

        return []

    def get_dong_code(self, district_name: str, dong_name: str) -> Optional[str]:
        """동 코드 조회"""
        return self.data_mapper.get_dong_code(district_name, dong_name)

    def save_apartment_info(self, apt: Dict[str, Any], district_name: str) -> None:
        """아파트 기본 정보 저장"""
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
            "poi_category": "아파트",
            "validation_result": "VALID",
            "data_source": "HOGANGNONO",
        }

        self.csv_writer.save_complexes([complex_data])

    def fetch_and_save_transactions(self, apt_id: str, apt_name: str) -> None:
        """아파트 실거래 내역 조회 및 저장"""
        if not apt_id or not apt_id.isdigit() or apt_id in self.invalid_apartments:
            return

        try:
            response = self.api_client.get_apartment_transactions(
                apartment_id=apt_id,
                apt_id=apt_id,
                trade_type=1,
                area_no=201,
                full_period=False,
            )

            if response.success and response.data:
                transactions = self._parse_transactions(response.data, apt_id, apt_name)
                if transactions:
                    self.csv_writer.save_transactions(transactions)
        except Exception as e:
            if "404" in str(e):
                self.invalid_apartments.add(apt_id)
            self.logger.error(f"Failed to fetch transactions for {apt_id}: {e}")

    def _parse_transactions(
        self, data: Dict[str, Any], apt_id: str, apt_name: str
    ) -> List[Dict[str, Any]]:
        """실거래 내역 파싱"""
        transactions = []

        if "data" in data and "shortTermReport" in data["data"]:
            reports = data["data"]["shortTermReport"]
        elif "shortTermReport" in data:
            reports = data["shortTermReport"]
        else:
            return transactions

        for report in reports:
            if not isinstance(report, dict):
                continue

            date_str = report.get("date", "")
            if date_str:
                trade_date = date_str[:7].replace("-", "")
                trade_year = int(date_str[:4])
            else:
                trade_date = ""
                trade_year = 0

            transaction = {
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

            transactions.append(transaction)

        return transactions

    def crawl_district(self, district: Dict[str, Any]) -> Dict[str, Any]:
        """단일 구/군 크롤링"""
        district_name = district["name"]

        self.logger.info(f"크롤링 시작: {district_name}")

        # bbox 분할
        if "bounds" in district:
            bounds = district["bounds"]
            lat_min = bounds.get("lat_min", self.region_bounds[0])
            lng_min = bounds.get("lng_min", self.region_bounds[1])
            lat_max = bounds.get("lat_max", self.region_bounds[2])
            lng_max = bounds.get("lng_max", self.region_bounds[3])
        else:
            lat_min, lng_min, lat_max, lng_max = self.region_bounds

        bboxes = self.divide_bbox_simple(lat_min, lng_min, lat_max, lng_max, grid_size=4)

        # 아파트 수집
        all_apartments = []
        seen_ids = set()

        for bbox in bboxes:
            apartments = self.fetch_apartments_from_bbox(bbox)
            for apt in apartments:
                apt_id = apt.get("id")
                if apt_id and apt_id not in seen_ids:
                    all_apartments.append(apt)
                    seen_ids.add(apt_id)

            # API 레이트 리밋
            time.sleep(1.0)

        # 아파트 정보 저장
        for apt in all_apartments:
            try:
                self.save_apartment_info(apt, district_name)
                self.fetch_and_save_transactions(str(apt.get("id", "")), apt.get("name", ""))
            except Exception as e:
                self.logger.error(f"Failed to process apartment: {e}")

        # 체크포인트 업데이트
        self.checkpoint_manager.add_completed_district(district_name)

        stats = {
            "district": district_name,
            "apartments_found": len(all_apartments),
            "processed": len(seen_ids),
        }

        self.logger.info(f"크롤링 완료: {district_name}, 아파트 {len(all_apartments)}개")
        return stats

    def crawl_and_save(
        self,
        regions: Optional[List[str]] = None,
        districts: Optional[List[str]] = None,
        full_period: bool = False,
    ) -> Dict[str, Any]:
        """크롤링 실행"""
        start_time = datetime.now()

        try:
            # 지역 정보 조회
            regions_response = self.api_client.get_regions()
            if not regions_response.success:
                raise Exception(f"Failed to get regions: {regions_response.error}")

            all_regions = regions_response.data
            target_districts = self._filter_districts(all_regions, regions, districts)

            total_stats = {
                "districts_total": len(target_districts),
                "districts_completed": 0,
                "apartments_found": 0,
                "errors": 0,
            }

            # 구/군별 크롤링
            for district in target_districts:
                district_name = district["name"]

                # 체크포인트 확인
                if self.checkpoint_manager.is_district_completed(district_name):
                    self.logger.info(f"건너뛰기: {district_name} (이미 완료)")
                    continue

                try:
                    district_stats = self.crawl_district(district)
                    total_stats["districts_completed"] += 1
                    total_stats["apartments_found"] += district_stats["apartments_found"]
                except Exception as e:
                    total_stats["errors"] += 1
                    self.logger.error(f"District {district_name} failed: {e}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            final_stats = {
                **total_stats,
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }

            self.logger.info(f"크롤링 완료: 총 {total_stats['apartments_found']}개 아파트")
            return final_stats

        except Exception as e:
            self.logger.error(f"크롤링 실패: {e}", exc_info=True)
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

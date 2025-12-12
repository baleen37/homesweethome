"""통합 아파트 크롤러

bbox 기반 크롤러와 검색 기반 크롤러를 통합하여
상황에 따라 최적의 방식으로 데이터를 수집합니다.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
import json
import time

from ..config import CrawlerConfig
from ..api.hogangnono_client import HogangnonoAPIClient
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
from ..coordinator.progress_tracker import ProgressTracker
from ..utils.bbox_division import BBoxDivision
from ..utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class CrawlMethod(Enum):
    """크롤링 방식 열거형"""

    AUTO = "auto"  # 자동 선택 (기본값)
    BBOX_ONLY = "bbox"  # bbox 기반만 사용
    SEARCH_ONLY = "search"  # 검색 기반만 사용
    HYBRID = "hybrid"  # 두 방식 모두 사용 후 병합


class IntegratedCrawler:
    """통합 아파트 크롤러"""

    def __init__(
        self,
        config: CrawlerConfig,
        output_dir: Path | str,
        method: CrawlMethod = CrawlMethod.AUTO,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
    ):
        """초기화

        Args:
            config: 크롤러 설정
            output_dir: 출력 디렉토리
            method: 크롤링 방식
            region_bounds: 크롤링할 지역 좌표
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.method = method

        # 지역 경계 설정
        if region_bounds:
            self.region_bounds = region_bounds
        else:
            # 서울시 기본 경계
            self.region_bounds = (37.413294, 126.734086, 37.715133, 127.183394)

        # 공통 컴포넌트 초기화
        self.api_client = HogangnonoAPIClient(config)
        self.writer = HogangnonoCSVWriter(str(self.output_dir))
        self.data_mapper = HogangnonoDataMapper(
            dong_code_mapping_file=self.output_dir / "dong_code_mapping.json"
        )
        self.progress_tracker = ProgressTracker(
            checkpoint_file=self.output_dir / "integrated_checkpoint.json"
        )
        self.checkpoint_manager = CheckpointManager(
            str(self.output_dir / "integrated_checkpoint.json")
        )

        # bbox 분할 유틸리티
        self.bbox_divider = BBoxDivision(max_pois_per_bbox=900)

        # 크롤러별 인스턴스 (지연 초기화)
        self._bbox_crawler = None
        self._search_crawler = None

        # 수집된 아파트 ID 저장 (중복 방지)
        self.collected_apartment_ids = set()

        logger.info(
            "integrated_crawler_initialized",
            method=method.value,
            output_dir=str(self.output_dir),
            region_bounds=self.region_bounds,
        )

    @property
    def bbox_crawler(self):
        """bbox 기반 크롤러 인스턴스 (지연 초기화)"""
        if self._bbox_crawler is None:
            from .hogangnono import HogangnonoCrawler

            self._bbox_crawler = HogangnonoCrawler(
                config=self.config,
                output_dir=self.output_dir,
                region_bounds=self.region_bounds,
            )
        return self._bbox_crawler

    @property
    def search_crawler(self):
        """검색 기반 크롤러 인스턴스 (지연 초기화)"""
        if self._search_crawler is None:
            from .apartment_search_crawler import ApartmentSearchCrawler

            self._search_crawler = ApartmentSearchCrawler(
                api_client=self.api_client,
                data_mapper=self.data_mapper,
                writer=self.writer,
                progress_tracker=self.progress_tracker,
            )
        return self._search_crawler

    async def crawl_all(
        self,
        regions: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        use_bbox: Optional[bool] = None,
        use_search: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """전체 크롤링 실행

        Args:
            regions: 대상 지역 목록 (bbox 기반)
            keywords: 검색 키워드 목록 (검색 기반)
            use_bbox: bbox 기반 사용 여부 (None이면 method에 따름)
            use_search: 검색 기반 사용 여부 (None이면 method에 따름)

        Returns:
            크롤링 통계 정보
        """
        start_time = time.time()

        # 체크포인트 로드
        checkpoint = self._load_checkpoint()
        logger.info("checkpoint_loaded", completed_methods=checkpoint.get("completed_methods", []))

        # 크롤링 방식 결정
        should_use_bbox, should_use_search = self._determine_crawl_methods(
            use_bbox, use_search, checkpoint
        )

        stats = {
            "method": self.method.value,
            "bbox_enabled": should_use_bbox,
            "search_enabled": should_use_search,
            "apartments_from_bbox": 0,
            "apartments_from_search": 0,
            "total_unique_apartments": 0,
            "duplicates_removed": 0,
            "duration_seconds": 0,
        }

        # bbox 기반 크롤링
        if should_use_bbox and "bbox" not in checkpoint.get("completed_methods", []):
            logger.info("starting_bbox_crawling")
            bbox_stats = await self._crawl_with_bbox(regions)
            stats["apartments_from_bbox"] = bbox_stats["apartments_count"]
            self._save_method_checkpoint("bbox", bbox_stats)

        # 검색 기반 크롤링
        if should_use_search and "search" not in checkpoint.get("completed_methods", []):
            logger.info("starting_search_crawling")
            search_stats = await self._crawl_with_search(keywords)
            stats["apartments_from_search"] = search_stats["apartments_count"]
            self._save_method_checkpoint("search", search_stats)

        # 중복 제거 및 통계 계산
        stats["total_unique_apartments"] = len(self.collected_apartment_ids)
        stats["duplicates_removed"] = (
            stats["apartments_from_bbox"]
            + stats["apartments_from_search"]
            - stats["total_unique_apartments"]
        )
        stats["duration_seconds"] = time.time() - start_time

        # 최종 체크포인트 저장
        if should_use_bbox and should_use_search:
            self._save_method_checkpoint("both", stats)

        logger.info("crawling_completed", **stats)

        return stats

    def _determine_crawl_methods(
        self, use_bbox: Optional[bool], use_search: Optional[bool], checkpoint: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        """사용할 크롤링 방식 결정"""
        completed_methods = checkpoint.get("completed_methods", [])

        # 명시적 지정이 있으면 우선
        if use_bbox is not None or use_search is not None:
            return (
                use_bbox if use_bbox is not None else False,
                use_search if use_search is not None else False,
            )

        # method에 따라 결정
        if self.method == CrawlMethod.BBOX_ONLY:
            return (True, False)
        elif self.method == CrawlMethod.SEARCH_ONLY:
            return (False, True)
        elif self.method == CrawlMethod.HYBRID:
            return (True, True)
        else:  # AUTO
            # 이전 실행 결과 확인
            if len(completed_methods) == 0:
                # 첫 실행은 bbox로 시도
                return (True, False)
            elif "bbox" in completed_methods and "search" not in completed_methods:
                # bbox가 완료됐으면 search 실행
                return (False, True)
            else:
                # 둘 다 완료됐거나 첫 실행이면 bbox부터
                return (True, False)

    async def _crawl_with_bbox(self, regions: Optional[List[str]]) -> Dict[str, Any]:
        """bbox 기반 크롤링 실행"""
        try:
            # 지역 정보 가져오기
            regions_response = self.api_client.get_regions()
            if not regions_response.success:
                raise Exception(f"Failed to get regions: {regions_response.error}")

            # 크롤링 실행
            crawl_stats = self.bbox_crawler.crawl(
                regions=regions,
                districts=None,
                full_period=False,
            )

            # 수집된 아파트 ID 업데이트
            # TODO: bbox 크롤러에서 ID 목록을 반환하도록 개선
            # 현재는 체크포인트 파일에서 읽어오는 방식으로 대체
            self._update_apartment_ids_from_csv()

            return {
                "apartments_count": crawl_stats.get("dongs_processed", 0),
                "regions_processed": len(regions) if regions else 1,
            }

        except Exception as e:
            logger.error("bbox_crawling_failed", error=str(e))
            raise

    async def _crawl_with_search(self, keywords: Optional[List[str]]) -> Dict[str, Any]:
        """검색 기반 크롤링 실행"""
        try:
            async with self.search_crawler as crawler:
                if keywords:
                    # 특정 키워드로 크롤링
                    await crawler.collect_by_region(keywords)
                else:
                    # 전체 키워드로 크롤링
                    await crawler.crawl_all_apartments()

                # 수집된 아파트 ID 업데이트
                self.collected_apartment_ids.update(crawler.collected_apt_ids)

                return {
                    "apartments_count": len(crawler.collected_apt_ids),
                    "keywords_processed": len(keywords)
                    if keywords
                    else len(crawler.search_keywords),
                }

        except Exception as e:
            logger.error("search_crawling_failed", error=str(e))
            raise

    def _update_apartment_ids_from_csv(self):
        """CSV 파일에서 아파트 ID 읽어오기"""
        try:
            complexes_file = self.output_dir / "complexes.csv"
            if complexes_file.exists():
                import csv

                with open(complexes_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        apt_id = row.get("aptSeq")
                        if apt_id and apt_id.startswith("APT_"):
                            self.collected_apartment_ids.add(apt_id)
        except Exception as e:
            logger.warning("failed_to_update_apartment_ids_from_csv", error=str(e))

    def _load_checkpoint(self) -> Dict[str, Any]:
        """체크포인트 로드"""
        if self.checkpoint_manager.checkpoint_path.exists():
            with open(self.checkpoint_manager.checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_method_checkpoint(self, method: str, stats: Dict[str, Any]):
        """크롤링 방식별 체크포인트 저장"""
        checkpoint = self._load_checkpoint()
        completed_methods = checkpoint.get("completed_methods", [])

        if method not in completed_methods:
            completed_methods.append(method)

        checkpoint["completed_methods"] = completed_methods
        checkpoint[f"{method}_stats"] = stats
        checkpoint["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        with open(self.checkpoint_manager.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

        logger.info("method_checkpoint_saved", method=method, stats=stats)

    async def crawl_specific_region(
        self, region_name: str, method: Optional[CrawlMethod] = None
    ) -> Dict[str, Any]:
        """특정 지역 크롤링

        Args:
            region_name: 지역명 (예: 'gangnam', 'songpa')
            method: 크롤링 방식 (None이면 기본값 사용)

        Returns:
            크롤링 통계 정보
        """
        # bbox 분할로 지역 가져오기
        try:
            bboxes = self.bbox_divider.get_region_bboxes(region_name)
        except ValueError:
            logger.error(f"unknown_region: {region_name}")
            return {"error": f"Unknown region: {region_name}"}

        # 방식 결정
        use_method = method or self.method

        stats = {
            "region": region_name,
            "method": use_method.value,
            "bboxes_count": len(bboxes),
            "apartments_count": 0,
        }

        if use_method in [CrawlMethod.BBOX_ONLY, CrawlMethod.HYBRID, CrawlMethod.AUTO]:
            # bbox로 수집
            all_apartments = []
            for i, bbox in enumerate(bboxes):
                logger.info(f"processing_bbox_{i + 1}/{len(bboxes)}", region=region_name)

                search_params = self.api_client.SearchParams(
                    bbox=(
                        bbox[1],
                        bbox[0],
                        bbox[3],
                        bbox[2],
                    ),  # (lng_min, lat_min, lng_max, lat_max)
                    level=14,
                    tradeType=0,
                    aptType=1,
                )

                response = self.api_client.get_apartments_bounding(search_params)
                if response.success:
                    apartments = self.bbox_crawler.parse_response(response.data)
                    all_apartments.extend(apartments)

            # 중복 제거
            unique_apartments = []
            for apt in all_apartments:
                apt_id = apt.get("complex_id")
                if apt_id and apt_id not in self.collected_apartment_ids:
                    unique_apartments.append(apt)
                    self.collected_apartment_ids.add(apt_id)

            # 저장
            if unique_apartments:
                self.bbox_crawler.save_to_hogangnono_csv(unique_apartments, [])

            stats["apartments_count"] = len(unique_apartments)

        # TODO: search 기반의 특정 지역 크롤링 구현
        # region_name으로 검색어 변환 후 ApartmentSearchCrawler 사용

        logger.info("region_crawling_completed", **stats)
        return stats

    def get_crawl_statistics(self) -> Dict[str, Any]:
        """크롤링 통계 정보 반환"""
        stats = self.writer.get_stats()
        checkpoint = self._load_checkpoint()

        return {
            "output_directory": str(self.output_dir),
            "total_apartments": self.collected_apartment_ids,
            "apartment_count": len(self.collected_apartment_ids),
            "csv_stats": stats,
            "checkpoint": checkpoint,
            "method": self.method.value,
        }

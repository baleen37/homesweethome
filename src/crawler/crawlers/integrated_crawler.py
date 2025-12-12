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
from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter
from ..coordinator.progress_tracker import ProgressTracker
from ..utils.bbox_division import BBoxDivision
from ..utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class CrawlMethod(Enum):
    """크롤링 방식 열거형"""

    AUTO = "auto"  # 자동 선택 (기본값)
    BBOX_ONLY = "bbox"  # bbox 기반만 사용


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
        self.progress_tracker = ProgressTracker(
            checkpoint_file=self.output_dir / "integrated_checkpoint.json"
        )
        self.checkpoint_manager = CheckpointManager(
            str(self.output_dir / "integrated_checkpoint.json")
        )

        # bbox 분할 유틸리티
        self.bbox_divider = BBoxDivision()

        # bbox 크롤러 인스턴스 (지연 초기화)
        self._bbox_crawler = None

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

    async def crawl_all(
        self,
        regions: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        use_bbox: Optional[bool] = None,
        use_search: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """전체 크롤링 실행 (bbox 기반만)

        Args:
            regions: 크롤링할 지역 목록
            keywords: 검색 키워드 목록 (사용하지 않음)
            use_bbox: bbox 기반 크롤링 사용 여부
            use_search: 검색 기반 크롤링 사용 여부 (사용하지 않음)

        Returns:
            크롤링 통계 정보
        """
        start_time = time.time()

        # 체크포인트 로드
        checkpoint = self._load_checkpoint()
        logger.info("checkpoint_loaded", completed_methods=checkpoint.get("completed_methods", []))

        # bbox 크롤링만 사용
        if use_search:
            logger.warning(
                "search_based_crawling_deprecated",
                message="검색 기반 크롤링은 더 이상 지원되지 않습니다. bbox 기반만 사용합니다.",
            )

        stats = {
            "method": self.method.value,
            "apartments_count": 0,
            "duration_seconds": 0,
        }

        # bbox 기반 크롤링
        if "bbox" not in checkpoint.get("completed_methods", []):
            logger.info("starting_bbox_crawling")
            bbox_stats = await self._crawl_with_bbox(regions)
            stats["apartments_count"] = bbox_stats["apartments_count"]
            self._save_method_checkpoint("bbox", bbox_stats)
        else:
            # 이미 완료된 경우 CSV에서 아파트 ID 로드
            self._update_apartment_ids_from_csv()
            stats["apartments_count"] = len(self.collected_apartment_ids)

        stats["duration_seconds"] = time.time() - start_time
        logger.info("crawling_completed", **stats)

        return stats

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

                search_params = SearchParams(
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

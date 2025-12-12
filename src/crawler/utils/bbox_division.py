"""Bounding box 분할 유틸리티

POI API의 1000개 제한 문제를 해결하기 위해 bbox를 작은 격자로 분할하는 기능을 제공합니다.
"""

import math
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BBoxDivision:
    """Bounding box 분할 유틸리티 클래스"""

    def __init__(self, max_pois_per_bbox: int = 900):
        """초기화

        Args:
            max_pois_per_bbox: bbox당 최대 POI 수 (기본값: 900, 1000개 제한에 마진 포함)
        """
        self.max_pois_per_bbox = max_pois_per_bbox

    def calculate_optimal_grid_size(
        self,
        lat_min: float,
        lng_min: float,
        lat_max: float,
        lng_max: float,
        estimated_pois: Optional[int] = None,
    ) -> Tuple[int, int]:
        """최적의 격자 크기 계산

        Args:
            lat_min: 최소 위도
            lng_min: 최소 경도
            lat_max: 최대 위도
            lng_max: 최대 경도
            estimated_pois: 추정 POI 수 (없으면 면적으로 추정)

        Returns:
            (행 개수, 열 개수) 튜플
        """
        # bbox 면적 계산 (대략적인)
        lat_diff = lat_max - lat_min
        lng_diff = lng_max - lng_min
        area = lat_diff * lng_diff

        # POI 밀도 기반 추정 (서울 기준 약 5000 POI / 1도²)
        if estimated_pois is None:
            estimated_pois = int(area * 5000)

        # 필요한 격자 수 계산
        required_grids = math.ceil(estimated_pois / self.max_pois_per_bbox)

        # 정사각형에 가깝게 격자 크기 결정
        rows = math.ceil(math.sqrt(required_grids * (lat_diff / lng_diff)))
        cols = math.ceil(required_grids / rows)

        # 최소/최대 격자 수 제한
        rows = max(1, min(20, rows))
        cols = max(1, min(20, cols))

        logger.info(f"Grid size calculated: {rows}x{cols} for {estimated_pois} estimated POIs")

        return rows, cols

    def divide_bbox(
        self, lat_min: float, lng_min: float, lat_max: float, lng_max: float, max_grid_size: int = 5
    ) -> List[Tuple[float, float, float, float]]:
        """bbox를 격자로 분할

        Args:
            lat_min: 최소 위도
            lng_min: 최소 경도
            lat_max: 최대 위도
            lng_max: 최대 경도
            max_grid_size: 최대 격자 크기 (행/열)

        Returns:
            분할된 bbox 리스트 [(lat_min, lng_min, lat_max, lng_max), ...]
        """
        # 최적 격자 크기 계산
        rows, cols = self.calculate_optimal_grid_size(lat_min, lng_min, lat_max, lng_max)

        # 최대 격자 크기 제한
        rows = min(rows, max_grid_size)
        cols = min(cols, max_grid_size)

        lat_step = (lat_max - lat_min) / rows
        lng_step = (lng_max - lng_min) / cols

        bboxes = []

        for row in range(rows):
            for col in range(cols):
                sub_lat_min = lat_min + (row * lat_step)
                sub_lat_max = lat_min + ((row + 1) * lat_step)
                sub_lng_min = lng_min + (col * lng_step)
                sub_lng_max = lng_min + ((col + 1) * lng_step)

                bboxes.append((sub_lat_min, sub_lng_min, sub_lat_max, sub_lng_max))

        logger.info(
            f"Divided bbox into {len(bboxes)} grids ({rows}x{cols}) "
            f"for area ({lat_min:.3f}, {lng_min:.3f}) to ({lat_max:.3f}, {lng_max:.3f})"
        )

        return bboxes

    def adaptive_divide(
        self,
        lat_min: float,
        lng_min: float,
        lat_max: float,
        lng_max: float,
        poi_count_func: callable,
        max_depth: int = 3,
    ) -> List[Tuple[float, float, float, float]]:
        """적응적 bbox 분할 (POI 수에 따라 동적으로 분할)

        Args:
            lat_min: 최소 위도
            lng_min: 최소 경도
            lat_max: 최대 위도
            lng_max: 최대 경도
            poi_count_func: bbox를 인자로 받아 POI 수를 반환하는 함수
            max_depth: 최대 분할 깊이

        Returns:
            분할된 bbox 리스트
        """

        def divide_recursive(
            bbox: Tuple[float, float, float, float], depth: int = 0
        ) -> List[Tuple[float, float, float, float]]:
            lat_min, lng_min, lat_max, lng_max = bbox

            # 현재 bbox의 POI 수 확인
            try:
                poi_count = poi_count_func(bbox)
                logger.debug(f"Bbox {bbox} has {poi_count} POIs at depth {depth}")
            except Exception as e:
                logger.warning(f"Failed to get POI count for {bbox}: {e}")
                poi_count = 0

            # POI 수가 적거나 최대 깊이에 도달하면 분할 중단
            if poi_count <= self.max_pois_per_bbox or depth >= max_depth:
                return [bbox]

            # 2x2로 분할
            sub_boxes = self._divide_quad(bbox)

            # 재귀적으로 각 서브 bbox 처리
            result = []
            for sub_box in sub_boxes:
                result.extend(divide_recursive(sub_box, depth + 1))

            return result

        bboxes = divide_recursive((lat_min, lng_min, lat_max, lng_max))

        logger.info(
            f"Adaptive division resulted in {len(bboxes)} bboxes "
            f"for initial bbox ({lat_min:.3f}, {lng_min:.3f}) to ({lat_max:.3f}, {lng_max:.3f})"
        )

        return bboxes

    def _divide_quad(
        self, bbox: Tuple[float, float, float, float]
    ) -> List[Tuple[float, float, float, float]]:
        """bbox를 4개로 분할 (2x2)

        Args:
            bbox: (lat_min, lng_min, lat_max, lng_max)

        Returns:
            4개의 bbox 리스트
        """
        lat_min, lng_min, lat_max, lng_max = bbox
        lat_mid = (lat_min + lat_max) / 2
        lng_mid = (lng_min + lng_max) / 2

        return [
            (lat_min, lng_min, lat_mid, lng_mid),  # 남서
            (lat_min, lng_mid, lat_mid, lng_max),  # 남동
            (lat_mid, lng_min, lat_max, lng_mid),  # 북서
            (lat_mid, lng_mid, lat_max, lng_max),  # 북동
        ]

    def optimize_division_for_seoul(self) -> List[Tuple[float, float, float, float]]:
        """서울 특별시용 최적화 bbox 분할

        Returns:
            서울을覆盖하는 bbox 리스트
        """
        # 서울시 경계 좌표
        seoul_bounds = (37.413294, 126.734086, 37.715133, 127.183394)

        # 서울은 5x5 격자로 분할 (지역별 특성 고려)
        return self.divide_bbox(*seoul_bounds, max_grid_size=5)

    def get_region_bboxes(self, region_name: str) -> List[Tuple[float, float, float, float]]:
        """주요 지역별 bbox 반환

        Args:
            region_name: 지역명 (예: 'seoul', 'gangnam', 'songpa')

        Returns:
            해당 지역의 bbox 리스트
        """
        # 주요 지역 경계 좌표
        regions = {
            "seoul": (37.413294, 126.734086, 37.715133, 127.183394),
            "gangnam": (37.495, 127.045, 37.525, 127.095),
            "songpa": (37.490, 127.100, 37.550, 127.150),
            "nowon": (37.620, 127.050, 37.680, 127.120),
            "yeongdeungpo": (37.510, 126.880, 37.540, 126.920),
            "jongno": (37.560, 126.970, 37.590, 127.010),
            "mapo": (37.540, 126.900, 37.570, 126.950),
            "gwangjin": (37.530, 127.070, 37.570, 127.110),
            "dongdaemun": (37.570, 127.040, 127.620, 127.080),
            "seocho": (37.465, 127.000, 37.515, 127.030),
        }

        if region_name.lower() not in regions:
            raise ValueError(f"Unknown region: {region_name}")

        bounds = regions[region_name.lower()]

        # 작은 지역은 2x2로, 서울 전체는 5x5로 분할
        if region_name.lower() == "seoul":
            return self.divide_bbox(*bounds, max_grid_size=5)
        else:
            return self.divide_bbox(*bounds, max_grid_size=2)

"""단순화된 Bounding box 분할 유틸리티

고정 4x4 그리드로 bbox를 분합니다.
"""

from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class BBoxDivision:
    """단순화된 Bounding box 분할 유틸리티 클래스"""

    # 주요 지역의 bbox 정의 (region_name: (lat_min, lng_min, lat_max, lng_max))
    REGION_BBOXES = {
        "gangnam": (37.495, 127.045, 37.535, 127.115),
        "songpa": (37.485, 127.115, 37.545, 127.185),
        "seoul": (37.413294, 126.734086, 37.715133, 127.183394),
        "busan": (35.095, 128.950, 35.235, 129.190),
        "daegu": (35.800, 128.550, 35.950, 128.750),
    }

    def divide_bbox(
        self, lat_min: float, lng_min: float, lat_max: float, lng_max: float
    ) -> List[Tuple[float, float, float, float]]:
        """bbox를 고정 4x4 그리드로 분할

        Args:
            lat_min: 최소 위도
            lng_min: 최소 경도
            lat_max: 최대 위도
            lng_max: 최대 경도

        Returns:
            분할된 bbox 리스트 [(lat_min, lng_min, lat_max, lng_max), ...]
        """
        # 고정된 4x4 그리드 사용
        rows, cols = 4, 4

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

    def get_region_bboxes(self, region_name: str) -> List[Tuple[float, float, float, float]]:
        """지역 이름에 해당하는 bbox들을 반환

        Args:
            region_name: 지역 이름 (예: gangnam, songpa, seoul)

        Returns:
            분할된 bbox 리스트

        Raises:
            ValueError: 지원하지 않는 지역인 경우
        """
        region_name = region_name.lower()

        if region_name not in self.REGION_BBOXES:
            raise ValueError(
                f"지원하지 않는 지역입니다: {region_name}. "
                f"지원하는 지역: {', '.join(self.REGION_BBOXES.keys())}"
            )

        lat_min, lng_min, lat_max, lng_max = self.REGION_BBOXES[region_name]
        return self.divide_bbox(lat_min, lng_min, lat_max, lng_max)

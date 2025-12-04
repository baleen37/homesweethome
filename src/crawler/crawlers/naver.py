import json
from pathlib import Path
from typing import Any

from crawler.crawlers.base import BaseCrawler
from crawler.utils.checkpoint import CheckpointManager


class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()

    def get_url(self) -> str:
        return "https://new.land.naver.com/complexes"

    def fetch(self, url: str) -> str:
        # 이 메서드는 사용하지 않지만 추상 메서드이므로 구현 필요
        return ""

    def parse(self, html: str) -> list[dict[str, Any]]:
        # 이 메서드는 사용하지 않지만 추상 메서드이므로 구현 필요
        return []

    def _load_districts_data(self) -> dict[str, Any]:
        data_path = Path(__file__).parent.parent / "data" / "seoul_districts.json"
        with open(data_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _parse_api_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        items = response.get("list", [])
        results = []

        for item in items:
            results.append(
                {
                    "marker_id": item["markerId"],
                    "complex_name": item["complexName"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "real_estate_type": item["realEstateTypeName"],
                    "completion_year_month": item["completionYearMonth"],
                    "total_dong_count": item["totalDongCount"],
                    "total_household_count": item["totalHouseholdCount"],
                    "floor_area_ratio": item["floorAreaRatio"],
                    "min_area": item["minArea"],
                    "max_area": item["maxArea"],
                    "deal_count": item["dealCount"],
                    "lease_count": item["leaseCount"],
                    "total_article_count": item["totalArticleCount"],
                }
            )

        self.logger.info("parsed_complexes", count=len(results))
        return results

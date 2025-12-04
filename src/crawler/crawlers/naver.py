import json
from pathlib import Path
from typing import Any

import structlog

from crawler.config import CrawlerConfig
from crawler.utils.checkpoint import CheckpointManager


class NaverRealEstateCrawler:
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.logger = structlog.get_logger()
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()
        self.page: Any = None  # Playwright page object

    def get_url(self) -> str:
        return "https://new.land.naver.com/complexes"

    def _load_districts_data(self) -> dict[str, Any]:
        data_path = Path(__file__).parent.parent / "data" / "seoul_districts.json"
        with open(data_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _fetch_dong_data(self, dong: dict[str, Any]) -> list[dict[str, Any]]:
        cortar_no = dong["cortarNo"]
        bounds = dong["bounds"]

        api_url = (
            f"https://new.land.naver.com/api/complexes/single-markers/2.0?"
            f"cortarNo={cortar_no}&"
            f"zoom=17&"
            f"priceType=RETAIL&"
            f"realEstateType=APT&"
            f"tradeType=A1&"
            f"leftLon={bounds['leftLon']}&"
            f"rightLon={bounds['rightLon']}&"
            f"topLat={bounds['topLat']}&"
            f"bottomLat={bounds['bottomLat']}"
        )

        self.logger.info(
            "fetching_dong_data",
            dong=dong.get("dong_name", ""),
            cortar_no=cortar_no,
        )

        result = self.page.evaluate(
            """
            async (url) => {
                const response = await fetch(url);
                return await response.json();
            }
            """,
            api_url,
        )

        return self._parse_api_response(result)

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

import json
import time
from pathlib import Path
from typing import Any

import structlog
from playwright.sync_api import sync_playwright

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

    def _fetch_with_retry(self, dong: dict[str, Any], max_retries: int = 3) -> list[dict[str, Any]]:
        for attempt in range(max_retries):
            try:
                data = self._fetch_dong_data(dong)
                time.sleep(0.5)  # Rate limiting
                return data
            except TimeoutError:
                self.logger.warning(
                    "fetch_timeout",
                    dong=dong.get("dong_name", ""),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt == max_retries - 1:
                    self.checkpoint_manager.add_failed_dong(dong, "Timeout after retries")
                    return []
                time.sleep(2**attempt)  # 지수 백오프
            except Exception as e:
                self.logger.error(
                    "fetch_error",
                    dong=dong.get("dong_name", ""),
                    error=str(e),
                )
                self.checkpoint_manager.add_failed_dong(dong, str(e))
                return []
        return []

    def crawl(self) -> list[dict[str, Any]]:
        """서울시 전체 구/동을 순회하며 크롤링"""
        self.logger.info("crawling_start")

        # 체크포인트 로드
        checkpoint = self.checkpoint_manager.load()
        if checkpoint:
            self.logger.info("checkpoint_loaded", checkpoint=checkpoint["last_completed"])

        all_results: list[dict[str, Any]] = []
        url = self.get_url()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            self.page = browser.new_page()
            self.page.goto(url, timeout=self.config.timeout * 1000)
            self.page.wait_for_load_state("networkidle")

            self.logger.info("browser_ready")

            total_dongs = sum(
                len(district["dongs"]) for district in self.districts_data["districts"]
            )
            completed_count = 0

            for district in self.districts_data["districts"]:
                for dong in district["dongs"]:
                    # 체크포인트에서 완료된 동 건너뛰기
                    if self.checkpoint_manager.should_skip_dong(dong["cortarNo"]):
                        self.logger.info("skipping_completed_dong", dong=dong["dong_name"])
                        completed_count += 1
                        continue

                    self.logger.info(
                        "crawling_dong",
                        district=district["district_name"],
                        dong=dong["dong_name"],
                        progress=f"{completed_count}/{total_dongs}",
                    )

                    results = self._fetch_with_retry(dong)
                    all_results.extend(results)

                    # 체크포인트 업데이트
                    self.checkpoint_manager.checkpoint["last_completed"] = {
                        "district": district["district_name"],
                        "dong": dong["dong_name"],
                    }
                    self.checkpoint_manager.checkpoint.setdefault("completed_dongs", []).append(
                        dong["cortarNo"]
                    )
                    self.checkpoint_manager.checkpoint["total_complexes_crawled"] = len(all_results)
                    self.checkpoint_manager.save(self.checkpoint_manager.checkpoint)

                    completed_count += 1

            browser.close()

        self.logger.info("crawling_complete", total_complexes=len(all_results))
        return all_results

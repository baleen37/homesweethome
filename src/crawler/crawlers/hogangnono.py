"""호갱노노 전용 크롤러 구현

BaseCrawler를 상속받아 Playwright 기반으로 호갱노노 부동산 데이터를 수집합니다.
"""

from __future__ import annotations

from typing import Any, List, Optional

from bs4 import BeautifulSoup

from .base import BaseCrawler
from ..config import CrawlerConfig
from ..utils.browser_manager import BrowserManager


class HogangnonoCrawler(BaseCrawler):
    """호갱노노 부동산 크롤러

    BaseCrawler를 상속받아 Playwright를 통해 호갱노노 사이트의 데이터를 수집합니다.
    - 지역(구/동) 기반 검색
    - 동적 로딩 되는 매물 목록 추출
    - 상세 정보 접근 및 파싱
    """

    def __init__(self, config: CrawlerConfig) -> None:
        """HogangnonoCrawler 초기화

        Args:
            config: 크롤러 설정
        """
        super().__init__(config)

        # Playwright를 위한 BrowserManager 초기화
        self.browser_manager = BrowserManager(config)

        # 기본 URL
        self.base_url = "https://hogangnono.com"

        self.logger.info(
            "hogangnono_crawler_initialized",
            base_url=self.base_url,
            headless=config.headless,
        )

    def get_url(self) -> str:
        """크롤링할 URL 반환

        Returns:
            호갱노노 기본 URL
        """
        return self.base_url

    def fetch(self, url: str) -> str:
        """Playwright를 사용하여 HTML 가져오기

        Args:
            url: 가져올 URL

        Returns:
            HTML 문자열

        Raises:
            Exception: 페이지 로드 실패 시
        """
        try:
            with self.browser_manager.managed_browser() as page:
                # 페이지 이동
                page.goto(url)

                # 네트워크 유휴 상태 대기 (JavaScript 실행 완료)
                page.wait_for_load_state("networkidle")

                # HTML 콘텐츠 가져오기
                html_content = page.content()

                self.logger.info(
                    "page_loaded_successfully",
                    url=url,
                    content_length=len(html_content),
                )

                return html_content

        except Exception as e:
            self.logger.error(
                "failed_to_fetch_page",
                url=url,
                error=str(e),
            )
            raise

    def parse(self, html: str) -> List[dict[str, Any]]:
        """HTML 파싱하여 부동산 데이터 추출

        Args:
            html: 파싱할 HTML 문자열

        Returns:
            추출된 부동산 데이터 리스트
        """
        if not html:
            self.logger.warning("empty_html_received")
            return []

        try:
            # BeautifulSoup으로 HTML 파싱
            soup = BeautifulSoup(html, "html.parser")

            # 부동산 매물 목록 추출
            listings = self._parse_listings_from_html(soup)

            self.logger.info(
                "html_parsed_successfully",
                listings_count=len(listings),
            )

            return listings

        except Exception as e:
            self.logger.error(
                "failed_to_parse_html",
                error=str(e),
                html_length=len(html),
            )
            return []

    def _parse_listings_from_html(self, soup: BeautifulSoup) -> List[dict[str, Any]]:
        """BeautifulSoup 객체에서 매물 목록 추출

        Args:
            soup: BeautifulSoup 객체

        Returns:
            추출된 매물 정보 리스트
        """
        listings = []

        try:
            # 실제 호갱노노 사이트의 CSS 선택자 (예시)
            # TODO: 실제 사이트 구조에 맞게 선택자 업데이트 필요
            items = soup.find_all("div", {"data-testid": "real-estate-item"})

            if not items:
                # 다른 가능한 선택자 시도
                items = soup.find_all("div", class_="property-item")
                if not items:
                    items = soup.find_all("li", class_="search-item")

            for item in items:
                try:
                    # 각 매물 정보 추출
                    listing_data = self._extract_listing_data(item)

                    if listing_data:
                        listings.append(listing_data)

                except Exception as e:
                    self.logger.warning(
                        "failed_to_extract_listing",
                        error=str(e),
                    )
                    continue

        except Exception as e:
            self.logger.error(
                "failed_to_parse_listings",
                error=str(e),
            )

        return listings

    def _extract_listing_data(self, item) -> Optional[dict[str, Any]]:
        """개별 매물 정보 추출

        Args:
            item: BeautifulSoup item element

        Returns:
            추출된 매물 정보 또는 None
        """
        try:
            # 가격 정보 추출
            price_element = item.find("div", class_="price")
            price = price_element.get_text(strip=True) if price_element else ""

            # 면적 정보 추출
            area_element = item.find("div", class_="area")
            area = area_element.get_text(strip=True) if area_element else ""

            # 층 정보 추출
            floor_element = item.find("div", class_="floor")
            floor = floor_element.get_text(strip=True) if floor_element else ""

            # 날짜 정보 추출
            date_element = item.find("div", class_="date")
            date = date_element.get_text(strip=True) if date_element else ""

            # 단지명 추출
            complex_element = item.find("div", class_="complex-name")
            complex_name = complex_element.get_text(strip=True) if complex_element else ""

            # 주소 정보 추출
            address_element = item.find("div", class_="address")
            address = address_element.get_text(strip=True) if address_element else ""

            # 필수 정보가 있으면 데이터 반환
            if price or complex_name:
                return {
                    "price": price,
                    "area": area,
                    "floor": floor,
                    "date": date,
                    "complex_name": complex_name,
                    "address": address,
                }

        except Exception as e:
            self.logger.warning(
                "failed_to_extract_item_data",
                error=str(e),
            )

        return None

    def crawl_region(self, district: str, dong: Optional[str] = None) -> List[dict[str, Any]]:
        """지역별 크롤링 실행

        Args:
            district: 구 이름 (예: "강남구")
            dong: 동 이름 (선택적)

        Returns:
            수집된 부동산 데이터 리스트
        """
        try:
            search_query = f"{district} {dong or ''}".strip()

            with self.browser_manager.managed_browser() as page:
                # 1. 사이트 접속
                page.goto(self.base_url)
                page.wait_for_load_state("networkidle")

                # 2. 검색창에 지역 입력
                # TODO: 실제 검색창 선택자에 맞게 수정 필요
                search_input = page.locator(
                    'input[placeholder*="지역"], input[placeholder*="검색"]'
                )
                if search_input.count() > 0:
                    search_input.fill(search_query)
                    page.keyboard.press("Enter")

                    # 3. 검색 결과 로딩 대기
                    page.wait_for_load_state("networkidle")

                    # 추가 로딩을 위해 잠시 대기
                    page.wait_for_timeout(2000)

                    # 4. 현재 페이지의 HTML 가져오기
                    html = page.content()

                    # 5. 데이터 파싱
                    listings = self.parse(html)

                    self.logger.info(
                        "region_crawl_completed",
                        district=district,
                        dong=dong,
                        search_query=search_query,
                        listings_count=len(listings),
                    )

                    return listings
                else:
                    self.logger.warning(
                        "search_input_not_found",
                        district=district,
                        dong=dong,
                    )
                    return []

        except Exception as e:
            self.logger.error(
                "failed_to_crawl_region",
                district=district,
                dong=dong,
                error=str(e),
            )
            return []

    def crawl_with_pagination(
        self, district: str, dong: Optional[str] = None, max_pages: int = 5
    ) -> List[dict[str, Any]]:
        """페이지네이션 포함 크롤링

        Args:
            district: 구 이름
            dong: 동 이름
            max_pages: 최대 페이지 수

        Returns:
            수집된 부동산 데이터 리스트
        """
        all_listings = []

        try:
            search_query = f"{district} {dong or ''}".strip()

            with self.browser_manager.managed_browser() as page:
                # 1. 사이트 접속 및 검색
                page.goto(self.base_url)
                page.wait_for_load_state("networkidle")

                search_input = page.locator(
                    'input[placeholder*="지역"], input[placeholder*="검색"]'
                )
                if search_input.count() > 0:
                    search_input.fill(search_query)
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)

                    # 2. 첫 페이지 데이터 수집
                    html = page.content()
                    listings = self.parse(html)
                    all_listings.extend(listings)

                    # 3. 추가 페이지 로딩 (더보기 버튼 또는 스크롤)
                    for page_num in range(2, max_pages + 1):
                        # TODO: 실제 페이지네이션 방식에 맞게 수정 필요
                        # "더보기" 버튼 클릭 시도
                        more_button = page.locator(
                            'button:has-text("더보기"), button:has-text("더 보기")'
                        )

                        if more_button.count() > 0 and more_button.is_visible():
                            more_button.click()
                            page.wait_for_timeout(2000)

                            # 새 데이터 수집
                            html = page.content()
                            new_listings = self.parse(html)

                            # 중복 제거 후 추가
                            existing_ids = {
                                item.get("complex_name", "") + item.get("area", "")
                                for item in all_listings
                            }
                            for item in new_listings:
                                item_id = item.get("complex_name", "") + item.get("area", "")
                                if item_id not in existing_ids:
                                    all_listings.append(item)
                                    existing_ids.add(item_id)

                            self.logger.info(
                                "additional_page_loaded",
                                page_num=page_num,
                                new_items=len(new_listings),
                                total_items=len(all_listings),
                            )
                        else:
                            # 더보기 버튼이 없으면 종료
                            self.logger.info(
                                "no_more_pages",
                                last_page=page_num - 1,
                                total_items=len(all_listings),
                            )
                            break

                    return all_listings
                else:
                    self.logger.warning("search_input_not_found")
                    return []

        except Exception as e:
            self.logger.error(
                "failed_to_crawl_with_pagination",
                district=district,
                dong=dong,
                error=str(e),
            )
            return all_listings

"""호갱노노 전용 크롤러 구현

BaseCrawler를 상속받아 호갱노노 API 클라이언트를 통해 부동산 데이터를 수집합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from bs4 import BeautifulSoup

from .base import BaseCrawler
from ..config import CrawlerConfig
from ..api.hogangnono_client import HogangnonoAPIClient, SearchParams
from ..utils.browser_manager import BrowserManager
from ..rate_limiter import AdaptiveRateLimiter
from ..writers.hogangnono_csv_writer import HogangnonoCSVWriter


class HogangnonoCrawler(BaseCrawler):
    """호갱노노 부동산 크롤러

    BaseCrawler를 상속받아 API 클라이언트를 통해 호갱노노 데이터를 수집합니다.
    - 지역(구/동) 기반 검색
    - API 기반 매물 목록 추출
    - 상세 정보 접근 및 파싱
    """

    def __init__(self, config: CrawlerConfig) -> None:
        """HogangnonoCrawler 초기화

        Args:
            config: 크롤러 설정
        """
        super().__init__(config)

        # API 클라이언트 초기화
        self.api_client = HogangnonoAPIClient(config)

        # Playwright를 위한 BrowserManager 초기화 (fallback용)
        self.browser_manager = BrowserManager(config)

        # Rate Limiter 초기화 (API 클라이언트에 내장된 것 사용)
        self.rate_limiter = AdaptiveRateLimiter()

        # CSV Writer 초기화
        output_dir = config.output_file or "output"
        # If output_file is a file path, extract directory
        if output_dir.endswith(".csv"):
            output_dir = str(Path(output_dir).parent)
        self.csv_writer = HogangnonoCSVWriter(output_dir=output_dir)

        # 기본 URL
        self.base_url = "https://hogangnono.com"

        # 설정에서 제한값 가져오기
        site_config = config.get_site_config()
        self.max_pages = getattr(site_config, "max_page", 5)
        self.max_apartments_per_page = getattr(site_config, "page_size", 10)

        output_dir = config.output_file or "output"
        if output_dir.endswith(".csv"):
            output_dir = str(Path(output_dir).parent)
        self.logger.info(
            "hogangnono_crawler_initialized",
            base_url=self.base_url,
            max_pages=self.max_pages,
            max_apartments_per_page=self.max_apartments_per_page,
            output_dir=output_dir,
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
        # Rate limiting 적용
        self.rate_limiter.wait()

        try:
            with self.browser_manager.managed_browser() as page:
                # 페이지 이동
                page.goto(url)

                # 네트워크 유휴 상태 대기 (JavaScript 실행 완료)
                page.wait_for_load_state("networkidle")

                # HTML 콘텐츠 가져오기
                html_content = page.content()

                # 성공 시 rate limiter 알림
                self.rate_limiter.on_success()

                self.logger.info(
                    "page_loaded_successfully",
                    url=url,
                    content_length=len(html_content),
                )

                return html_content

        except Exception as e:
            # HTTP 429 에러인 경우 rate limiter에 알림
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.rate_limiter.on_rate_limit_error()
            else:
                self.rate_limiter.on_error()

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
            # 1. 아파트 목록에서 추출 (검색 결과 페이지)
            items = soup.find_all("a", href=lambda x: x and "/apt/" in x)

            for item in items:
                try:
                    # 각 아파트 정보 추출
                    listing_data = self._extract_apartment_data(item)

                    if listing_data:
                        listings.append(listing_data)

                except Exception as e:
                    self.logger.warning(
                        "failed_to_extract_apartment",
                        error=str(e),
                    )
                    continue

            # 2. 실거래가 표에서 추출 (상세 페이지)
            if not listings:
                listings = self._extract_transaction_data(soup)

        except Exception as e:
            self.logger.error(
                "failed_to_parse_listings",
                error=str(e),
            )

        return listings

    def _extract_apartment_data(self, item: Any) -> Optional[dict[str, Any]]:
        """개별 아파트 정보 추출 (검색 결과 페이지)

        Args:
            item: BeautifulSoup a element

        Returns:
            추출된 아파트 정보 또는 None
        """
        try:
            # 링크에서 아파트 ID 추출
            href = item.get("href", "")
            apt_id = href.split("/apt/")[-1].split("/")[0] if "/apt/" in href else ""

            # 아파트 이름과 정보는 전체 텍스트에서 추출
            # Playwright는 실제 HTML을 반환하므로 li 전체 텍스트를 사용
            parent = item.find_parent("li")
            if parent:
                full_text = parent.get_text(strip=True)

                # 첫 번째 링크 텍스트가 아파트 이름
                complex_name = item.get_text(strip=True)

                # 전체 텍스트에서 동 이름 추출
                dong = ""
                if "동" in full_text:
                    # "개포동 개포자이프레지던스" 형태에서 동 추출
                    parts = full_text.split()
                    for part in parts:
                        if "동" in part and part != complex_name:
                            dong = part
                            break

                # 세대수 및 입주일 정보 추출
                household_count = ""
                move_in_date = ""
                if "세대" in full_text:
                    import re

                    household_match = re.search(r"(\d+[,\d]*\s*세대)", full_text)
                    if household_match:
                        household_count = household_match.group(1)

                if "년" in full_text and "입주" in full_text:
                    date_match = re.search(r"(\d{4}\s*년\s*\d+\s*월\s*입주)", full_text)
                    if date_match:
                        move_in_date = date_match.group(1)

                # 필수 정보가 있으면 데이터 반환
                if complex_name and apt_id:
                    return {
                        "apt_id": apt_id,
                        "complex_name": complex_name,
                        "dong": dong,
                        "household_count": household_count,
                        "move_in_date": move_in_date,
                        "price": "",
                        "area": "",
                        "floor": "",
                        "date": "",
                        "address": "",
                    }

        except Exception as e:
            self.logger.warning(
                "failed_to_extract_apartment_data",
                error=str(e),
            )

        return None

    def _extract_transaction_data(self, soup: BeautifulSoup) -> List[dict[str, Any]]:
        """실거래가 데이터 추출 (상세 페이지)

        Args:
            soup: BeautifulSoup 객체

        Returns:
            추출된 실거래가 데이터 리스트
        """
        listings: List[dict[str, Any]] = []

        try:
            # 실거래가 표 찾기
            table = soup.find("table")
            if not table:
                return listings

            # 단지 정보 추출
            complex_name = ""
            heading = soup.find("h1")
            if heading:
                complex_name = heading.get_text(strip=True)

            # 주소 정보 추출
            address = ""
            address_generic = soup.find("generic", string=lambda x: x and "특별시" in x)
            if address_generic:
                address = address_generic.get_text(strip=True)

            # 실거래가 행들 추출
            rows = table.find_all("tr")[1:]  # 헤더 제외
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    try:
                        # 계약일
                        date_cell = cells[0]
                        date = date_cell.get_text(strip=True)

                        # 면적 (타입)
                        area_cell = cells[1]
                        area_button = area_cell.find("button")
                        area = (
                            area_button.get_text(strip=True)
                            if area_button
                            else area_cell.get_text(strip=True)
                        )

                        # 가격 및 층수
                        price_cell = cells[2]
                        # 각 generic 요소에서 텍스트 추출
                        price_generics = price_cell.find_all("generic")

                        price = ""
                        floor = ""
                        if len(price_generics) >= 2:
                            # 첫 번째 generic: 가격
                            price = price_generics[0].get_text(strip=True)
                            # 두 번째 generic: 층수
                            floor = price_generics[1].get_text(strip=True)
                        else:
                            # fallback: 전체 텍스트에서 분리
                            price_text = price_cell.get_text(strip=True)
                            if "층" in price_text:
                                # "억 7,000 28층" 형태 처리
                                import re

                                match = re.search(r"([0-9,]+억(?:\s*[0-9,]+만)?)", price_text)
                                if match:
                                    price = match.group(1)
                                floor_match = re.search(r"(\d+층)", price_text)
                                if floor_match:
                                    floor = floor_match.group(1)

                        listings.append(
                            {
                                "apt_id": "",
                                "complex_name": complex_name,
                                "dong": address.split()[1] if len(address.split()) > 1 else "",
                                "household_count": "",
                                "move_in_date": "",
                                "price": price,
                                "area": area,
                                "floor": floor,
                                "date": date,
                                "address": address,
                            }
                        )

                    except Exception as e:
                        self.logger.warning(
                            "failed_to_extract_transaction_row",
                            error=str(e),
                        )
                        continue

        except Exception as e:
            self.logger.error(
                "failed_to_extract_transaction_data",
                error=str(e),
            )

        return listings

    def crawl_region(self, district: str, dong: Optional[str] = None) -> List[dict[str, Any]]:
        """지역별 크롤링 실행

        Args:
            district: 구 이름 (예: "강남구")
            dong: 동 이름 (선택적)

        Returns:
            수집된 부동산 데이터 리스트
        """
        # Rate limiting 적용
        self.rate_limiter.wait()

        try:
            search_query = f"{district} {dong or ''}".strip()
            encoded_query = search_query.replace(" ", "%20")

            with self.browser_manager.managed_browser() as page:
                # 1. 검색 결과 페이지로 직접 이동
                search_url = f"{self.base_url}/search?q={encoded_query}"
                page.goto(search_url)
                page.wait_for_load_state("networkidle")

                # 2. 로딩 대기 (설정에서 가져온 값 사용)
                page.wait_for_timeout(3000)

                # 3. 현재 페이지의 HTML 가져오기
                html = page.content()

                # 4. 데이터 파싱
                listings = self.parse(html)

                # 성공 시 rate limiter 알림
                self.rate_limiter.on_success()

                self.logger.info(
                    "region_crawl_completed",
                    district=district,
                    dong=dong,
                    search_query=search_query,
                    listings_count=len(listings),
                )

                return listings

        except Exception as e:
            # HTTP 429 에러인 경우 rate limiter에 알림
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.rate_limiter.on_rate_limit_error()
            else:
                self.rate_limiter.on_error()

            self.logger.error(
                "failed_to_crawl_region",
                district=district,
                dong=dong,
                error=str(e),
            )
            return []

    def crawl_apartment_detail(self, apt_id: str) -> List[dict[str, Any]]:
        """아파트 상세 페이지 크롤링 (실거래가 데이터)

        Args:
            apt_id: 아파트 ID

        Returns:
            수집된 실거래가 데이터 리스트
        """
        # Rate limiting 적용
        self.rate_limiter.wait()

        try:
            with self.browser_manager.managed_browser() as page:
                # 1. 아파트 상세 페이지로 이동
                detail_url = f"{self.base_url}/apt/{apt_id}/0"
                page.goto(detail_url)
                page.wait_for_load_state("networkidle")

                # 2. 로딩 대기
                page.wait_for_timeout(3000)

                # 3. "더보기" 버튼 클릭하여 더 많은 실거래가 로드
                try:
                    # 여러 "더보기" 버튼이 있을 수 있으므로 실거래가 섹션의 더보기 버튼 찾기
                    more_buttons = page.locator('button:has-text("더보기")')
                    count = more_buttons.count()

                    for i in range(count):
                        button = more_buttons.nth(i)
                        # 버튼이 보이고 활성화되어 있으면 클릭
                        if button.is_visible() and button.is_enabled():
                            button.click()
                            page.wait_for_timeout(2000)
                except Exception as e:
                    self.logger.debug(
                        "failed_to_click_more_button",
                        error=str(e),
                    )

                # 4. 페이지 HTML 가져오기
                html = page.content()

                # 5. 데이터 파싱
                listings = self.parse(html)

                # 성공 시 rate limiter 알림
                self.rate_limiter.on_success()

                self.logger.info(
                    "apartment_detail_crawl_completed",
                    apt_id=apt_id,
                    listings_count=len(listings),
                )

                return listings

        except Exception as e:
            # HTTP 429 에러인 경우 rate limiter에 알림
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.rate_limiter.on_rate_limit_error()
            else:
                self.rate_limiter.on_error()

            self.logger.error(
                "failed_to_crawl_apartment_detail",
                apt_id=apt_id,
                error=str(e),
            )
            return []

    def crawl_with_pagination(
        self,
        district: str,
        dong: Optional[str] = None,
        max_pages: Optional[int] = None,
        save_to_csv: bool = True,
    ) -> List[dict[str, Any]]:
        """페이지네이션 포함 크롤링

        Args:
            district: 구 이름
            dong: 동 이름
            max_pages: 최대 페이지 수 (설정에서 가져옴)
            save_to_csv: CSV 파일에 저장할지 여부

        Returns:
            수집된 부동산 데이터 리스트
        """
        # 설정에서 max_pages 가져오기 (인자로 전달된 경우 우선 사용)
        if max_pages is None:
            max_pages = self.max_pages

        all_listings = []
        all_transactions = []

        # Rate limiting 적용
        self.rate_limiter.wait()

        try:
            search_query = f"{district} {dong or ''}".strip()
            encoded_query = search_query.replace(" ", "%20")

            with self.browser_manager.managed_browser() as page:
                # 1. 검색 결과 페이지로 직접 이동
                search_url = f"{self.base_url}/search?q={encoded_query}"
                page.goto(search_url)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)

                # 2. 첫 페이지 데이터 수집 (아파트 목록)
                html = page.content()
                listings = self.parse(html)
                all_listings.extend(listings)

                # 3. 각 아파트의 상세 페이지에서 실거래가 데이터 수집
                # 설정에서 가져온 최대 아파트 수만큼만 상세 조회
                max_apartments = min(len(listings), self.max_apartments_per_page)

                for listing in listings[:max_apartments]:
                    apt_id = listing.get("apt_id", "")
                    if apt_id:
                        try:
                            # 상세 페이지 크롤링 (내부에서 rate limiting 적용)
                            transactions = self.crawl_apartment_detail(apt_id)

                            # 상세 정보를 기존 정보와 병합
                            for transaction in transactions:
                                transaction.update(
                                    {
                                        "dong": listing.get("dong", ""),
                                        "household_count": listing.get("household_count", ""),
                                        "move_in_date": listing.get("move_in_date", ""),
                                    }
                                )
                                all_listings.append(transaction)
                                all_transactions.append(transaction)

                        except Exception as e:
                            self.logger.warning(
                                "failed_to_crawl_apartment_transaction",
                                apt_id=apt_id,
                                error=str(e),
                            )
                            continue

                # 성공 시 rate limiter 알림
                self.rate_limiter.on_success()

                # 4. CSV에 저장
                if save_to_csv:
                    # 단지 정보 저장 (목록에서)
                    if listings:
                        # 목록을 POI 형식으로 변환
                        complexes_data = []
                        for listing in listings:
                            complex_data = {
                                "complexNo": listing.get("apt_id", ""),
                                "complexName": listing.get("complex_name", ""),
                                "useApproveDate": listing.get("move_in_date", "")
                                .replace("년", "-")
                                .replace("월", "")
                                .replace("입주", ""),
                                "totalDongCount": 0,  # 목록에서는 없음
                                "totalHouseholdCount": 0,  # 목록에서는 없음
                                "minArea": 0.0,
                                "maxArea": 0.0,
                                "dealCnt": len(all_transactions),
                                "leaseCnt": 0,
                                "rentCnt": 0,
                            }
                            complexes_data.append(complex_data)

                        self.save_complexes_to_csv(complexes_data)

                    # 거래내역 저장
                    if all_transactions:
                        self.save_transactions_to_csv(all_transactions)

                self.logger.info(
                    "pagination_crawl_completed",
                    district=district,
                    dong=dong,
                    apartments_count=len(listings),
                    transactions_count=len(all_transactions),
                    total_items=len(all_listings),
                    max_pages=max_pages,
                    max_apartments_per_page=self.max_apartments_per_page,
                    saved_to_csv=save_to_csv,
                )

                return all_listings

        except Exception as e:
            # HTTP 429 에러인 경우 rate limiter에 알림
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.rate_limiter.on_rate_limit_error()
            else:
                self.rate_limiter.on_error()

            self.logger.error(
                "failed_to_crawl_with_pagination",
                district=district,
                dong=dong,
                error=str(e),
            )
            return all_listings

    def fetch_complexes_by_region(self, bounds: dict[str, float]) -> List[dict[str, Any]]:
        """API를 통해 지역별 단지 정보 조회

        Args:
            bounds: 좌표 정보 (startX, endX, startY, endY)

        Returns:
            수집된 단지 정보 리스트
        """
        try:
            # SearchParams 생성
            search_params = SearchParams(
                startX=bounds["startX"],
                endX=bounds["endX"],
                startY=bounds["startY"],
                endY=bounds["endY"],
                level=17,
                isIgnorePin=False,
            )

            # API 호출
            response = self.api_client.get_apartments_bounding(search_params)

            if response.success and response.data:
                # POI 데이터 파싱
                pois = self.api_client.parse_pois_from_bounding(response.data)

                self.logger.info(
                    "api_complex_fetch_success",
                    pois_count=len(pois),
                    bounds=bounds,
                )

                return pois
            else:
                self.logger.error(
                    "api_complex_fetch_failed",
                    error=response.error,
                    status_code=response.status_code,
                )
                return []

        except Exception as e:
            self.logger.error(
                "failed_to_fetch_complexes_by_region",
                bounds=bounds,
                error=str(e),
            )
            return []

    def fetch_rankings(self, rank_type: str = "daily", limit: int = 100) -> List[dict[str, Any]]:
        """API를 통해 인기 순위 조회

        Args:
            rank_type: 순위 타입 (daily, weekly, monthly)
            limit: 가져올 항목 수

        Returns:
            수집된 순위 정보 리스트
        """
        try:
            # API 호출
            response = self.api_client.get_ranking(rank_type=rank_type, limit=limit)

            if response.success and response.data:
                # 순위 데이터 파싱
                complexes = self.api_client.parse_complexes_from_ranks(response.data)

                self.logger.info(
                    "api_rankings_fetch_success",
                    complexes_count=len(complexes),
                    rank_type=rank_type,
                    limit=limit,
                )

                return complexes
            else:
                self.logger.error(
                    "api_rankings_fetch_failed",
                    error=response.error,
                    status_code=response.status_code,
                )
                return []

        except Exception as e:
            self.logger.error(
                "failed_to_fetch_rankings",
                rank_type=rank_type,
                error=str(e),
            )
            return []

    def save_complexes_to_csv(self, complexes_data: List[dict[str, Any]]) -> None:
        """단지 데이터를 CSV 파일에 저장

        Args:
            complexes_data: 저장할 단지 데이터 리스트
        """
        try:
            self.csv_writer.save_complexes(complexes_data)
            self.logger.info(
                "complexes_saved_to_csv",
                count=len(complexes_data),
            )
        except Exception as e:
            self.logger.error(
                "failed_to_save_complexes",
                error=str(e),
            )

    def save_transactions_to_csv(self, transactions_data: List[dict[str, Any]]) -> None:
        """거래내역 데이터를 CSV 파일에 저장

        Args:
            transactions_data: 저장할 거래내역 데이터 리스트
        """
        try:
            self.csv_writer.save_transactions(transactions_data)
            self.logger.info(
                "transactions_saved_to_csv",
                count=len(transactions_data),
            )
        except Exception as e:
            self.logger.error(
                "failed_to_save_transactions",
                error=str(e),
            )

    def get_csv_stats(self) -> dict[str, Any]:
        """CSV 파일 통계 정보 반환

        Returns:
            CSV 파일 통계 정보
        """
        return self.csv_writer.get_stats()

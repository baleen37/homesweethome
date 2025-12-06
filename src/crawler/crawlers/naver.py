import json
import time
from pathlib import Path
from typing import Any

import structlog

from crawler.config import CrawlerConfig
from crawler.rate_limiter import AdaptiveRateLimiter
from crawler.utils.checkpoint import CheckpointManager
from crawler.utils.browser_manager import BrowserManager
from crawler.utils.retry import BROWSER_RETRY_CONFIG, Retryable
from crawler.coordinator import CrawlCoordinator


class NaverRealEstateCrawler:
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.logger = structlog.get_logger()
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()
        self.page: Any = None  # Playwright page object
        self.rate_limiter = AdaptiveRateLimiter()  # Initialize rate limiter
        self.browser_manager = BrowserManager(config)

    def get_url(self) -> str:
        return "https://new.land.naver.com/complexes"

    def _load_districts_data(self) -> dict[str, Any]:
        data_path = Path(__file__).parent.parent / "data" / "seoul_districts.json"
        with open(data_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def filter_districts(self, district_names: list[str] | None) -> list[dict[str, Any]]:
        """지정된 구만 필터링하여 반환

        Args:
            district_names: 구 이름 리스트 (None이면 전체)

        Returns:
            필터링된 구 리스트

        Raises:
            ValueError: 유효하지 않은 구 이름이 있을 경우
        """
        # 타입 어노테이션을 명시적으로 추가
        districts: list[dict[str, Any]] = self.districts_data["districts"]

        if district_names is None:
            return districts

        # 입력된 구 이름들의 유효성 검증
        valid_district_names = {d["district_name"] for d in districts}
        invalid_names = set(district_names) - valid_district_names

        if invalid_names:
            raise ValueError(f"유효하지 않은 구 이름: {', '.join(invalid_names)}")

        # 필터링
        filtered = [
            d for d in districts
            if d["district_name"] in district_names
        ]

        return filtered

    def crawl(self) -> list[dict[str, Any]]:
        """
        네이버 부동산에서 단지 목록 데이터 크롤링

        Returns:
            단지 정보 리스트
        """
        self.logger.info("starting_naver_real_estate_crawl")

        # CrawlCoordinator를 사용하여 크롤링 조정
        coordinator = CrawlCoordinator(self.config, self)
        return coordinator.crawl_all_districts()

    def _fetch_dong_data(self, dong: dict[str, Any]) -> list[dict[str, Any]]:
        """
        동 단위로 데이터를 가져오는 메서드

        Args:
            dong: 동 정보

        Returns:
            단지 정보 리스트
        """
        # BrowserManager를 사용하여 브라우저 리소스 관리
        with self.browser_manager.managed_browser() as page:
            self.page = page  # 일시적으로 저장

            # 동 페이지 접속
            self.logger.info("accessing_dong_page", dong=dong.get("dong_name", ""))
            page.goto(f"https://new.land.naver.com/houses?cortarNo={dong['cortarNo']}")
            page.wait_for_load_state("networkidle")

            # 데이터 추출 스크립트 실행
            self.logger.info("extracting_dong_data", dong=dong.get("dong_name", ""))

            # 페이지에 있는 데이터 추출
            result = page.evaluate("""
                () => {
                    const data = [];

                    // 단지 목록 추출
                    const complexes = document.querySelectorAll('a.item_link');
                    complexes.forEach(complex => {
                        try {
                            const complexName = complex.querySelector('.complex_name')?.textContent?.trim() || '';
                            const price = complex.querySelector('.price_line')?.textContent?.trim() || '';
                            const spec = complex.querySelector('.spec_line')?.textContent?.trim() || '';
                            const location = complex.querySelector('.location_line')?.textContent?.trim() || '';

                            if (complexName) {
                                data.push({
                                    complex_name: complexName,
                                    price: price,
                                    spec: spec,
                                    location: location
                                });
                            }
                        } catch (e) {
                            console.error('Error extracting complex:', e);
                        }
                    });

                    return data;
                }
            """)

            return result

    def fetch_dong_with_retry(self, dong: dict[str, Any], max_retries: int = 3) -> list[dict[str, Any]]:
        """
        재시도 로직과 함께 동 데이터 가져오기

        Args:
            dong: 동 정보
            max_retries: 최대 재시도 횟수

        Returns:
            단지 정보 리스트
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting 먼저 적용 (요청 전 대기)
                self.rate_limiter.wait()
                data = self._fetch_dong_data(dong)
                # 성공 시 rate limiter 업데이트
                self.rate_limiter.on_success()
                return data
            except TimeoutError:
                self.logger.warning(
                    "fetch_timeout",
                    dong=dong.get("dong_name", ""),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                self.rate_limiter.on_error()
                if attempt == max_retries - 1:
                    self.checkpoint_manager.add_failed_dong(dong["cortarNo"], "Timeout after retries")
                    return []
                time.sleep(2**attempt)  # 지수 백오프
            except Exception as e:
                error_msg = str(e)

                # 429 에러인지 확인
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    self.logger.warning(
                        "rate_limit_error_dong",
                        dong=dong.get("dong_name", ""),
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    self.rate_limiter.on_rate_limit_error()

                    # 재시도
                    if attempt < max_retries - 1:
                        wait_time = self.rate_limiter.get_retry_delay(attempt)
                        self.logger.info(
                            "retrying_dong_after_rate_limit",
                            dong=dong.get("dong_name", ""),
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        self.checkpoint_manager.add_failed_dong(dong["cortarNo"], error_msg)
                        return []
                else:
                    # 기타 에러
                    self.logger.error(
                        "fetch_error",
                        dong=dong.get("dong_name", ""),
                        error=error_msg,
                    )
                    self.rate_limiter.on_error()
                    self.checkpoint_manager.add_failed_dong(dong["cortarNo"], error_msg)
                    return []
        return []

    def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
        """단지 상세 정보 조회 (평형, 보유세, 공시가격, 시세 등)"""
        self.logger.info("fetching_complex_detail", complex_id=complex_id)

        base_url = "https://fin.land.naver.com/front-api/v1/complex"

        # API 엔드포인트 목록
        endpoints = [
            # 평형 정보
            f"{base_url}/building/pyeongList?complexNumber={complex_id}",
            # 보유세 정보 (pyeongTypeNumber=1 필요)
            f"{base_url}/holdingTax?complexNumber={complex_id}&pyeongTypeNumber=1",
            # 공시가격 정보 (pyeongTypeNumber=1 필요)
            f"{base_url}/declaredValue/pyeongType?complexNumber={complex_id}&pyeongTypeNumber=1",
            # 매물 가격 분포 (추가 파라미터 필요)
            f"{base_url}/askingPrice?complexNumber={complex_id}&pyeongTypeNumber=1&realEstateType=A01",
            # 최근 시세 (추가 파라미터 필요)
            f"{base_url}/marketPrice/recent?complexNumber={complex_id}&pyeongTypeNumber=1&realEstateType=A01",
        ]

        detail_data: dict[str, Any] = {
            "complex_id": complex_id,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            # BrowserManager를 사용하여 브라우저 리소스 관리
            with self.browser_manager.managed_browser() as page:
                self.page = page  # 일시적으로 저장

                # 단지 상세 페이지에 먼저 접속하여 세션 확보
                self.logger.info("accessing_complex_page", complex_id=complex_id)
                page.goto("https://fin.land.naver.com/complexes")
                page.wait_for_load_state("networkidle")
                # 추가 대기 시간
                time.sleep(3)

                page.goto(f"https://fin.land.naver.com/complexes/{complex_id}")
                page.wait_for_load_state("networkidle")
                time.sleep(5)  # 페이지 로딩 및 세션 안정화를 위한 충분한 대기

                # 각 API 엔드포인트 호출
                for idx, endpoint_url in enumerate(endpoints):
                    endpoint_name = endpoint_url.split("/")[-1].split("?")[0]
                    self.logger.info("fetching_endpoint", endpoint=endpoint_name, index=idx + 1, total=len(endpoints))

                    # 엔드포인트 호출을 재시도 로직으로 감싸기
                    response = self._fetch_endpoint_with_retry(page, endpoint_url, endpoint_name)

                    if response is not None:
                        detail_data[endpoint_name] = response
                    else:
                        detail_data[endpoint_name] = {"error": "Failed after retries"}

                    # Rate limiting - API 호출 간 충분한 대기 (429 에러 방지)
                    if idx < len(endpoints) - 1:
                        time.sleep(6)  # 6초 대기로 증가

            # 데이터 파싱
            parsed_detail = self._parse_complex_detail(detail_data)
            self.logger.info("complex_detail_fetched", complex_id=complex_id)

            return parsed_detail

        except Exception as e:
            self.logger.error(
                "complex_detail_fetch_failed",
                complex_id=complex_id,
                error=str(e),
            )
            return {
                "complex_id": complex_id,
                "error": str(e),
                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

    def _fetch_endpoint_with_retry(
        self,
        page: Any,
        endpoint_url: str,
        endpoint_name: str,
        max_retries: int = 3
    ) -> dict[str, Any] | None:
        """
        API 엔드포인트를 재시도 로직과 함께 호출

        Retryable 클래스를 사용하여 재시도 로직을 처리합니다.

        Args:
            page: Playwright page object
            endpoint_url: API 엔드포인트 URL
            endpoint_name: 엔드포인트 이름 (로깅용)
            max_retries: 최대 재시도 횟수

        Returns:
            API 응답 JSON 또는 None (모든 재시도 실패 시)
        """
        def fetch_endpoint():
            result = page.evaluate(
                """
                async (url) => {
                    try {
                        const response = await fetch(url, {
                            method: 'GET',
                            headers: {
                                'Accept': 'application/json, text/plain, */*',
                                'Accept-Language': 'ko-KR,ko;q=0.9',
                            }
                        });

                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`HTTP ${response.status}: ${errorText}`);
                        }

                        return await response.json();
                    } catch (error) {
                        console.error('API call failed:', error);
                        throw error;
                    }
                }
                """,
                endpoint_url,
            )

            self.logger.info(
                "endpoint_fetched_successfully",
                endpoint=endpoint_name,
            )
            return result

        try:
            # Use Retryable with browser-specific configuration
            # Override max_attempts if provided
            retry_config = BROWSER_RETRY_CONFIG
            if max_retries != 3:  # Default is 5 in BROWSER_RETRY_CONFIG
                retry_config = type(BROWSER_RETRY_CONFIG)(
                    max_attempts=max_retries,
                    base_delay=retry_config.base_delay,
                    max_delay=retry_config.max_delay,
                    strategy=retry_config.strategy,
                    jitter=retry_config.jitter,
                    exponential_base=retry_config.exponential_base,
                    retry_on=retry_config.retry_on,
                )

            return retry_config.execute(fetch_endpoint)

        except Exception as e:
            self.logger.error(
                "endpoint_fetch_failed_final",
                endpoint=endpoint_name,
                error=str(e),
            )
            return None

    def _parse_complex_detail(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """단지 상세 데이터 파싱"""
        parsed = {
            "complex_id": raw_data.get("complex_id"),
            "fetched_at": raw_data.get("fetched_at"),
        }

        # 평형 정보 파싱
        if "pyeongList" in raw_data:
            pyeong_data = raw_data["pyeongList"]
            if isinstance(pyeong_data, dict) and "result" in pyeong_data:
                parsed["pyeong_info"] = pyeong_data["result"]

        # 보유세 정보 파싱
        if "holdingTax" in raw_data:
            tax_data = raw_data["holdingTax"]
            if isinstance(tax_data, dict) and "result" in tax_data:
                parsed["holding_tax"] = tax_data["result"]

        # 공시가격 정보 파싱
        if "declaredValue" in raw_data:
            price_data = raw_data["declaredValue"]
            if isinstance(price_data, dict) and "result" in price_data:
                parsed["declared_price"] = price_data["result"]

        # 매물 가격 분포 파싱
        if "askingPrice" in raw_data:
            asking_data = raw_data["askingPrice"]
            if isinstance(asking_data, dict) and "result" in asking_data:
                parsed["asking_price"] = asking_data["result"]

        # 최근 시세 파싱
        if "recent" in raw_data:
            market_data = raw_data["recent"]
            if isinstance(market_data, dict) and "result" in market_data:
                parsed["market_price"] = market_data["result"]

        return parsed

    def fetch_complex_listings(self, complex_id: str, trade_type: str = "A1") -> list[dict[str, Any]]:
        """
        특정 단지의 매물 목록을 가져옵니다.

        Args:
            complex_id: 단지 ID (예: 111861)
            trade_type: 거래 유형 (A1: 매매, B1: 전세, B2: 월세)

        Returns:
            매물 정보 리스트
        """
        self.logger.info(
            "fetching_complex_listings",
            complex_id=complex_id,
            trade_type=trade_type,
        )

        all_listings = []

        # BrowserManager를 사용하여 브라우저 리소스 관리
        with self.browser_manager.managed_browser() as page:
            self.page = page  # 일시적으로 저장

            # 먼저 단지 페이지에 접속하여 세션 확보
            page.goto("https://m.land.naver.com/complexes")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            page.goto(f"https://m.land.naver.com/complex/{complex_id}")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            page = 1
            max_pages = 10  # 최대 페이지 수 제한

            while page <= max_pages:
                self.logger.info(
                    "fetching_listing_page",
                    complex_id=complex_id,
                    trade_type=trade_type,
                    page=page,
                )

                # 모바일 API URL
                api_url = (
                    f"https://m.land.naver.com/cluster/ajax/articleList?"
                    f"complexNo={complex_id}&"
                    f"tradTpCd={trade_type}&"
                    f"page={page}&"
                    f"showR0=N"
                )

                try:
                    # 브라우저 컨텍스트에서 API 호출
                    result = page.evaluate(
                        """
                        async (url) => {
                            try {
                                const response = await fetch(url, {
                                    method: 'GET',
                                    headers: {
                                        'Accept': 'application/json, text/plain, */*',
                                        'Accept-Language': 'ko-KR,ko;q=0.9',
                                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
                                    }
                                });

                                if (!response.ok) {
                                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                                }

                                return await response.json();
                            } catch (error) {
                                console.error('API call failed:', error);
                                throw error;
                            }
                        }
                        """,
                        api_url,
                    )

                    # 응답 파싱
                    listings = self._parse_complex_listings(result)

                    # 더 이상 매물이 없으면 중단
                    if not listings:
                        self.logger.info(
                            "no_more_listings",
                            complex_id=complex_id,
                            trade_type=trade_type,
                            last_page=page - 1,
                        )
                        break

                    all_listings.extend(listings)

                    # API 응답에 결과 수가 설정된 경우 확인
                    if "result" in result and len(result["result"]) < 20:
                        # 한 페이지에 20개 미만이면 마지막 페이지로 간주
                        break

                    page += 1

                    # Rate limiting - 페이지별 4초 대기 (429 에러 방지)
                    time.sleep(4)

                except Exception as e:
                    self.logger.error(
                        "fetch_listings_error",
                        complex_id=complex_id,
                        trade_type=trade_type,
                        page=page,
                        error=str(e),
                    )
                    # 오류 발생 시 중단
                    break

            self.logger.info(
                "complex_listings_fetched",
                complex_id=complex_id,
                trade_type=trade_type,
                total_listings=len(all_listings),
                pages_fetched=page - 1,
            )

            return all_listings

    def _parse_complex_listings(self, api_response: dict[str, Any]) -> list[dict[str, Any]]:
        """API 응답에서 매물 정보 파싱"""
        listings = []

        if "result" not in api_response:
            return listings

        for item in api_response["result"]:
            try:
                listing = {
                    "article_no": item.get("articleNo"),
                    "trade_type_name": item.get("tradeTypeName"),
                    "floor": item.get("floor"),
                    "area": item.get("area2"),
                    "area_pyeong": item.get("area1"),
                    "price": item.get("price"),
                    "rent_price": item.get("rentPrice"),
                    "direction": item.get("direction"),
                    "description": item.get("description"),
                    "tag_list": item.get("tagList"),
                    "representative_image": item.get("representativeImgurl"),
                    "room_count": item.get("roomCount"),
                    "bathroom_count": item.get("bathroomCount"),
                    "is_jeonse_key": item.get("isJeonseKey", False),
                    "is_immediately_available": item.get("isImmediate", False),
                    "is_heating_type": item.get("heatingType"),
                    "building_name": item.get("buildingName"),
                    "reg_date": item.get("regDate"),
                    "contact_agent_name": item.get("agentName"),
                    "contact_tel1": item.get("tel1"),
                    "contact_tel2": item.get("tel2"),
                }
                listings.append(listing)
            except Exception as e:
                self.logger.warning(
                    "failed_to_parse_listing",
                    error=str(e),
                    item=item,
                )

        return listings

    def fetch_transaction_history(
        self,
        complex_id: str,
        pyeong_type_number: int,
        trade_type: str,  # "A1", "B1", "B2"
        complex_name: str = "",
        pyeong_name: str = "",
    ) -> list[dict[str, Any]]:
        """
        특정 단지의 특정 평형에 대한 전체 거래내역 조회

        페이지네이션 방식 사용:
        - page=1부터 시작
        - hasNextPage=false가 될 때까지 반복
        - Rate limiter 적용하여 API 호출
        - 데이터 유효성 검증 및 파싱 포함

        Args:
            complex_id: 단지 ID
            pyeong_type_number: 평형 타입 번호
            trade_type: 거래 유형 ("A1", "B1", "B2")
            complex_name: 단지명 (선택적)
            pyeong_name: 평형명 (선택적)

        Returns:
            전체 거래내역 리스트
        """
        self.logger.info(
            "fetching_transaction_history",
            complex_id=complex_id,
            pyeong_type_number=pyeong_type_number,
            trade_type=trade_type,
        )

        all_transactions = []
        page = 1

        # BrowserManager를 사용하여 브라우저 리소스 관리
        with self.browser_manager.managed_browser() as page_obj:
            self.page = page_obj  # 일시적으로 저장

            # 먼저 단지 상세 페이지에 접속하여 세션 확보
            self.logger.info("accessing_complex_detail_page", complex_id=complex_id)
            page_obj.goto(f"https://fin.land.naver.com/complexes/{complex_id}")
            page_obj.wait_for_load_state("networkidle")
            time.sleep(3)  # 페이지 로딩 및 세션 안정화

            while True:
                self.logger.info(
                    "fetching_transaction_page",
                    complex_id=complex_id,
                    trade_type=trade_type,
                    page=page,
                )

                # Rate limiting 적용
                self.rate_limiter.wait()

                # GraphQL API URL (모든 거래내용 조회)
                api_url = (
                    f"https://fin.land.naver.com/graphql"
                    f"?complexNo={complex_id}"
                    f"&pyeongTypeNumber={pyeong_type_number}"
                    f"&tradeTypeCode={trade_type}"
                    f"&page={page}"
                )

                try:
                    # GraphQL 쿼리 실행
                    result = page_obj.evaluate(
                        """
                        async (url) => {
                            const variables = {
                                first: 20,
                                after: "",
                                tradeTypeCode: "",
                                complexNo: "",
                                pyeongTypeNumber: 0,
                                isMine: false,
                                realEstateTypeCode: "",
                                orderTypeCode: "RECENT"
                            };

                            // URL에서 파라미터 추출
                            const urlParams = new URLSearchParams(url.split('?')[1]);
                            if (urlParams.has('complexNo')) {
                                variables.complexNo = urlParams.get('complexNo');
                            }
                            if (urlParams.has('pyeongTypeNumber')) {
                                variables.pyeongTypeNumber = parseInt(urlParams.get('pyeongTypeNumber'));
                            }
                            if (urlParams.has('tradeTypeCode')) {
                                variables.tradeTypeCode = urlParams.get('tradeTypeCode');
                            }

                            // 페이지네이션을 위한 cursor 설정
                            if (page > 1) {
                                // 이전 페이지의 마지막 항목으로 cursor 설정 (실제로는 API에서 제공하는 cursor 사용)
                                variables.after = btoa(`arrayconnection:${(page - 1) * 19}`);
                            }

                            const query = `
                                query DealHistories(
                                    $first: Int!,
                                    $after: String,
                                    $tradeTypeCode: String!,
                                    $complexNo: String!,
                                    $pyeongTypeNumber: Int!,
                                    $isMine: Boolean!,
                                    $realEstateTypeCode: String,
                                    $orderTypeCode: String!
                                ) {
                                    dealHistories(
                                        first: $first,
                                        after: $after,
                                        tradeTypeCode: $tradeTypeCode,
                                        complexNo: $complexNo,
                                        pyeongTypeNumber: $pyeongTypeNumber,
                                        isMine: $isMine,
                                        realEstateTypeCode: $realEstateTypeCode,
                                        orderTypeCode: $orderTypeCode
                                    ) {
                                        totalCount
                                        edges {
                                            node {
                                                tradeType
                                                exclusivePyeong
                                                dealYear
                                                dealMonth
                                                dealDay
                                                dealAmount
                                                floor
                                                buildingName
                                                cancelDealType
                                                agentName
                                                __typename
                                            }
                                            cursor
                                            __typename
                                        }
                                        pageInfo {
                                            hasNextPage
                                            endCursor
                                            __typename
                                        }
                                        __typename
                                    }
                                }
                            `;

                            const response = await fetch('https://fin.land.naver.com/graphql', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json',
                                },
                                body: JSON.stringify({
                                    query: query,
                                    variables: variables
                                })
                            });

                            if (!response.ok) {
                                const errorText = await response.text();
                                throw new Error(`HTTP ${response.status}: ${errorText}`);
                            }

                            return await response.json();
                        }
                        """,
                        api_url,
                    )

                    # 응답 확인
                    if "data" not in result or "dealHistories" not in result["data"]:
                        self.logger.error(
                            "invalid_transaction_response",
                            result=result,
                        )
                        break

                    deal_histories = result["data"]["dealHistories"]
                    edges = deal_histories.get("edges", [])

                    if not edges:
                        self.logger.info(
                            "no_more_transactions",
                            complex_id=complex_id,
                            last_page=page - 1,
                        )
                        break

                    # 데이터 파싱
                    page_transactions = []
                    for edge in edges:
                        node = edge.get("node", {})
                        if not node:
                            continue

                        try:
                            transaction = {
                                "complex_id": complex_id,
                                "complex_name": complex_name,
                                "pyeong_type_number": pyeong_type_number,
                                "pyeong_name": pyeong_name,
                                "trade_type": node.get("tradeType"),
                                "exclusive_pyeong": node.get("exclusivePyeong"),
                                "deal_year": node.get("dealYear"),
                                "deal_month": node.get("dealMonth"),
                                "deal_day": node.get("dealDay"),
                                "deal_amount": node.get("dealAmount"),
                                "floor": node.get("floor"),
                                "building_name": node.get("buildingName"),
                                "cancel_deal_type": node.get("cancelDealType"),
                                "agent_name": node.get("agentName"),
                                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            page_transactions.append(transaction)
                        except Exception as e:
                            self.logger.warning(
                                "failed_to_parse_transaction",
                                error=str(e),
                                node=node,
                            )

                    all_transactions.extend(page_transactions)

                    self.logger.info(
                        "transaction_page_fetched",
                        complex_id=complex_id,
                        page=page,
                        count=len(page_transactions),
                        total_count=deal_histories.get("totalCount", 0),
                    )

                    # 다음 페이지 확인
                    page_info = deal_histories.get("pageInfo", {})
                    if not page_info.get("hasNextPage", False):
                        self.logger.info(
                            "reached_last_transaction_page",
                            complex_id=complex_id,
                            total_pages=page,
                        )
                        break

                    page += 1

                    # Rate limiting - 페이지별 2초 대기
                    time.sleep(2)

                except Exception as e:
                    error_msg = str(e)

                    # 429 에러인지 확인
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        self.logger.warning(
                            "rate_limit_error_transaction",
                            complex_id=complex_id,
                            page=page,
                            error=error_msg,
                        )
                        self.rate_limiter.on_rate_limit_error()

                        # 재시도
                        wait_time = self.rate_limiter.get_retry_delay(page)
                        self.logger.info(
                            "retrying_transaction_after_rate_limit",
                            complex_id=complex_id,
                            page=page,
                            wait_time=wait_time,
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # 기타 에러
                        self.logger.error(
                            "transaction_fetch_error",
                            complex_id=complex_id,
                            page=page,
                            error=error_msg,
                        )
                        self.rate_limiter.on_error()
                        break

        self.logger.info(
            "transaction_history_fetched",
            complex_id=complex_id,
            pyeong_type_number=pyeong_type_number,
            trade_type=trade_type,
            total_transactions=len(all_transactions),
            pages_fetched=page - 1,
        )

        return all_transactions

    def save_checkpoint(self) -> None:
        """현재 상태를 체크포인트로 저장"""
        self.checkpoint_manager.save_checkpoint()

    def load_checkpoint(self) -> dict[str, Any]:
        """체크포인트를 로드"""
        return self.checkpoint_manager.load_checkpoint()
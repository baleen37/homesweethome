import json
import time
from pathlib import Path
from typing import Any

import structlog

from crawler.config import CrawlerConfig
from crawler.rate_limiter import AdaptiveRateLimiter
from crawler.utils.checkpoint import CheckpointManager
from crawler.utils.browser_manager import BrowserManager
from crawler.utils.retry import BROWSER_RETRY_CONFIG
from crawler.utils.logging_config import CrawlLogger
from crawler.coordinator import CrawlCoordinator


class NaverRealEstateCrawler:
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.crawl_logger = CrawlLogger("naver_real_estate")
        self.logger = structlog.get_logger()  # 기존 호환성 유지
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()
        self.page: Any = None  # Playwright page object
        self.rate_limiter = AdaptiveRateLimiter()  # Initialize rate limiter
        self.browser_manager = BrowserManager(config)

        # 리소스 사용량 추적
        self.start_time = time.time()

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
        filtered = [d for d in districts if d["district_name"] in district_names]

        return filtered

    def crawl(self, district_filter: list[str] | None = None) -> list[dict[str, Any]]:
        """
        네이버 부동산에서 단지 목록 데이터 크롤링

        Args:
            district_filter: 크롤링할 구 필터 (None이면 전체)

        Returns:
            단지 정보 리스트
        """
        # 구 필터링
        filtered_districts = self.filter_districts(district_filter)

        self.crawl_logger.log_crawl_start(
            total_items=len(filtered_districts),
            districts_count=len(filtered_districts),
        )

        # 리소스 사용량 초기 로깅
        self.crawl_logger.log_resource_usage(
            requests_made=0,
            avg_response_time=0,
        )

        try:
            # CrawlCoordinator를 사용하여 크롤링 조정
            coordinator = CrawlCoordinator(
                output_dir=Path("output"), checkpoint_path=Path("output/checkpoint.json")
            )

            # 필터링된 구 데이터를 dong_complexes 형식으로 변환
            dong_complexes = []
            for district in filtered_districts:
                # 각 구의 동(dongs)을 개별적으로 처리
                for dong in district.get("dongs", []):
                    # 각 동에 대해 단지 데이터 수집
                    self.logger.info(
                        "fetching_dong_complexes",
                        dong_name=dong.get("dong_name", ""),
                        cortar_no=dong.get("cortarNo", ""),
                    )

                    # 재시도 로직과 함께 동 데이터 가져오기
                    complexes = self.fetch_dong_with_retry(dong)

                    dong_complexes.append(
                        {
                            "dong_code": dong.get("cortarNo", ""),
                            "dong_name": dong.get("dong_name", ""),
                            "complexes": complexes,  # 수집된 단지 정보
                        }
                    )

            # crawl_multiple_dongs 메서드 호출
            # 래퍼 함수를 사용하여 인스턴스 메서드를 함수로 전달
            coordinator.crawl_multiple_dongs(
                dong_complexes=dong_complexes,
                fetch_complex_detail=self.fetch_complex_detail,
                fetch_transaction_history=lambda complex_id,
                pyeong_type,
                trade_type: self.fetch_transaction_history(complex_id, pyeong_type, trade_type),
                resume=self.checkpoint_manager.exists(),
            )

            # 모든 단지 정보 수집하여 반환
            all_complexes = []
            for dong_data in dong_complexes:
                all_complexes.extend(dong_data["complexes"])

            # 크롤링 완료 로깅
            self.crawl_logger.log_crawl_end(
                items_processed=len(all_complexes),
                success=True,
                summary={
                    "total_complexes": len(all_complexes),
                },
            )

            # 최종 리소스 사용량 로깅
            self.crawl_logger.log_resource_usage(
                requests_made=self.crawl_logger.request_count,
                avg_response_time=0,  # TODO: 평균 응답시간 계산 추가
            )

            # 단지 정보 리스트 반환
            return all_complexes

        except Exception as e:
            # 에러 발생 시 상세 로깅
            self.crawl_logger.error_with_context(
                error=e,
                context={
                    "total_districts": len(self.districts_data.get("districts", [])),
                    "requests_made": self.crawl_logger.request_count,
                },
                critical=False,
            )

            # 크롤링 실패 로깅
            self.crawl_logger.log_crawl_end(
                items_processed=0,
                success=False,
                summary={"error": str(e)},
            )

            raise

    def _fetch_dong_data(self, dong: dict[str, Any]) -> list[dict[str, Any]]:
        """법정동별 단지 데이터 수집 (모바일 API 사용)"""
        start_time = time.time()
        dong_name = dong.get("dong_name", "")
        cortar_no = dong.get("cortarNo", "")

        # BrowserManager를 사용하여 브라우저 리소스 관리
        with self.browser_manager.managed_browser() as page:
            self.page = page  # 일시적으로 저장

            # 모바일 페이지 접속하여 세션 확보
            page.goto("https://m.land.naver.com/complexes")
            page.wait_for_load_state("networkidle")
            time.sleep(3)  # 세션 안정화

            # bounds 정보 가져오기
            bounds = dong.get(
                "bounds",
                {
                    "leftLon": 127.047294,
                    "rightLon": 127.063564,
                    "topLat": 37.527949,
                    "bottomLat": 37.513261,
                },
            )

            # 중심 좌표 계산
            center_lon = (bounds["leftLon"] + bounds["rightLon"]) / 2
            center_lat = (bounds["topLat"] + bounds["bottomLat"]) / 2

            # 모바일 API URL 생성
            api_url = (
                f"https://m.land.naver.com/cluster/ajax/complexList?"
                f"cortarNo={cortar_no}&"
                f"rletTpCd=APT&"
                f"tradTpCd=A1&"
                f"z=17&"
                f"lat={center_lat}&"
                f"lon={center_lon}&"
                f"btm={bounds['bottomLat']}&"
                f"lft={bounds['leftLon']}&"
                f"top={bounds['topLat']}&"
                f"rgt={bounds['rightLon']}"
            )

            # 브라우저 컨텍스트에서 API 호출
            result = page.evaluate(
                """
                async (url) => {
                    try {
                        const response = await fetch(url, {
                            method: 'GET',
                            credentials: 'same-origin',
                            headers: {
                                'Accept': 'application/json, text/plain, */*',
                                'Accept-Language': 'ko-KR,ko;q=0.9',
                                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
                            }
                        });

                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`HTTP ${response.status}: ${errorText}`);
                        }

                        return await response.json();
                    } catch (error) {
                        console.error('API call failed:', error);
                        return { error: error.message };
                    }
                }
            """,
                api_url,
            )

            # 응답 시간 로깅
            response_time = time.time() - start_time
            status_code = 200 if result and not result.get("error") else 500

            # API 호출 결과 상세 로깅
            self.crawl_logger.log_api_call(
                endpoint="/cluster/ajax/complexList",
                params={"cortarNo": cortar_no, "dong_name": dong_name},
                response_time=response_time,
                response_size=len(str(result)) if result else 0,
                status_code=status_code,
            )

            # 응답 시간에 대한 추가 로깅
            if response_time > 3.0:
                self.logger.warning(
                    "slow_api_response",
                    dong_name=dong_name,
                    response_time=response_time,
                    status_code=status_code,
                )
            else:
                self.logger.info(
                    "api_call_completed",
                    dong_name=dong_name,
                    response_time=response_time,
                    status_code=status_code,
                    complex_count=len(result.get("result", []))
                    if result and not result.get("error")
                    else 0,
                )

            # 데이터 파싱
            if result and result.get("error"):
                # 429 에러 핸들링
                if "429" in str(result["error"]) or "Too Many Requests" in str(result["error"]):
                    self.logger.warning(
                        "rate_limit_hit", dong_name=dong_name, wait_time=10, error=result["error"]
                    )
                    time.sleep(10)  # Rate limit 걸리면 10초 대기
                else:
                    self.logger.error("api_call_failed", dong_name=dong_name, error=result["error"])
                return []

            # API 호출 성공 후 Rate Limiting
            if not result.get("error"):
                # 다음 API 호출까지 최소 5초 대기
                time.sleep(5)

            return self._parse_complex_list_api(result)

    def _parse_complex_list_api(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """모바일 API 응답 파싱"""
        # 모바일 API는 "result" 키에 데이터가 들어있음
        items = response.get("result", [])

        if not items:
            return []

        # HTML 태그 제거 함수 (루프 외부로 이동)
        def clean_price(price_str: str) -> str:
            if not price_str:
                return ""
            return price_str.replace("<em class='txt_unit'>", "").replace("</em>", "").strip()

        results = []
        for item in items:
            results.append(
                {
                    "complex_id": item.get("hscpNo", ""),
                    "complex_name": item.get("hscpNm", ""),
                    "real_estate_type": item.get("hscpTypeNm", ""),
                    "completion_year_month": item.get("useAprvYmd", ""),
                    "total_dong_count": item.get("totDongCnt", 0),
                    "total_household_count": item.get("totHsehCnt", 0),
                    "min_area": item.get("minSpc", ""),
                    "max_area": item.get("maxSpc", ""),
                    "deal_count": item.get("dealCnt", 0),
                    "lease_count": item.get("leaseCnt", 0),
                    "rent_count": item.get("rentCnt", 0),
                    "deal_price_min": clean_price(item.get("dealPrcMin", "")),
                    "deal_price_max": clean_price(item.get("dealPrcMax", "")),
                    "lease_price_min": clean_price(item.get("leasePrcMin", "")),
                    "lease_price_max": clean_price(item.get("leasePrcMax", "")),
                }
            )

        return results

    def fetch_dong_with_retry(
        self, dong: dict[str, Any], max_retries: int = 3
    ) -> list[dict[str, Any]]:
        """
        재시도 로직과 함께 동 데이터 가져오기

        Args:
            dong: 동 정보
            max_retries: 최대 재시도 횟수

        Returns:
            단지 정보 리스트
        """
        dong_name = dong.get("dong_name", "")

        for attempt in range(max_retries):
            try:
                # Rate limiting 먼저 적용 (요청 전 대기)
                self.rate_limiter.wait()
                data = self._fetch_dong_data(dong)
                # 성공 시 rate limiter 업데이트
                self.rate_limiter.on_success()
                return data
            except TimeoutError as e:
                # 타임아웃 에러 로깅
                delay = 2**attempt  # 지수 백오프
                self.crawl_logger.log_retry(
                    attempt=attempt + 1,
                    max_attempts=max_retries,
                    error=f"Timeout: {str(e)}",
                    delay=delay,
                    context={
                        "dong_name": dong_name,
                        "cortarNo": dong.get("cortarNo"),
                        "error_type": "timeout",
                    },
                )
                self.rate_limiter.on_error()
                if attempt == max_retries - 1:
                    self.checkpoint_manager.add_failed_dong(
                        dong["cortarNo"], "Timeout after retries"
                    )
                    return []
                time.sleep(delay)
            except Exception as e:
                error_msg = str(e)

                # 429 에러인지 확인
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    wait_time = self.rate_limiter.get_retry_delay(attempt)
                    self.crawl_logger.log_retry(
                        attempt=attempt + 1,
                        max_attempts=max_retries,
                        error=f"Rate limit: {error_msg}",
                        delay=wait_time,
                        context={
                            "dong_name": dong_name,
                            "cortarNo": dong.get("cortarNo"),
                            "error_type": "rate_limit",
                        },
                    )
                    self.rate_limiter.on_rate_limit_error()

                    # 재시도
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    else:
                        self.checkpoint_manager.add_failed_dong(dong["cortarNo"], error_msg)
                        return []
                else:
                    # 기타 에러
                    self.crawl_logger.error_with_context(
                        error=e,
                        context={
                            "dong_name": dong_name,
                            "cortarNo": dong.get("cortarNo"),
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "error_type": "general_error",
                        },
                    )
                    self.rate_limiter.on_error()
                    self.checkpoint_manager.add_failed_dong(dong["cortarNo"], error_msg)
                    return []
        return []

    def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
        """단지 상세 정보 조회 (평형, 보유세, 공시가격, 시세 등)"""
        self.crawl_logger.log_api_call(
            endpoint="/complex/detail",
            params={"complex_id": complex_id},
        )

        base_url = "https://fin.land.naver.com/front-api/v1/complex"

        # API 엔드포인트 목록
        endpoints = [
            # 평형 정보
            f"{base_url}/building/pyeongList?complexNumber={complex_id}",
            # 보유세 정보 (pyeongTypeNumber=1 필요)
            f"{base_url}/holdingTax?complexNumber={complex_id}&pyeongTypeNumber=1",
            # 공시가격 정보 (pyeongTypeNumber=1 필요)
            f"{base_url}/declaredValue/pyeongType?complexNumber={complex_id}&pyeongTypeNumber=1",
            # 최근 시세 (추가 파라미터 필요)
            f"{base_url}/marketPrice/recent?complexNumber={complex_id}&pyeongTypeNumber=1&realEstateType=A01",
            # 주의: askingPrice 엔드포인트는 현재 네이버에서 제공하지 않음 (404 에러)
            # f"{base_url}/marketPrice/askingPrice?complexNumber={complex_id}&pyeongTypeNumber=1",
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
                    self.crawl_logger.log_progress(
                        current=idx + 1,
                        total=len(endpoints),
                        item_type="endpoints",
                    )

                    # 엔드포인트 호출을 재시도 로직으로 감싸기
                    start_time = time.time()
                    response = self._fetch_endpoint_with_retry(page, endpoint_url, endpoint_name)
                    response_time = time.time() - start_time

                    if response is not None:
                        detail_data[endpoint_name] = response
                        self.crawl_logger.log_api_call(
                            endpoint=f"/complex/{endpoint_name}",
                            params={"complex_id": complex_id},
                            response_time=response_time,
                            response_size=len(str(response)),
                            status_code=200,
                        )
                    else:
                        detail_data[endpoint_name] = {"error": "Failed after retries"}
                        self.crawl_logger.log_api_call(
                            endpoint=f"/complex/{endpoint_name}",
                            params={"complex_id": complex_id},
                            response_time=response_time,
                            status_code=500,
                        )

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
        self, page: Any, endpoint_url: str, endpoint_name: str, max_retries: int = 3
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
            start_time = time.time()
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

                        const responseText = await response.text();

                        // 응답이 JSON인지 확인
                        if (responseText.trim().startsWith('<')) {
                            throw new Error('Received HTML instead of JSON - likely blocked or redirected');
                        }

                        try {
                            return JSON.parse(responseText);
                        } catch (parseError) {
                            throw new Error(`Invalid JSON response: ${parseError.message}. Response starts with: ${responseText.substring(0, 100)}`);
                        }
                    } catch (error) {
                        console.error('API call failed:', error);
                        throw error;
                    }
                }
                """,
                endpoint_url,
            )

            response_time = time.time() - start_time
            self.crawl_logger.log_api_call(
                endpoint=f"/api/{endpoint_name}",
                response_time=response_time,
                response_size=len(str(result)) if result else 0,
                status_code=200,
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
            # 최종 실패 시 상세 로깅
            self.crawl_logger.error_with_context(
                error=e,
                context={
                    "endpoint": endpoint_name,
                    "endpoint_url": endpoint_url[:100] + "..."
                    if len(endpoint_url) > 100
                    else endpoint_url,
                    "max_retries": max_retries,
                    "error_type": "api_fetch_failed",
                },
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
                result_data = pyeong_data["result"]
                parsed["pyeong_info"] = result_data

                # pyeong_types 필드 추가 (coordinator에서 사용)
                # result_data가 유효한 리스트 또는 딕셔너리인지 확인
                if isinstance(result_data, (list, dict)):
                    parsed["pyeong_types"] = result_data
                else:
                    self.logger.warning(
                        "invalid_pyeong_types_data",
                        complex_id=raw_data.get("complex_id"),
                        data_type=type(result_data),
                        data=str(result_data)[:200] if result_data else None,
                    )
                    parsed["pyeong_types"] = []  # 빈 리스트로 초기화하여 오류 방지
            else:
                self.logger.warning(
                    "invalid_pyeong_data_structure",
                    complex_id=raw_data.get("complex_id"),
                    pyeong_data_type=type(pyeong_data),
                )
                parsed["pyeong_types"] = []  # 빈 리스트로 초기화

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

    def fetch_complex_listings(
        self, complex_id: str, trade_type: str = "A1"
    ) -> list[dict[str, Any]]:
        """
        특정 단지의 매물 목록을 가져옵니다 (모바일 API 사용).

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
            # 모바일 페이지 접속하여 세션 확보
            page.goto("https://m.land.naver.com/complexes")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            current_page = 1
            max_pages = 10

            while current_page <= max_pages:
                # 모바일 API URL
                api_url = (
                    f"https://m.land.naver.com/cluster/ajax/articleList?"
                    f"complexNo={complex_id}&"
                    f"tradTpCd={trade_type}&"
                    f"page={current_page}&"
                    f"showR0=N"
                )

                # 브라우저 컨텍스트에서 API 호출
                result = page.evaluate(
                    """
                    async (url) => {
                        try {
                            const response = await fetch(url, {
                                method: 'GET',
                                credentials: 'same-origin',
                                headers: {
                                    'Accept': 'application/json, text/plain, */*',
                                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
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

                # 응답 로깅
                self.logger.info(
                    "api_response_received",
                    complex_id=complex_id,
                    current_page=current_page,
                    response_keys=result.keys() if isinstance(result, dict) else type(result),
                    has_result=result.get("result") if isinstance(result, dict) else False,
                )

                # 데이터 파싱
                listings = self._parse_complex_listings(result)

                if not listings:
                    self.logger.info(
                        "no_listings_found",
                        complex_id=complex_id,
                        current_page=current_page,
                        response_result=result.get("result", [])
                        if isinstance(result, dict)
                        else result,
                    )
                    break

                all_listings.extend(listings)

                # Check response size from appropriate key
                response_size = 0
                if isinstance(result, dict):
                    if "result" in result:
                        response_size = len(result["result"])
                    elif "body" in result:
                        response_size = len(result["body"])

                if response_size > 0 and response_size < 20:
                    break

                current_page += 1
                time.sleep(4)  # 페이지별 대기

        return all_listings

    def _parse_complex_listings(self, api_response: dict[str, Any] | list) -> list[dict[str, Any]]:
        """API 응답에서 매물 정보 파싱"""
        listings = []

        # API 응답이 배열일 경우와 객체일 경우를 모두 처리
        items = []
        if isinstance(api_response, list):
            items = api_response
        elif isinstance(api_response, dict) and "result" in api_response:
            items = api_response["result"]
        elif isinstance(api_response, dict):
            # 다른 가능한 키들 확인
            for key in ["body", "articles", "articleList", "list", "data"]:
                if key in api_response:
                    items = api_response[key]
                    break

        if not items:
            return listings

        for item in items:
            try:
                listing = {
                    "article_no": item.get("articleNo")
                    or item.get("atclNo")
                    or item.get("articleId"),
                    "trade_type_name": item.get("tradeTypeName") or item.get("tradeTpNm"),
                    "floor": item.get("floor") or item.get("flrInfo"),
                    "area": item.get("area2") or item.get("spc1") or item.get("representativeArea"),
                    "area_pyeong": item.get("area1"),
                    "price": item.get("price") or item.get("prcInfo") or item.get("sellingPrice"),
                    "rent_price": item.get("rentPrice") or item.get("rentPrc"),
                    "direction": item.get("direction"),
                    "description": item.get("description")
                    or item.get("tagList")
                    or item.get("articleFeatureDesc"),
                    "tag_list": item.get("tagList"),
                    "representative_image": item.get("representativeImgurl") or item.get("imgUrl"),
                    "room_count": item.get("roomCount") or item.get("roomCnt"),
                    "bathroom_count": item.get("bathroomCount") or item.get("bathCnt"),
                    "is_jeonse_key": item.get("isJeonseKey", False),
                    "is_immediately_available": item.get("isImmediate", False)
                    or item.get("mvInDt") == "즉시입주",
                    "is_heating_type": item.get("heatingType") or item.get("heatTpNm"),
                    "building_name": item.get("buildingName") or item.get("hscpNm"),
                    "reg_date": item.get("regDate") or item.get("atclYmd"),
                    "contact_agent_name": item.get("agentName") or item.get("rltrNm"),
                    "contact_tel1": item.get("tel1") or item.get("telNo"),
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

                # REST API URL (API 가이드에 따른 올바른 엔드포인트)
                api_url = (
                    f"https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice?"
                    f"complexNumber={complex_id}&"
                    f"pyeongTypeNumber={pyeong_type_number}&"
                    f"tradeType={trade_type}&"
                    f"page={page}&"
                    f"size=20"
                )

                try:
                    # REST API 호출
                    result = page_obj.evaluate(
                        """
                        async (url) => {
                            try {
                                const response = await fetch(url, {
                                    method: 'GET',
                                    headers: {
                                        'Accept': 'application/json, text/plain, */*',
                                        'Accept-Language': 'ko-KR,ko;q=0.9'
                                    }
                                });

                                if (!response.ok) {
                                    const errorText = await response.text();
                                    throw new Error(`HTTP ${response.status}: ${errorText}`);
                                }

                                return await response.json();
                            } catch (error) {
                                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                                    throw new Error('Network error: Failed to fetch');
                                }
                                throw error;
                            }
                        }
                        """,
                        api_url,
                    )

                    # 응답 확인 (REST API 형식)
                    if not result.get("isSuccess") or "result" not in result:
                        self.logger.error(
                            "invalid_transaction_response",
                            result=result,
                        )
                        break

                    api_result = result["result"]
                    transactions_list = api_result.get("list", [])

                    if not transactions_list:
                        self.logger.info(
                            "no_more_transactions",
                            complex_id=complex_id,
                            last_page=page - 1,
                        )
                        break

                    # 데이터 파싱
                    page_transactions = []
                    for txn in transactions_list:
                        if not txn:
                            continue

                        try:
                            # API 가이드에 따른 필드 매핑
                            transaction = {
                                "complex_id": complex_id,
                                "complex_name": complex_name,
                                "pyeong_type_number": pyeong_type_number,
                                "pyeong_name": pyeong_name,
                                "trade_date": txn.get("tradeDate"),
                                "trade_year": txn.get("tradeYear"),
                                "deal_price": txn.get("dealPrice"),
                                "deposit": txn.get("deposit"),
                                "monthly_rent": txn.get("monthlyRent"),
                                "floor": txn.get("floor"),
                                "trade_category": txn.get("tradeCategory"),
                                "is_delete": txn.get("isDelete"),
                                "is_renew": txn.get("isRenew"),
                                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            page_transactions.append(transaction)
                        except Exception as e:
                            self.logger.warning(
                                "failed_to_parse_transaction",
                                error=str(e),
                                transaction=txn,
                            )

                    all_transactions.extend(page_transactions)

                    self.logger.info(
                        "transaction_page_fetched",
                        complex_id=complex_id,
                        page=page,
                        count=len(page_transactions),
                    )

                    # 다음 페이지 확인
                    if not api_result.get("hasNextPage", False):
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

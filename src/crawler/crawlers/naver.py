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

        # 중심 좌표 계산
        center_lon = (bounds["leftLon"] + bounds["rightLon"]) / 2
        center_lat = (bounds["topLat"] + bounds["bottomLat"]) / 2

        # 모바일 API 사용 (데스크톱 API는 더 이상 작동하지 않음)
        api_url = (
            f"https://m.land.naver.com/cluster/ajax/complexList?"
            f"cortarNo={cortar_no}&"
            f"rletTpCd=APT&"  # 아파트
            f"tradTpCd=A1&"  # 매매
            f"z=17&"
            f"lat={center_lat}&"
            f"lon={center_lon}&"
            f"btm={bounds['bottomLat']}&"
            f"lft={bounds['leftLon']}&"
            f"top={bounds['topLat']}&"
            f"rgt={bounds['rightLon']}"
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
        # 모바일 API는 "result" 키에 데이터가 들어있음
        items = response.get("result", [])
        results = []

        for item in items:
            # HTML 태그 제거 함수 (가격 문자열에서 <em> 태그 제거)
            def clean_price(price_str: str) -> str:
                if not price_str:
                    return ""
                return price_str.replace("<em class='txt_unit'>", "").replace("</em>", "").strip()

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
                    "total_article_count": item.get("totalAtclCnt", 0),
                    "deal_price_min": clean_price(item.get("dealPrcMin", "")),
                    "deal_price_max": clean_price(item.get("dealPrcMax", "")),
                    "lease_price_min": clean_price(item.get("leasePrcMin", "")),
                    "lease_price_max": clean_price(item.get("leasePrcMax", "")),
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
                    self.checkpoint_manager.add_failed_dong(dong["cortarNo"], "Timeout after retries")
                    return []
                time.sleep(2**attempt)  # 지수 백오프
            except Exception as e:
                self.logger.error(
                    "fetch_error",
                    dong=dong.get("dong_name", ""),
                    error=str(e),
                )
                self.checkpoint_manager.add_failed_dong(dong["cortarNo"], str(e))
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
            # 페이지가 없으면 새로 생성
            if not self.page:
                browser = sync_playwright().start()
                self.page = browser.chromium.launch(headless=self.config.headless).new_page()
                self.page.goto("https://fin.land.naver.com/complexes")
                self.page.wait_for_load_state("networkidle")
                # 추가 대기 시간
                time.sleep(2)

            # 단지 상세 페이지에 먼저 접속하여 세션 확보
            self.logger.info("accessing_complex_page", complex_id=complex_id)
            self.page.goto(f"https://fin.land.naver.com/complexes/{complex_id}")
            self.page.wait_for_load_state("networkidle")
            time.sleep(3)  # 페이지 로딩 및 초기 API 호출 대기

            # 각 API 엔드포인트 호출
            for idx, endpoint_url in enumerate(endpoints):
                endpoint_name = endpoint_url.split("/")[-1].split("?")[0]
                self.logger.info("fetching_endpoint", endpoint=endpoint_name)

                try:
                    # 첫 호출 전에 더 긴 대기
                    if idx == 0:
                        time.sleep(3)

                    response = self.page.evaluate(
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
                                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                                    throw new Error('Network error: Failed to fetch');
                                }
                                throw error;
                            }
                        }
                        """,
                        endpoint_url,
                    )

                    detail_data[endpoint_name] = response
                    # Rate limiting - API 호출 간 3초 대기 (429 에러 방지)
                    if idx < len(endpoints) - 1:
                        time.sleep(3)

                except Exception as e:
                    self.logger.error(
                        "endpoint_fetch_error",
                        endpoint=endpoint_name,
                        error=str(e),
                    )
                    detail_data[endpoint_name] = {"error": str(e)}

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

    def _parse_complex_detail(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """API 응답 데이터를 파싱하여 필요한 정보 추출"""
        parsed = {
            "complex_id": raw_data.get("complex_id", ""),
            "fetched_at": raw_data.get("fetched_at", ""),
        }

        # 1. 평형 정보 파싱 (pyeongList)
        if "pyeongList" in raw_data and not raw_data["pyeongList"].get("error"):
            pyeong_data = raw_data["pyeongList"]
            if pyeong_data.get("isSuccess"):
                pyeong_list = pyeong_data.get("result", [])
                parsed["pyeong_types"] = []
                for pyeong in pyeong_list:
                    parsed["pyeong_types"].append({
                        "pyeong_type_number": pyeong.get("pyeongTypeNumber", 0),
                        "pyeong_name": pyeong.get("pyeongName", ""),
                        "supply_area": pyeong.get("supplyArea", ""),  # 공급면적
                        "exclusive_area": pyeong.get("exclusiveArea", ""),  # 전용면적
                        "room_count": pyeong.get("roomCount", ""),  # 방 개수
                        "bathroom_count": pyeong.get("bathroomCount", ""),  # 화장실 개수
                        "household_count": pyeong.get("householdCount", 0),  # 세대수
                    })

        # 2. 보유세 정보 파싱 (holdingTax)
        if "holdingTax" in raw_data and not raw_data["holdingTax"].get("error"):
            tax_data = raw_data["holdingTax"]
            if tax_data.get("isSuccess"):
                result = tax_data.get("result", {})
                parsed["holding_tax"] = {
                    "property_tax": result.get("propertyTax", 0),  # 재산세
                    "comprehensive_real_estate_tax": result.get("comprehensiveRealEstateTax", 0),  # 종부세
                    "total_tax": result.get("totalTax", 0),  # 총 보유세
                    "tax_base_year": result.get("taxBaseYear", ""),  # 과세 기준년도
                }

        # 3. 공시가격 정보 파싱 (pyeongType)
        if "pyeongType" in raw_data and not raw_data["pyeongType"].get("error"):
            declared_data = raw_data["pyeongType"]
            if declared_data.get("isSuccess"):
                result = declared_data.get("result", {})
                parsed["declared_value"] = {
                    "declared_price": result.get("declaredPrice", 0),  # 공시가격
                    "declared_price_per_pyeong": result.get("declaredPricePerPyeong", 0),  # 평당 공시가격
                    "declared_year": result.get("declaredYear", ""),  # 공시가격 기준년도
                }

        # 4. 매물 가격 분포 파싱 (askingPrice)
        if "askingPrice" in raw_data and not raw_data["askingPrice"].get("error"):
            price_data = raw_data["askingPrice"]
            if price_data.get("isSuccess"):
                result = price_data.get("result", {})
                parsed["asking_price"] = {
                    "min_price": result.get("minPrice", 0),  # 최저가
                    "max_price": result.get("maxPrice", 0),  # 최고가
                    "avg_price": result.get("avgPrice", 0),  # 평균가
                    "price_distribution": result.get("priceDistribution", []),  # 가격 분포
                }

        # 5. 최근 시세 파싱 (recent)
        if "recent" in raw_data and not raw_data["recent"].get("error"):
            market_data = raw_data["recent"]
            if market_data.get("isSuccess"):
                result = market_data.get("result", {})
                parsed["recent_market_price"] = {
                    "recent_price": result.get("recentPrice", 0),  # 최근 시세
                    "price_change_rate": result.get("priceChangeRate", 0),  # 변동률
                    "updated_date": result.get("updatedDate", ""),  # 업데이트 일자
                    "source": result.get("source", ""),  # 제공처 (KB, 한국부동산원 등)
                }

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

        # 페이지가 없으면 새로 생성
        if not self.page:
            browser = sync_playwright().start()
            self.page = browser.chromium.launch(headless=self.config.headless).new_page()
            self.page.goto("https://m.land.naver.com/complexes")
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)

        # 먼저 단지 페이지에 접속하여 세션 확보
        self.page.goto(f"https://m.land.naver.com/complex/{complex_id}")
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        all_listings = []
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
                result = self.page.evaluate(
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

    def _parse_complex_listings(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """
        매물 목록 API 응답을 파싱합니다.

        Args:
            response: API 응답 JSON

        Returns:
            파싱된 매물 정보 리스트
        """
        # 모바일 API는 "result" 키에 데이터가 들어있음
        items = response.get("result", [])

        if not items:
            return []

        listings = []

        for item in items:
            # 필드 추출 및 정제
            listing = {
                "article_id": item.get("atclNo", ""),  # 매물 ID
                "complex_id": item.get("hscpNo", ""),  # 단지 ID
                "complex_name": item.get("hscpNm", ""),  # 단지명
                "trade_type": item.get("tradTpCd", ""),  # 거래 유형 코드
                "trade_type_name": item.get("tradTpNm", ""),  # 거래 유형명
                "floor": item.get("flrInfo", ""),  # 층
                "area": item.get("spc1", ""),  # 전용면적
                "area_m2": item.get("prc", ""),  # 평수? (확인 필요)
                "price": item.get("prcInfo", ""),  # 가격
                "price_desc": item.get("prcDesc", ""),  # 가격 설명
                "direction": item.get("direction", ""),  # 방향
                "room_type": item.get("roomCnt", ""),  # 방 개수
                "bathroom_count": item.get("bathCnt", ""),  # 욕실 개수
                "heating_type": item.get("heatTpNm", ""),  # 난방 방식
                "supply_area": item.get("spc2", ""),  # 공급면적
                "move_in_date": item.get("mvInDt", ""),  # 입주 가능일
                "description": item.get("tagList", ""),  # 추가 정보 태그
                "article_url": item.get("atclUrl", ""),  # 매물 URL
                "image_count": item.get("imgCnt", 0),  # 이미지 개수
                "manage_cost": item.get("manageCost", ""),  # 관리비
                "manage_cost_include": item.get("manageCostIncld", ""),  # 관리비 포함 항목
                "parking": item.get("prk", ""),  # 주차
                "elevator": item.get("elv", ""),  # 엘리베이터
                "is_new_building": item.get("newHouse", ""),  # 신축 여부
                "is_direct_deal": item.get("directDeal", ""),  # 직거래 여부
                "real_estate_agent": item.get("rltrNm", ""),  # 부동산명
                "real_estate_phone": item.get("telNo", ""),  # 부동산 전화번호
                "service_report": item.get("certYn", ""),  # 서비스 리포트
                "article_date": item.get("atclYmd", ""),  # 매물 등록일
                "article_modify_date": item.get("atclMdfYmd", ""),  # 매물 수정일
                "view_count": item.get("readCnt", 0),  # 조회수
                "interest_count": item.get("intrCnt", 0),  # 관심 수
                "is_contract_renewal": item.get("cntnYn", ""),  # 계약 갱신권 여부
                "contract_renewal_price": item.get("cntnPrc", ""),  # 계약 갱신권 보증금
                "contract_renewal_fee": item.get("cntnRentPrc", ""),  # 계약 갱신권 월세
                "monthly_rent_fee": item.get("rentFee", ""),  # 월세
                "deposit": item.get("deposit", ""),  # 보증금
                "short_term_rental_available": item.get("shortRentYn", ""),  # 단기임대 가능 여부
                "special_provision": item.get("spcPrv", ""),  # 특약사항
            }

            listings.append(listing)

        self.logger.info(
            "parsed_listings",
            count=len(listings),
            fields=len(listings[0].keys()) if listings else 0,
        )

        return listings

    def crawl(self) -> list[dict[str, Any]]:
        """서울시 전체 구/동을 순회하며 크롤링"""
        self.logger.info("crawling_start")

        # 체크포인트 로드
        checkpoint = self.checkpoint_manager.load()
        last_dong = checkpoint.get("last_dong") if checkpoint else None
        if last_dong:
            self.logger.info("checkpoint_loaded", last_dong=last_dong)

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

            # 체크포인트에서부터 시작하기 위한 플래그
            should_start_crawling = last_dong is None

            for district in self.districts_data["districts"]:
                for dong in district["dongs"]:
                    # last_dong을 찾을 때까지 건너뛰기
                    if not should_start_crawling:
                        if dong["cortarNo"] == last_dong:
                            should_start_crawling = True
                            self.logger.info("resuming_from_checkpoint", dong=dong["dong_name"])
                            # 마지막으로 처리한 동은 다시 처리하지 않고 건너뛰기
                            completed_count += 1
                            continue
                        else:
                            self.logger.info("skipping_dong", dong=dong["dong_name"])
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

                    # 체크포인트 저장 - 마지막으로 완료한 동만 기록
                    self.checkpoint_manager.save(dong["cortarNo"])

                    completed_count += 1

            browser.close()

        self.logger.info("crawling_complete", total_complexes=len(all_results))
        return all_results

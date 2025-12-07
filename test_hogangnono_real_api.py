#!/usr/bin/env python3
"""
호갱노노 실제 API 엔드포인트 테스트 스크립트
"""

import time
import requests
import json
from datetime import datetime
from typing import Dict, Optional
import statistics


class HogangnonoRealAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://hogangnono.com"

        # 실제 브라우저에서 사용하는 헤더
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Sec-Ch-Ua": '"Chromium";v="142", "Google Chrome";v="142", "Not(A:Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        # 테스트 결과 저장
        self.results = {
            "successful_requests": [],
            "failed_requests": [],
            "rate_limit_errors": [],
            "response_times": [],
        }

    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """API 요청을 보내고 결과를 반환"""
        start_time = time.time()

        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)

            end_time = time.time()
            response_time = end_time - start_time

            result = {
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response_time,
                "headers": dict(response.headers),
                "url": str(response.url),
            }

            # Rate Limiting 관련 헤더 확인
            rate_limit_headers = {}
            for header_name in response.headers:
                if any(
                    key in header_name.lower() for key in ["rate", "limit", "x-rl", "x-ratelimit"]
                ):
                    rate_limit_headers[header_name] = response.headers[header_name]

            if rate_limit_headers:
                result["rate_limit_headers"] = rate_limit_headers

            # 응답 처리
            if response.status_code == 200:
                try:
                    result["data"] = response.json()
                    self.results["successful_requests"].append(result)
                except json.JSONDecodeError:
                    result["data"] = response.text[:500]  # 첫 500자만 저장
                    self.results["successful_requests"].append(result)
            elif response.status_code == 429:
                self.results["rate_limit_errors"].append(result)
                print(f"⚠️  429 Rate Limit Error 발생! (응답 시간: {response_time:.2f}초)")
            else:
                self.results["failed_requests"].append(result)
                print(f"❌ 요청 실패: {response.status_code} (응답 시간: {response_time:.2f}초)")

            self.results["response_times"].append(response_time)
            return result

        except requests.exceptions.RequestException as e:
            end_time = time.time()
            result = {
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "error": str(e),
                "response_time": end_time - start_time,
                "type": "network_error",
            }
            self.results["failed_requests"].append(result)
            print(f"🔴 네트워크 에러: {e}")
            return result

    def test_basic_endpoints(self):
        """기본 API 엔드포인트 테스트"""
        print("\n🔍 기본 API 엔드포인트 테스트")
        print("-" * 50)

        # 확인된 기본 엔드포인트들
        endpoints = [
            ("/get/config", None),
            ("/api/me", None),  # 인증 필요 (401 예상)
            (
                "/api/v2/maps/region",
                {"lat": 37.51655253697078, "lng": 127.0401375821117, "zoom": 13},
            ),
            ("/api/v2/notices/check-new", None),
            ("/api/v2/apts/recent-visits", {"list": "gDG7d:0:0", "hideUserTopApt": False}),
            ("/api/v2/ranks/rolling", None),
            ("/api/v2/new-feature-guides", None),
        ]

        for endpoint, params in endpoints:
            print(f"\n테스트: {endpoint}")
            result = self.make_request(endpoint, params)

            if result.get("status_code") == 200:
                print(f"✅ 성공 ({result['response_time']:.2f}s)")
            elif result.get("status_code") == 401:
                print(f"🔐 인증 필요 ({result['response_time']:.2f}s)")
            elif result.get("status_code") == 429:
                print(f"⚠️  Rate Limited ({result['response_time']:.2f}s)")
            else:
                print(f"❌ 실패 ({result.get('status_code', 'N/A')})")

            # 요청 간격
            time.sleep(0.5)

    def test_apartment_search(self):
        """아파트 검색 API 테스트"""
        print("\n🏢 아파트 검색 API 테스트")
        print("-" * 50)

        # 실제 사용되는 아파트 검색 API
        endpoint = "/api/apt/bounding"
        params = {
            "map": "google",
            "level": 17,
            "screenWidth": 1200,
            "screenHeight": 924,
            "apt": True,  # 아파트
            "areaNo": "",
            "startX": 127.0337003,
            "endX": 127.0465749,
            "startY": 37.5126209,
            "endY": 37.520484,
            "tradeType": 0,  # 0: 전체, 1: 매매, 2: 전세, 3: 월세
            "areaFrom": 0,
            "areaTo": 80,
            "priceFrom": 0,
            "priceTo": 401000,
            "gapPriceFrom": 0,
            "gapPriceTo": 151000,
            "gapPriceNeg": False,
            "sinceFrom": 0,
            "sinceTo": 30,
            "floorAreaRatioFrom": 0,
            "floorAreaRatioTo": 900,
            "buildingCoverageRatioFrom": 0,
            "buildingCoverageRatioTo": 100,
            "rentalBusinessRatioFrom": 0,
            "rentalBusinessRatioTo": 100,
            "householdFrom": 0,
            "householdTo": 5000,
            "parking": 0,
            "profitRatio": 0,
            "rentRateFrom": 0,
            "rentRateTo": 200,
            "aptType": -1,
            "isIgnorePin": False,
            "auctionState": -1,
            "reconstructionStep": 0,
            "reconstructionStepFrom": 1,
            "reconstructionStepTo": 10,
            "r": int(time.time()),  # 랜덤 파라미터
        }

        print(f"\n테스트: {endpoint}")
        result = self.make_request(endpoint, params)

        if result.get("status_code") == 200:
            data = result.get("data", {})
            if isinstance(data, dict):
                if "list" in data:
                    print(
                        f"✅ 성공 - {len(data['list'])}개의 매물 발견 ({result['response_time']:.2f}s)"
                    )
                elif "items" in data:
                    print(
                        f"✅ 성공 - {len(data['items'])}개의 매물 발견 ({result['response_time']:.2f}s)"
                    )
                else:
                    print(f"✅ 성공 ({result['response_time']:.2f}s)")
                    print(f"   응답 키: {list(data.keys())}")
        else:
            print(f"❌ 실패 ({result.get('status_code', 'N/A')})")

    def test_rapid_requests(self, count: int = 20, interval: float = 0.1):
        """짧은 간격으로 빠른 요청 보내기"""
        print(f"\n🚀 빠른 요청 테스트: {count}회 요청, {interval}초 간격")
        print("-" * 50)

        endpoint = "/get/config"  # 가장 간단한 엔드포인트

        for i in range(count):
            print(f"요청 {i+1}/{count}... ", end="")
            result = self.make_request(endpoint)

            if result.get("status_code") == 200:
                print(f"✅ 성공 ({result['response_time']:.2f}s)")
            elif result.get("status_code") == 429:
                print(f"⚠️  Rate Limited ({result['response_time']:.2f}s)")
                break
            else:
                print(f"❌ 실패 ({result.get('status_code', 'N/A')})")

            if interval > 0:
                time.sleep(interval)

    def test_different_intervals(self):
        """다른 간격으로 요청 테스트"""
        print("\n⏱️  다른 요청 간격 테스트")
        print("-" * 50)

        endpoint = "/api/v2/ranks/rolling"
        intervals = [0.1, 0.2, 0.5, 1.0]

        for interval in intervals:
            print(f"\n{interval}초 간격으로 10회 요청:")
            success_count = 0
            rate_limit_count = 0

            for i in range(10):
                result = self.make_request(endpoint)
                if result.get("status_code") == 200:
                    success_count += 1
                elif result.get("status_code") == 429:
                    rate_limit_count += 1
                    break

                time.sleep(interval)

            print(f"  성공: {success_count}회, Rate Limited: {rate_limit_count}회")

    def test_concurrent_ips_simulation(self):
        """다른 IP에서의 요청 시뮬레이션 (User-Agent 변경)"""
        print("\n🌍 다른 클라이언트 시뮬레이션 (User-Agent 변경)")
        print("-" * 50)

        # 다양한 User-Agent 목록
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        ]

        endpoint = "/api/v2/ranks/rolling"

        for i, ua in enumerate(user_agents):
            print(f"\n클라이언트 {i+1} (User-Agent: {ua[:50]}...)")
            self.session.headers["User-Agent"] = ua

            # 빠르게 5회 요청
            rate_limited = False
            for j in range(5):
                result = self.make_request(endpoint)
                if result.get("status_code") == 429:
                    print(f"  ⚠️  {j+1}회째 요청에서 Rate Limited")
                    rate_limited = True
                    break
                elif j == 4:  # 5회 모두 성공
                    print("  ✅ 5회 모두 성공")
                time.sleep(0.1)

            if rate_limited:
                print("  30초 대기...")
                time.sleep(30)

    def analyze_results(self):
        """테스트 결과 분석"""
        print("\n\n📊 테스트 결과 분석")
        print("=" * 50)

        successful = len(self.results["successful_requests"])
        failed = len(self.results["failed_requests"])
        rate_limited = len(self.results["rate_limit_errors"])
        total = successful + failed + rate_limited

        print("\n📈 요청 통계:")
        print(f"  총 요청: {total}")
        print(f"  성공: {successful} ({successful/total*100:.1f}%)")
        print(f"  실패: {failed} ({failed/total*100:.1f}%)")
        print(f"  Rate Limited: {rate_limited} ({rate_limited/total*100:.1f}%)")

        if self.results["response_times"]:
            print("\n⏱️  응답 시간 통계:")
            avg_time = statistics.mean(self.results["response_times"])
            min_time = min(self.results["response_times"])
            max_time = max(self.results["response_times"])
            print(f"  평균: {avg_time:.2f}초")
            print(f"  최소: {min_time:.2f}초")
            print(f"  최대: {max_time:.2f}초")

        # Rate Limiting 관련 헤더 분석
        all_headers = set()
        for req in self.results["successful_requests"] + self.results["rate_limit_errors"]:
            if "rate_limit_headers" in req:
                all_headers.update(req["rate_limit_headers"].keys())

        if all_headers:
            print("\n🏷️  Rate Limiting 관련 헤더:")
            for header in sorted(all_headers):
                print(f"  {header}")
        else:
            print("\n🏷️  Rate Limiting 관련 헤더: 발견되지 않음")

        # 429 에러 분석
        if self.results["rate_limit_errors"]:
            print("\n⚠️  Rate Limiting 에러 분석:")
            for error in self.results["rate_limit_errors"]:
                print(f"  시간: {error['timestamp']}")
                print(f"  엔드포인트: {error['endpoint']}")
                print(f"  응답 시간: {error['response_time']:.2f}초")
                if "rate_limit_headers" in error:
                    print(f"  헤더: {error['rate_limit_headers']}")
                print()

    def save_results(self, filename: str = "hogangnono_real_api_test_results.json"):
        """테스트 결과를 파일로 저장"""

        # datetime 객체를 문자열로 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        # 결과를 JSON 직렬화 가능한 형태로 변환
        serializable_results = {}
        for key, value in self.results.items():
            serializable_results[key] = []
            for item in value:
                if isinstance(item, dict):
                    # 각 딕셔너리의 모든 datetime 객체를 변환
                    converted_item = {}
                    for k, v in item.items():
                        if isinstance(v, datetime):
                            converted_item[k] = v.isoformat()
                        else:
                            converted_item[k] = v
                    serializable_results[key].append(converted_item)
                else:
                    serializable_results[key].append(item)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n💾 테스트 결과가 '{filename}' 파일에 저장되었습니다.")


def main():
    """메인 테스트 실행"""
    print("🔍 호갱노노 실제 API 엔드포인트 및 Rate Limiting 테스트")
    print("=" * 50)
    print("테스트 시작 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    tester = HogangnonoRealAPITester()

    try:
        # 1. 기본 엔드포인트 테스트
        tester.test_basic_endpoints()

        # 2. 아파트 검색 API 테스트
        tester.test_apartment_search()

        # 3. 빠른 요청 테스트
        tester.test_rapid_requests(count=30, interval=0.1)

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 4. 다른 간격 테스트
        tester.test_different_intervals()

        # 5. 다른 클라이언트 시뮬레이션
        tester.test_concurrent_ips_simulation()

    except KeyboardInterrupt:
        print("\n\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    # 결과 분석 및 저장
    tester.analyze_results()
    tester.save_results()

    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()

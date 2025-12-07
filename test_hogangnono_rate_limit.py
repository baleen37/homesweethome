#!/usr/bin/env python3
"""
호갱노노 Rate Limiting 정책 실제 테스트 스크립트
"""

import time
import requests
import json
from datetime import datetime
from typing import Dict, Optional
import statistics


class HogangnonoRateLimitTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://api.hogangnono.com"

        # 실제 모바일 브라우저 헤더 설정
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                "Content-Type": "application/json",
                "Origin": "https://m.hogangnono.com",
                "Referer": "https://m.hogangnono.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
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
            response = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=10)

            end_time = time.time()
            response_time = end_time - start_time

            result = {
                "timestamp": datetime.now(),
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
                "error": str(e),
                "response_time": end_time - start_time,
                "type": "network_error",
            }
            self.results["failed_requests"].append(result)
            print(f"🔴 네트워크 에러: {e}")
            return result

    def test_rapid_requests(self, count: int = 20, interval: float = 0.1):
        """짧은 간격으로 빠른 요청 보내기"""
        print(f"\n🚀 빠른 요청 테스트: {count}회 요청, {interval}초 간격")
        print("-" * 50)

        # 테스트용 API 엔드포인트 (부동산 매물 검색)
        endpoint = "/api/v1/search/properties"
        params = {
            "locationCode": "1100000000",  # 서울특별시
            "tradeType": "매매",
            "propertyType": "아파트",
            "page": 1,
            "size": 20,
        }

        for i in range(count):
            print(f"요청 {i+1}/{count}... ", end="")
            result = self.make_request(endpoint, params)

            if result.get("status_code") == 200:
                print(f"✅ 성공 ({result['response_time']:.2f}s)")
            elif result.get("status_code") == 429:
                print(f"⚠️  Rate Limited ({result['response_time']:.2f}s)")
                break  # Rate Limit 걸리면 중단
            else:
                print(f"❌ 실패 ({result.get('status_code', 'N/A')})")

            if interval > 0:
                time.sleep(interval)

    def test_sustained_requests(self, duration_minutes: int = 2, interval: float = 0.5):
        """지속적인 요청 테스트 (지정된 시간 동안)"""
        print(f"\n⏱️  지속적 요청 테스트: {duration_minutes}분 동안 {interval}초 간격으로 요청")
        print("-" * 50)

        endpoint = "/api/v1/search/properties"
        params = {
            "locationCode": "1100000000",  # 서울특별시
            "tradeType": "매매",
            "propertyType": "아파트",
            "page": 1,
            "size": 20,
        }

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        request_count = 0

        while time.time() < end_time:
            request_count += 1
            elapsed = time.time() - start_time
            print(f"[{elapsed:.0f}s] 요청 {request_count}... ", end="")

            result = self.make_request(endpoint, params)

            if result.get("status_code") == 200:
                print(f"✅ 성공 ({result['response_time']:.2f}s)")
            elif result.get("status_code") == 429:
                print("⚠️  Rate Limited! 테스트 중단")
                break
            else:
                print(f"❌ 실패 ({result.get('status_code', 'N/A')})")

            time.sleep(interval)

        print(f"\n총 {request_count}회 요청 완료")

    def test_burst_requests(self, burst_size: int = 10, burst_count: int = 3):
        """버스트 요청 테스트 (한 번에 여러 요청 후 대기)"""
        print(f"\n💥 버스트 요청 테스트: {burst_count}번에 걸쳐 {burst_size}회씩 요청")
        print("-" * 50)

        endpoint = "/api/v1/search/properties"
        params = {
            "locationCode": "1100000000",
            "tradeType": "매매",
            "propertyType": "아파트",
            "page": 1,
            "size": 20,
        }

        for burst in range(burst_count):
            print(f"\n버스트 {burst + 1}/{burst_count}:")
            rate_limited = False

            for i in range(burst_size):
                print(f"  요청 {i+1}/{burst_size}... ", end="")
                result = self.make_request(endpoint, params)

                if result.get("status_code") == 200:
                    print("✅ 성공")
                elif result.get("status_code") == 429:
                    print("⚠️  Rate Limited!")
                    rate_limited = True
                    break
                else:
                    print("❌ 실패")

            if not rate_limited and burst < burst_count - 1:
                print("30초 대기...")
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

        # 429 에러 분석
        if self.results["rate_limit_errors"]:
            print("\n⚠️  Rate Limiting 에러 분석:")
            for error in self.results["rate_limit_errors"]:
                print(f"  시간: {error['timestamp']}")
                print(f"  응답 시간: {error['response_time']:.2f}초")
                if "rate_limit_headers" in error:
                    print(f"  헤더: {error['rate_limit_headers']}")
                print()

    def save_results(self, filename: str = "hogangnono_rate_limit_test_results.json"):
        """테스트 결과를 파일로 저장"""

        # datetime 객체를 문자열로 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        serializable_results = {}
        for key, value in self.results.items():
            serializable_results[key] = []
            for item in value:
                serializable_results[key].append(convert_datetime(item))

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 테스트 결과가 '{filename}' 파일에 저장되었습니다.")


def main():
    """메인 테스트 실행"""
    print("🔍 호갱노노 Rate Limiting 정책 실제 테스트")
    print("=" * 50)
    print("테스트 시작 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    tester = HogangnonoRateLimitTester()

    try:
        # 1. 빠른 요청 테스트 (0.1초 간격)
        tester.test_rapid_requests(count=20, interval=0.1)

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 2. 지속적 요청 테스트 (2분 동안 0.5초 간격)
        tester.test_sustained_requests(duration_minutes=2, interval=0.5)

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 3. 버스트 요청 테스트
        tester.test_burst_requests(burst_size=10, burst_count=3)

    except KeyboardInterrupt:
        print("\n\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 중 오류 발생: {e}")

    # 결과 분석 및 저장
    tester.analyze_results()
    tester.save_results()

    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()

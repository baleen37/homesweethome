#!/usr/bin/env python3
"""
호갱노노 최종 Rate Limiting 테스트 - 다양한 엔드포인트로 확인
"""

import time
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random


class HogangnonoFinalTester:
    def __init__(self):
        self.base_url = "https://hogangnono.com"
        self.results = {"requests": [], "rate_limits": [], "errors": []}

    def get_session(self, user_agent_override=None):
        """새 세션 생성"""
        session = requests.Session()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        if user_agent_override:
            headers["User-Agent"] = user_agent_override
        else:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
            )

        session.headers.update(headers)
        return session

    def test_endpoint(self, session, endpoint, params=None):
        """단일 엔드포인트 테스트"""
        try:
            start_time = time.time()
            response = session.get(f"{self.base_url}{endpoint}", params=params, timeout=5)
            end_time = time.time()

            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "timestamp": datetime.now(),
                "headers": dict(response.headers),
            }

            # Rate Limit 관련 헤더 확인
            rate_headers = {}
            for k, v in response.headers.items():
                if any(key in k.lower() for key in ["rate", "limit", "x-rl", "x-ratelimit"]):
                    rate_headers[k] = v

            if rate_headers:
                result["rate_limit_headers"] = rate_headers

            self.results["requests"].append(result)

            if response.status_code == 429:
                self.results["rate_limits"].append(result)
                print(f"⚠️  Rate Limit: {endpoint}")
            elif response.status_code >= 400:
                self.results["errors"].append(result)
                if response.status_code != 401:  # 401은 인증 필요로 정상
                    print(f"❌ Error {response.status_code}: {endpoint}")

            return result

        except Exception as e:
            error_result = {"endpoint": endpoint, "error": str(e), "timestamp": datetime.now()}
            self.results["errors"].append(error_result)
            print(f"🔴 Exception: {endpoint} - {e}")
            return error_result

    def test_various_endpoints_rapid(self, count: int = 100):
        """다양한 엔드포인트를 빠르게 테스트"""
        print(f"\n🚀 다양한 엔드포인트 빠른 테스트: {count}회 요청")
        print("-" * 50)

        endpoints = [
            ("/get/config", None),
            ("/api/v2/maps/region", {"lat": 37.5, "lng": 127.0, "zoom": 13}),
            ("/api/v2/apts/recent-visits", {"list": "gDG7d:0:0", "hideUserTopApt": False}),
            ("/api/v2/ranks/rolling", None),
            ("/api/v2/new-feature-guides", None),
            (
                "/api/v2/pois-bounding",
                {"level": 17, "startX": 127.0, "endX": 127.1, "startY": 37.5, "endY": 37.6},
            ),
        ]

        session = self.get_session()

        for i in range(count):
            # 랜덤하게 엔드포인트 선택
            endpoint, params = random.choice(endpoints)
            self.test_endpoint(session, endpoint, params)

            # 간격 없음
            # time.sleep(0)

        print(f"\n요청 완료: 총 {count}회")

    def test_heavy_load(self):
        """고부하 테스트 - 여러 IP/세션 시뮬레이션"""
        print("\n🔥 고부하 테스트 - 여러 클라이언트 시뮬레이션")
        print("-" * 50)

        # 다양한 User-Agent 목록
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]

        endpoint = "/get/config"
        requests_per_ua = 100

        with ThreadPoolExecutor(max_workers=len(user_agents)) as executor:
            futures = []

            for ua in user_agents:
                session = self.get_session(ua)
                for i in range(requests_per_ua):
                    futures.append(executor.submit(self.test_endpoint, session, endpoint))

            # 모든 요청 완료 대기
            for future in futures:
                future.result()

        print(f"총 요청: {len(user_agents) * requests_per_ua}회")

    def test_auth_required_endpoints(self):
        """인증이 필요한 엔드포인트 테스트"""
        print("\n🔐 인증 필요 엔드포인트 테스트")
        print("-" * 50)

        auth_endpoints = [
            "/api/me",
            "/api/v2/user/preferences",
            "/api/v2/user/recent-searches",
            "/api/v2/user/favorites",
        ]

        session = self.get_session()

        for endpoint in auth_endpoints:
            for i in range(10):  # 각 엔드포인트 10회씩 요청
                self.test_endpoint(session, endpoint)
                time.sleep(0.1)

    def analyze_results(self):
        """결과 분석"""
        print("\n\n📊 최종 결과 분석")
        print("=" * 50)

        total = len(self.results["requests"])
        rate_limited = len(self.results["rate_limits"])
        errors = len(self.results["errors"])

        print("\n📈 요청 통계:")
        print(f"  총 요청: {total}")
        print(f"  성공: {total - rate_limited - errors}")
        print(
            f"  Rate Limited: {rate_limited} ({rate_limited/total*100:.1f}%)"
            if total > 0
            else "N/A"
        )
        print(f"  기타 오류: {errors}")

        if self.results["rate_limits"]:
            print("\n⚠️  Rate Limiting 상세:")
            for rl in self.results["rate_limits"]:
                print(f"  - {rl['endpoint']} at {rl['timestamp']}")
                if "rate_limit_headers" in rl:
                    print(f"    헤더: {rl['rate_limit_headers']}")

        # 응답 시간 통계
        response_times = [
            r["response_time"] for r in self.results["requests"] if "response_time" in r
        ]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            print("\n⏱️  응답 시간:")
            print(f"  평균: {avg_time:.3f}초")
            print(f"  최소: {min_time:.3f}초")
            print(f"  최대: {max_time:.3f}초")

    def save_results(self):
        """결과 저장"""
        with open("hogangnono_final_test_results.json", "w", encoding="utf-8") as f:
            # datetime 객체를 문자열로 변환
            def convert(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            json.dump(self.results, f, ensure_ascii=False, indent=2, default=convert)
        print("\n💾 결과가 'hogangnono_final_test_results.json'에 저장되었습니다.")


def main():
    """메인 실행"""
    print("🔍 호갱노노 최종 Rate Limiting 테스트")
    print("=" * 50)
    print("시작 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    tester = HogangnonoFinalTester()

    try:
        # 1. 다양한 엔드포인트 빠른 테스트
        tester.test_various_endpoints_rapid(count=200)

        # 잠시 대기
        print("\n10초 대기...")
        time.sleep(10)

        # 2. 고부하 테스트
        tester.test_heavy_load()

        # 잠시 대기
        print("\n10초 대기...")
        time.sleep(10)

        # 3. 인증 필요 엔드포인트 테스트
        tester.test_auth_required_endpoints()

    except KeyboardInterrupt:
        print("\n\n⏹️  테스트 중단")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    # 결과 분석
    tester.analyze_results()
    tester.save_results()

    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()

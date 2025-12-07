#!/usr/bin/env python3
"""
호갱노노 Rate Limiting 스트레스 테스트
"""

import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict


class HogangnonoStressTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://hogangnono.com"

        # 실제 브라우저 헤더
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            }
        )

        self.results = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "rate_limited": 0,
            "start_time": None,
            "end_time": None,
        }

    def single_request(self, thread_id: int, request_id: int) -> Dict:
        """단일 요청 수행"""
        try:
            response = self.session.get(f"{self.base_url}/get/config", timeout=5)

            result = {
                "thread_id": thread_id,
                "request_id": request_id,
                "status_code": response.status_code,
                "timestamp": datetime.now(),
                "response_time": response.elapsed.total_seconds(),
            }

            if response.status_code == 200:
                self.results["successful"] += 1
                result["status"] = "success"
            elif response.status_code == 429:
                self.results["rate_limited"] += 1
                result["status"] = "rate_limited"
                print(f"⚠️  Thread {thread_id}: Rate Limit 발생!")
            else:
                self.results["failed"] += 1
                result["status"] = "failed"

            self.results["total_requests"] += 1
            return result

        except Exception as e:
            self.results["failed"] += 1
            self.results["total_requests"] += 1
            return {
                "thread_id": thread_id,
                "request_id": request_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(),
            }

    def test_concurrent_requests(self, threads: int = 5, requests_per_thread: int = 50):
        """동시 요청 테스트"""
        print(f"\n🔥 동시 요청 테스트: {threads}개 스레드, 각 {requests_per_thread}회 요청")
        print("-" * 50)

        self.results["start_time"] = datetime.now()

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []

            # 각 스레드에 대한 요청 생성
            for thread_id in range(threads):
                for req_id in range(requests_per_thread):
                    futures.append(executor.submit(self.single_request, thread_id, req_id))
                    # 스레드 간 약간의 지연
                    time.sleep(0.01)

            # 결과 수집
            for future in as_completed(futures):
                future.result()  # 결과만 처리

        self.results["end_time"] = datetime.now()

        duration = (self.results["end_time"] - self.results["start_time"]).total_seconds()
        rps = self.results["total_requests"] / duration if duration > 0 else 0

        print("\n테스트 완료:")
        print(f"  총 요청: {self.results['total_requests']}")
        print(f"  성공: {self.results['successful']}")
        print(f"  실패: {self.results['failed']}")
        print(f"  Rate Limited: {self.results['rate_limited']}")
        print(f"  소요 시간: {duration:.2f}초")
        print(f"  초당 요청수 (RPS): {rps:.2f}")

    def test_sustained_load(self, duration_minutes: int = 2, target_rps: int = 10):
        """지속적인 부하 테스트"""
        print(f"\n⏱️  지속적 부하 테스트: {duration_minutes}분 동안 초당 {target_rps}회 요청")
        print("-" * 50)

        self.results["start_time"] = datetime.now()
        end_time = self.results["start_time"].timestamp() + (duration_minutes * 60)
        request_interval = 1.0 / target_rps

        request_count = 0

        while time.time() < end_time:
            start_time = time.time()

            # 요청 수행
            result = self.single_request(0, request_count)
            if result.get("status") == "rate_limited":
                print(f"⚠️  {request_count}회째 요청에서 Rate Limit 발생!")
                break

            request_count += 1

            # 다음 요청까지 대기
            elapsed = time.time() - start_time
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)

        self.results["end_time"] = datetime.now()

        print("\n테스트 완료:")
        print(f"  총 요청: {request_count}")
        print(f"  성공: {self.results['successful']}")
        print(f"  실패: {self.results['failed']}")
        print(f"  Rate Limited: {self.results['rate_limited']}")

    def test_burst_patterns(self):
        """버스트 패턴 테스트"""
        print("\n💥 버스트 패턴 테스트")
        print("-" * 50)

        patterns = [
            {"name": "짧은 버스트", "requests": 50, "interval": 0.05, "wait": 5},
            {"name": "중간 버스트", "requests": 100, "interval": 0.1, "wait": 10},
            {"name": "긴 버스트", "requests": 200, "interval": 0.2, "wait": 20},
        ]

        for pattern in patterns:
            print(
                f"\n{pattern['name']}: {pattern['requests']}회 요청, {pattern['interval']}초 간격"
            )
            rate_limited = False

            for i in range(pattern["requests"]):
                result = self.single_request(0, i)

                if result.get("status") == "rate_limited":
                    print(f"  ⚠️  {i+1}회째 요청에서 Rate Limit 발생!")
                    rate_limited = True
                    break

                time.sleep(pattern["interval"])

            if not rate_limited:
                print(f"  ✅ {pattern['requests']}회 모두 성공")

            print(f"  {pattern['wait']}초 대기...")
            time.sleep(pattern["wait"])

    def test_exponential_increase(self):
        """지수적 증가 테스트"""
        print("\n📈 지수적 증가 테스트")
        print("-" * 50)

        # 1, 2, 4, 8, 16, 32, 64, 128... 개씩 요청
        batch_sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256]

        for batch_size in batch_sizes:
            print(f"\n{batch_size}회 연속 요청:")
            rate_limited = False

            for i in range(batch_size):
                result = self.single_request(0, i)

                if result.get("status") == "rate_limited":
                    print(f"  ⚠️  {i+1}회째 요청에서 Rate Limit 발생!")
                    rate_limited = True
                    break

            if not rate_limited:
                print(f"  ✅ {batch_size}회 모두 성공")
            else:
                print("  🔴 Rate Limit 감지, 테스트 중단")
                break

            # 다음 배치 전 대기
            time.sleep(2)


def main():
    """메인 테스트 실행"""
    print("🔥 호갱노노 Rate Limiting 스트레스 테스트")
    print("=" * 50)
    print("테스트 시작 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\n⚠️  경고: 이 테스트는 서버에 부하를 줄 수 있습니다.")
    print("⚠️  테스트는 5초 후 시작됩니다...")

    time.sleep(5)

    tester = HogangnonoStressTester()

    try:
        # 1. 동시 요청 테스트
        tester.test_concurrent_requests(threads=10, requests_per_thread=20)

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 2. 지속적 부하 테스트
        tester.test_sustained_load(duration_minutes=1, target_rps=20)

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 3. 버스트 패턴 테스트
        tester.test_burst_patterns()

        # 잠시 대기
        print("\n30초 대기...")
        time.sleep(30)

        # 4. 지수적 증가 테스트
        tester.test_exponential_increase()

    except KeyboardInterrupt:
        print("\n\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    print("\n\n✅ 모든 테스트 완료")


if __name__ == "__main__":
    main()

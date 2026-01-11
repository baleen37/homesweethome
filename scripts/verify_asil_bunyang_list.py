#!/usr/bin/env python3
"""ASIL 분양 목록 API 응답 구조 확인 스크립트

이 스크립트는 ASIL의 분양 목록 API(data_bunyang_list.jsp)를 호출하여
실제 응답 구조를 확인하고 DTO 설계에 필요한 정보를 수집합니다.
"""

import json
import sys
from urllib.request import Request, urlopen


def test_bunyang_api():
    """분양 목록 API 테스트 및 응답 구조 확인"""

    # API 엔드포인트
    base_url = "https://asil.kr/app/data/data_bunyang_list.jsp"

    # 테스트 파라미터 조합 시도
    test_cases = [
        {
            "name": "서울 전체",
            "params": {
                "u": "",
                "area": "11",
                "type": "",
                "page": "1",
                "total": "100",
            },
        },
        {"name": "파라미터 없음", "params": {}},
        {
            "name": "다른 area 값",
            "params": {
                "area": "",
                "page": "1",
            },
        },
    ]

    for test_case in test_cases:
        print(f"\n{'=' * 80}")
        print(f"Test case: {test_case['name']}")
        print(f"{'=' * 80}")

        params = test_case["params"]
        url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

        print(f"API URL: {url}")
        print("-" * 80)

        try:
            # HTTP 요청
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://asil.kr/",
                },
            )

            with urlopen(request, timeout=10) as response:
                # UTF-8 디코딩 (다른 /app/data/ API들과 동일한 패턴)
                content = response.read().decode("utf-8")
                print("Response encoding: UTF-8")
                print(f"Response length: {len(content)} bytes")
                print()

                # JSON 파싱
                data = json.loads(content)

                print(f"Response type: {type(data)}")
                print(f"Response length: {len(data) if isinstance(data, list) else 'N/A'}")
                print()

                # 첫 번째 항목 구조 확인
                if isinstance(data, list) and len(data) > 0:
                    first_item = data[0]
                    print("First item structure:")
                    print(json.dumps(first_item, indent=2, ensure_ascii=False))
                    print()
                    print("First item fields:")
                    for key, value in first_item.items():
                        print(f"  {key}: {type(value).__name__} = {repr(value)}")

                    # 전체 응답 요약
                    print()
                    print(f"Total items: {len(data)}")
                    if len(data) > 1:
                        print()
                        print("Second item structure (for comparison):")
                        print(json.dumps(data[1], indent=2, ensure_ascii=False))

                    return data
                else:
                    print("Empty response or non-list data")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    return None


if __name__ == "__main__":
    result = test_bunyang_api()
    if result:
        print()
        print("=" * 80)
        print("API call successful!")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("API call failed!")
        print("=" * 80)
        sys.exit(1)

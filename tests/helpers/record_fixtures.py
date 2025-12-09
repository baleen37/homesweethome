"""API 응답 Fixture 수집 스크립트

실제 호갱노노 API를 호출하여 응답을 JSON 파일로 저장합니다.
API 변경 감지 및 파싱 로직 단위 테스트용으로 사용됩니다.
"""

import json
import requests
from pathlib import Path


def record_fixtures() -> None:
    """필요 최소한의 fixtures만 수집"""
    print("호갱노노 API Fixtures 수집 시작...")

    # 세션 생성 및 쿠키 획득
    session = requests.Session()
    print("1. 메인 페이지 접속 (쿠키 획득)...")
    session.get("https://hogangnono.com")

    # Fixtures 디렉토리 생성
    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(exist_ok=True)

    # 1. regions API 응답 저장
    print("2. /api/v2/regions API 호출...")
    resp = session.get(
        "https://hogangnono.com/api/v2/regions", headers={"X-Requested-With": "XMLHttpRequest"}
    )

    if resp.status_code == 200:
        save_json(fixtures_dir / "hogangnono_regions_response.json", resp.json())
        print("   ✓ regions API 응답 저장")
    else:
        print(f"   ✗ regions API 실패: {resp.status_code}")

    # 2. pois-bounding API 샘플 저장
    print("3. /api/v2/pois-bounding API 호출...")
    resp = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params={
            "level": 16,
            "startX": 127.0,
            "endX": 127.01,
            "startY": 37.5,
            "endY": 37.51,
            "types": "1",
        },
    )

    if resp.status_code == 200:
        save_json(fixtures_dir / "hogangnono_pois_sample.json", resp.json())
        print("   ✓ pois-bounding API 응답 저장")
    else:
        print(f"   ✗ pois-bounding API 실패: {resp.status_code}")

    print("\n✓ Fixtures 저장 완료")


def save_json(path: Path, data: dict) -> None:
    """JSON 파일 저장"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    record_fixtures()

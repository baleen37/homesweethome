#!/usr/bin/env python3
"""호갱노노 API에서 동 정보 추출하는 스크립트"""

import requests
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DongInfo:
    """동 정보 데이터 클래스"""

    code: str
    name: str
    full_name: str
    local_type: str
    local1_code: str
    local1_name: str
    local2_code: str
    local2_name: str
    local3_code: Optional[str] = None
    local3_name: Optional[str] = None
    lat: float = 0.0
    lng: float = 0.0

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "code": self.code,
            "name": self.name,
            "full_name": self.full_name,
            "local_type": self.local_type,
            "local1_code": self.local1_code,
            "local1_name": self.local1_name,
            "local2_code": self.local2_code,
            "local2_name": self.local2_name,
            "local3_code": self.local3_code,
            "local3_name": self.local3_name,
            "lat": self.lat,
            "lng": self.lng,
        }


class HogangnonoAPI:
    """호갱노노 API 클라이언트"""

    def __init__(self):
        self.base_url = "https://hogangnono.com/api/v2/searches/new"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": "https://hogangnono.com/",
            }
        )
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 최소 요청 간격 (초)

    def _make_request(self, params: Dict) -> Dict:
        """API 요청 (Rate limiting 적용)"""
        # Rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.json()
        except Exception as e:
            print(f"API 요청 실패: {e}")
            return {}

    def search_region(self, query: str, lat: float = None, lng: float = None) -> List[DongInfo]:
        """지역 검색하여 동 정보 추출"""
        params = {"query": query}
        if lat is not None:
            params["y"] = lat
        if lng is not None:
            params["x"] = lng

        print(f"검색: {query}")
        response = self._make_request(params)

        if not response or response.get("status") != "success":
            print(f"검색 실패: {query}")
            return []

        dongs = []
        matched = response.get("data", {}).get("matched", {})

        # region 정보 추출
        if "region" in matched:
            for item in matched["region"].get("list", []):
                dong = self._parse_region_item(item)
                if dong:
                    dongs.append(dong)

        return dongs

    def _parse_region_item(self, item: Dict) -> Optional[DongInfo]:
        """region 아이템 파싱"""
        try:
            return DongInfo(
                code=item.get("id", ""),
                name=item.get("local_name", ""),
                full_name=item.get("name", ""),
                local_type=item.get("local_type", ""),
                local1_code=item.get("local1_code", ""),
                local1_name=item.get("local1_name", ""),
                local2_code=item.get("local2_code", ""),
                local2_name=item.get("local2_name", ""),
                local3_code=item.get("local3_code"),
                local3_name=item.get("local3_name"),
                lat=item.get("location", {}).get("lat", 0),
                lng=item.get("location", {}).get("lon", 0),
            )
        except Exception as e:
            print(f"파싱 오류: {e}")
            return None

    def get_all_dongs_in_seoul(self) -> Dict[str, List[DongInfo]]:
        """서울시 모든 구/군 및 동 정보 수집"""
        seoul_districts = [
            ("강남구", 37.517305, 127.047502),
            ("강동구", 37.5499, 127.1470),
            ("강북구", 37.6395, 127.0258),
            ("강서구", 37.5510, 126.8495),
            ("관악구", 37.4785, 126.9516),
            ("광진구", 37.5385, 127.0823),
            ("구로구", 37.4955, 126.8874),
            ("금천구", 37.4568, 126.8955),
            ("노원구", 37.6542, 127.0568),
            ("도봉구", 37.6687, 127.0474),
            ("동대문구", 37.5744, 127.0396),
            ("동작구", 37.5124, 126.9395),
            ("마포구", 37.5663, 126.9013),
            ("서대문구", 37.5793, 126.9367),
            ("서초구", 37.483735, 127.005732),
            ("성동구", 37.5634, 127.0369),
            ("성북구", 37.5894, 127.0167),
            ("송파구", 37.5145, 127.1059),
            ("양천구", 37.5169, 126.8665),
            ("영등포구", 37.5264, 126.8964),
            ("용산구", 37.5325, 126.9908),
            ("은평구", 37.6173, 126.9227),
            ("종로구", 37.5701, 126.9808),
            ("중구", 37.5638, 126.9980),
            ("중랑구", 37.5945, 127.0938),
        ]

        result = {}

        for district_name, lat, lng in seoul_districts:
            print(f"\n{district_name} 정보 수집 중...")
            dongs = self.search_region(district_name, lat, lng)

            # 구/군 정보와 동 정보 분리
            gu_info = [d for d in dongs if d.local_type == "local2"]
            dong_info = [d for d in dongs if d.local_type == "local3"]

            result[district_name] = {"gu": gu_info, "dongs": dong_info}

            print(f"  - 구 정보: {len(gu_info)}개")
            print(f"  - 동 정보: {len(dong_info)}개")

        return result

    def save_to_files(self, data: Dict[str, List[DongInfo]], output_dir: Path = Path(".")):
        """수집된 데이터를 파일로 저장"""
        timestamp = int(time.time())

        # JSON 형식으로 저장
        json_data = {}
        for district, info in data.items():
            json_data[district] = {
                "gu": [d.to_dict() for d in info["gu"]],
                "dongs": [d.to_dict() for d in info["dongs"]],
            }

        json_file = output_dir / f"seoul_dongs_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON 저장 완료: {json_file}")

        # CSV 형식으로 동 정보만 저장
        csv_file = output_dir / f"seoul_dongs_{timestamp}.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            # 헤더
            f.write("구,동,동코드,법정동코드,위도,경도\n")

            # 데이터
            for district, info in data.items():
                for dong in info["dongs"]:
                    f.write(f"{district},{dong.name},{dong.code},{dong.local3_code},")
                    f.write(f"{dong.lat},{dong.lng}\n")
        print(f"✅ CSV 저장 완료: {csv_file}")

        # 코드 매핑 파일
        code_file = output_dir / f"seoul_code_mapping_{timestamp}.json"
        code_mapping = {}
        for district, info in data.items():
            if info["gu"]:
                gu = info["gu"][0]
                code_mapping[district] = {
                    "gu_code": gu.local2_code,
                    "dongs": {dong.name: dong.local3_code for dong in info["dongs"]},
                }

        with open(code_file, "w", encoding="utf-8") as f:
            json.dump(code_mapping, f, ensure_ascii=False, indent=2)
        print(f"✅ 코드 매핑 저장 완료: {code_file}")


def main():
    """메인 실행 함수"""
    print("호갱노노 동 정보 추출기")
    print("=" * 50)

    api = HogangnonoAPI()

    # 테스트: 강남구와 서초구만
    print("\n강남구 동 정보 테스트...")
    gangnam_dongs = api.search_region("강남구", 37.517305, 127.047502)

    print("\n서초구 동 정보 테스트...")
    seocho_dongs = api.search_region("서초구", 37.483735, 127.005732)

    # 결과 확인
    print("\n\n=== 강남구 분석 결과 ===")
    for dong in gangnam_dongs:
        print(f"- {dong.full_name} (코드: {dong.code})")
        print(f"  타입: {dong.local_type}, 지역코드: {dong.local2_code}")
        if dong.local_type == "local3":
            print(f"  동코드: {dong.local3_code}")

    print("\n=== 서초구 분석 결과 ===")
    for dong in seocho_dongs:
        print(f"- {dong.full_name} (코드: {dong.code})")
        print(f"  타입: {dong.local_type}, 지역코드: {dong.local2_code}")
        if dong.local_type == "local3":
            print(f"  동코드: {dong.local3_code}")

    # 전체 서울시 수집 (주석 처리 - 필요 시 해제)
    # print("\n\n전체 서울시 구/군 및 동 정보 수집 시작...")
    # all_dongs = api.get_all_dongs_in_seoul()
    # api.save_to_files(all_dongs)

    print("\n✅ 작업 완료")


if __name__ == "__main__":
    main()

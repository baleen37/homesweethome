#!/usr/bin/env python3
"""호갱노노 API 가이드 문서 검증을 위한 테스트 스크립트"""

import requests
import json
from typing import Dict, Any


class HogangnonoAPIValidator:
    """호갱노노 API 문서 검증기"""

    def __init__(self):
        self.base_url = "https://hogangnono.com"
        self.session = requests.Session()

        # 세션 초기화
        self._init_session()

    def _init_session(self):
        """세션 초기화 및 쿠키 획득"""
        try:
            response = self.session.get(self.base_url)
            print(f"✓ 세션 초기화 성공 (Status: {response.status_code})")
        except Exception as e:
            print(f"✗ 세션 초기화 실패: {e}")

    def validate_endpoint(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """API 엔드포인트 검증"""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {"X-Requested-With": "XMLHttpRequest"}

            response = self.session.get(url, params=params, headers=headers, timeout=10)

            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "content_type": response.headers.get("content-type", ""),
                "response_data": None,
                "error": None,
            }

            if response.status_code == 200:
                try:
                    data = response.json()
                    result["response_data"] = data

                    # 응답 구조 분석
                    if isinstance(data, dict):
                        result["data_keys"] = list(data.keys())
                        if "data" in data:
                            result["has_data_field"] = True
                            result["data_type"] = type(data["data"]).__name__

                except json.JSONDecodeError:
                    result["error"] = "JSON 파싱 실패"
                    result["response_data"] = response.text[:500]
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

            return result

        except Exception as e:
            return {"endpoint": endpoint, "success": False, "error": str(e)}

    def validate_regions_api(self) -> Dict[str, Any]:
        """지역 정보 API 검증"""
        print("\n=== 지역 정보 API 검증 ===")

        result = self.validate_endpoint("/api/v2/regions")

        if result["success"] and result["response_data"]:
            data = result["response_data"]

            # 문서와의 응답 구조 비교
            if "data" in data and "regionList" in data["data"]:
                regions = data["data"]["regionList"]

                # 서울 찾기
                seoul = next((r for r in regions if r.get("regionCode") == "11"), None)
                if seoul:
                    print(f"✓ 서울특별시 찾음: {seoul.get('name')}")

                    # 구 개수 확인
                    children = seoul.get("children", [])
                    print(f"✓ 서울 구 개수: {len(children)}개")

                    # 구 코드 목록
                    district_codes = []
                    for child in children:
                        district_codes.append(
                            {"code": child.get("regionCode"), "name": child.get("name")}
                        )

                    print("✓ 서울 구 코드 목록:")
                    for district in district_codes:
                        print(f"  {district['code']}: {district['name']}")

                    result["seoul_data"] = {
                        "found": True,
                        "name": seoul.get("name"),
                        "district_count": len(children),
                        "districts": district_codes,
                    }
                else:
                    print("✗ 서울 데이터 찾지 못함")
                    result["seoul_data"] = {"found": False}
            else:
                print("✗ 예상과 다른 응답 구조")
                print(f"실제 응답 키: {result.get('data_keys', [])}")

        return result

    def validate_pois_bounding_api(self) -> Dict[str, Any]:
        """POI 바운딩 API 검증"""
        print("\n=== POI 바운딩 API 검증 ===")

        # 문서의 파라미터 예시
        test_params = {
            "level": "16",
            "startX": 126.734086,
            "endX": 127.183394,
            "startY": 37.413294,
            "endY": 37.715133,
            "aptType": 0,
            "tradeType": 0,
            "screenWidth": 1200,
            "screenHeight": 924,
            "map": "google",
        }

        result = self.validate_endpoint("/api/v2/pois-bounding", test_params)

        if result["success"] and result["response_data"]:
            data = result["response_data"]

            if isinstance(data, list):
                poi_count = len(data)
                print(f"✓ POI 개수: {poi_count}")

                if poi_count > 0:
                    sample_poi = data[0]
                    print(f"✓ 첫번째 POI 키: {list(sample_poi.keys())}")

                    # 문서와의 필드 비교
                    expected_fields = ["id", "name", "lat", "lng", "category", "address", "aptId"]
                    missing_fields = []
                    for field in expected_fields:
                        if field not in sample_poi:
                            missing_fields.append(field)

                    if missing_fields:
                        print(f"⚠ 누락된 필드: {missing_fields}")

                    result["poi_analysis"] = {
                        "count": poi_count,
                        "sample_keys": list(sample_poi.keys()),
                        "missing_fields": missing_fields,
                    }

                # 600개 제한 확인
                if poi_count == 600:
                    print("⚠ 600개 제한에 걸림")
                    result["has_600_limit"] = True
                else:
                    result["has_600_limit"] = False

        return result

    def validate_apartment_transactions_api(self) -> Dict[str, Any]:
        """아파트 실거래 내역 API 검증"""
        print("\n=== 아파트 실거래 내역 API 검증 ===")

        # 테스트용 aptId (문서 예시)
        test_apt_id = "1Hq6f"

        # 최근 3년 데이터
        result1 = self.validate_endpoint(
            f"/api/v2/apts/{test_apt_id}/monthly-reports", {"tradeType": 0, "areaNo": 0}
        )

        print("\n--- 최근 3년 데이터 ---")
        if result1["success"] and result1["response_data"]:
            data = result1["response_data"]

            if isinstance(data, dict):
                if "shortTermReport" in data:
                    reports = data["shortTermReport"]
                    print(f"✓ 월간 보고서 개수: {len(reports)}")

                    if reports:
                        print(f"✓ 첫번째 보고서 키: {list(reports[0].keys())}")

                        # 거래 데이터 구조 확인
                        if "trades" in reports[0]:
                            trades = reports[0]["trades"]
                            if trades:
                                print(f"✓ 거래 데이터 샘플: {trades[0]}")

                        result1["analysis"] = {
                            "report_count": len(reports),
                            "sample_keys": list(reports[0].keys()),
                            "has_trades": bool(reports[0].get("trades")),
                        }

        # 전체 기간 데이터
        result2 = self.validate_endpoint(
            f"/api/v2/apts/{test_apt_id}/monthly-reports/more", {"tradeType": 0, "areaNo": 0}
        )

        print("\n--- 전체 기간 데이터 ---")
        print(f"상태 코드: {result2['status_code']}")

        return {"recent_data": result1, "full_period": result2}

    def validate_search_params(self) -> Dict[str, Any]:
        """SearchParams 클래스 검증"""
        print("\n=== SearchParams 클래스 검증 ===")

        # 문서의 예시 코드 테스트
        try:
            from src.crawler.api.hogangnono_client import SearchParams

            # 문서 예시대로 파라미터 생성
            search_params = SearchParams(
                bbox=(126.734086, 37.413294, 127.183394, 37.715133),
                level=14,
                tradeType=0,
                aptType=0,
            )

            # 딕셔너리 변환 확인
            params_dict = search_params.to_dict()

            print("✓ SearchParams 생성 성공")
            print(f"✓ 변환된 파라미터: {json.dumps(params_dict, indent=2, ensure_ascii=False)}")

            # 필수 파라미터 확인
            required_params = ["startX", "endX", "startY", "endY", "level"]
            missing_params = []
            for param in required_params:
                if param not in params_dict:
                    missing_params.append(param)

            if missing_params:
                print(f"⚠ 누락된 파라미터: {missing_params}")

            return {"success": True, "params": params_dict, "missing_params": missing_params}

        except Exception as e:
            print(f"✗ SearchParams 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    def run_validation(self):
        """전체 검증 실행"""
        print("=" * 60)
        print("호갱노노 API 가이드 문서 검증")
        print("=" * 60)

        results = {
            "regions": self.validate_regions_api(),
            "pois_bounding": self.validate_pois_bounding_api(),
            "apartment_transactions": self.validate_apartment_transactions_api(),
            "search_params": self.validate_search_params(),
        }

        # 요약
        print("\n" + "=" * 60)
        print("검증 결과 요약")
        print("=" * 60)

        for key, result in results.items():
            status = "✓ 성공" if result.get("success", False) else "✗ 실패"
            print(f"{key}: {status}")

        # 저장
        with open("api_validation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("\n✓ 검증 결과를 api_validation_results.json에 저장했습니다.")


if __name__ == "__main__":
    validator = HogangnonoAPIValidator()
    validator.run_validation()

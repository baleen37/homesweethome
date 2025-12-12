#!/usr/bin/env python
"""웹사이트 API 패턴 분석

호갱노노 웹사이트의 자바스크립트 소스 코드를 분석하여
실제 사용되는 API 호출 패턴을 파악합니다.
"""

import re
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import requests
from urllib.parse import urljoin


class WebAPIPatternAnalyzer:
    """웹 API 패턴 분석기"""

    def __init__(self):
        """초기화"""
        self.base_url = "https://hogangnono.com"
        self.results_dir = Path("output/web_analysis")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 발견된 API 패턴
        self.api_patterns = {
            "endpoints": set(),
            "params": {},
            "headers": {},
            "methods": set(),
        }

    def analyze_main_page(self) -> Dict[str, Any]:
        """메인 페이지 분석"""
        print("메인 페이지 분석 중...")

        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()

            # HTML에서 API 관련 정보 추출
            html_content = response.text

            # 1. JavaScript 파일 찾기
            js_files = self.extract_js_files(html_content)
            print(f"발견된 JS 파일: {len(js_files)}개")

            # 2. 각 JS 파일 분석
            for js_file in js_files[:10]:  # 처음 10개만 분석
                print(f"분석 중: {js_file}")
                self.analyze_js_file(js_file)
                time.sleep(1.0)

            # 3. HTML에서 직접 API 패턴 찾기
            self.find_api_patterns_in_html(html_content)

            return {
                "status": "success",
                "js_files_found": len(js_files),
                "api_patterns": self.get_api_patterns_summary(),
            }

        except Exception as e:
            print(f"오류: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }

    def extract_js_files(self, html_content: str) -> List[str]:
        """HTML에서 JavaScript 파일 경로 추출"""
        js_patterns = [
            r'<script[^>]+src="([^"]+\.js[^"]*)"',
            r"<script[^>]+src=\'([^\']+\.js[^\']*)\'",
        ]

        js_files = set()
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # URL 정규화
                if match.startswith("http"):
                    js_files.add(match)
                elif match.startswith("//"):
                    js_files.add(f"https:{match}")
                else:
                    js_files.add(urljoin(self.base_url, match))

        return list(js_files)

    def analyze_js_file(self, js_url: str):
        """JavaScript 파일 분석"""
        try:
            response = requests.get(js_url, timeout=10)
            response.raise_for_status()

            js_content = response.text

            # 1. API 엔드포인트 찾기
            self.find_endpoints_in_js(js_content)

            # 2. API 파라미터 찾기
            self.find_params_in_js(js_content)

            # 3. API 헤더 찾기
            self.find_headers_in_js(js_content)

            # 4. 특정 API 패턴 찾기
            self.find_specific_patterns(js_content)

        except Exception as e:
            print(f"  - 분석 실패: {str(e)}")

    def find_endpoints_in_js(self, js_content: str):
        """JavaScript에서 API 엔드포인트 찾기"""
        # 다양한 API 호출 패턴
        endpoint_patterns = [
            r'"(/api/[^"]+)"',
            r"'(/api/[^']+)'",
            r'endpoint:\s*["\']([^"\']+)["\']',
            r'url:\s*["\']([^"\']*api[^"\']*)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.get\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.post\s*\(\s*["\']([^"\']+)["\']',
            r'\.get\s*\(\s*["\']([^"\']*api[^"\']*)["\']',
            r'\.post\s*\(\s*["\']([^"\']*api[^"\']*)["\']',
        ]

        for pattern in endpoint_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for match in matches:
                if "/api/" in match.lower():
                    self.api_patterns["endpoints"].add(match)

    def find_params_in_js(self, js_content: str):
        """JavaScript에서 API 파라미터 패턴 찾기"""
        # 파라미터 관련 키워드
        param_keywords = [
            "aptType",
            "level",
            "tradeType",
            "category",
            "bbox",
            "bounds",
            "lat",
            "lng",
            "zoom",
        ]

        for keyword in param_keywords:
            # 파라미터 값 패턴
            patterns = [
                rf'{keyword}["\']?\s*:\s*["\']([^"\']+)["\']',
                rf'{keyword}["\']?\s*=\s*["\']([^"\']+)["\']',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, js_content, re.IGNORECASE)
                if matches and keyword not in self.api_patterns["params"]:
                    self.api_patterns["params"][keyword] = set()
                for match in matches:
                    self.api_patterns["params"][keyword].add(match)

    def find_headers_in_js(self, js_content: str):
        """JavaScript에서 API 헤더 패턴 찾기"""
        header_patterns = [
            r'X-Requested-With["\']?\s*:\s*["\']([^"\']+)["\']',
            r'Content-Type["\']?\s*:\s*["\']([^"\']+)["\']',
            r'Authorization["\']?\s*:\s*["\']([^"\']+)["\']',
            r'Referer["\']?\s*:\s*["\']([^"\']+)["\']',
        ]

        for pattern in header_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for match in matches:
                header_name = pattern.split('"')[0].strip()
                if header_name not in self.api_patterns["headers"]:
                    self.api_patterns["headers"][header_name] = set()
                self.api_patterns["headers"][header_name].add(match)

    def find_specific_patterns(self, js_content: str):
        """특정 API 패턴 찾기"""
        # 아파트 관련 패턴
        apartment_patterns = [
            r"apartments?[^a-zA-Z]",
            r"complex[^a-zA-Z]",
            r"danji[^a-zA-Z]",
            r"아파트",
            r"단지",
        ]

        # POI 관련 패턴
        poi_patterns = [
            r"poi[^a-zA-Z]",
            r"place[^a-zA-Z]",
            r"facility[^a-zA-Z]",
            r"지하철",
            r"병원",
            r"마트",
        ]

        all_patterns = apartment_patterns + poi_patterns
        found_patterns = []

        for pattern in all_patterns:
            if re.search(pattern, js_content, re.IGNORECASE):
                found_patterns.append(pattern)

        if found_patterns:
            if "patterns" not in self.api_patterns:
                self.api_patterns["patterns"] = set()
            self.api_patterns["patterns"].update(found_patterns)

    def find_api_patterns_in_html(self, html_content: str):
        """HTML에서 직접 API 패턴 찾기"""
        # data-* 속성에서 API 정보 찾기
        data_patterns = [
            r'data-api="([^"]+)"',
            r'data-endpoint="([^"]+)"',
            r'data-url="([^"]*)"',
        ]

        for pattern in data_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if "api" in match.lower():
                    self.api_patterns["endpoints"].add(match)

    def get_api_patterns_summary(self) -> Dict[str, Any]:
        """API 패턴 요약"""
        summary = {}

        # 엔드포인트 그룹화
        endpoint_groups = {}
        for endpoint in self.api_patterns["endpoints"]:
            parts = endpoint.split("/")
            if len(parts) > 2:
                group = "/".join(parts[:3])
                if group not in endpoint_groups:
                    endpoint_groups[group] = []
                endpoint_groups[group].append(endpoint)

        summary["endpoint_groups"] = {k: sorted(list(set(v))) for k, v in endpoint_groups.items()}
        summary["total_endpoints"] = len(self.api_patterns["endpoints"])

        # 파라미터 분석
        summary["params"] = {
            k: sorted(list(v)) if isinstance(v, set) else v
            for k, v in self.api_patterns["params"].items()
        }

        # 헤더 분석
        summary["headers"] = {
            k: sorted(list(v)) if isinstance(v, set) else v
            for k, v in self.api_patterns["headers"].items()
        }

        # 흥미로운 패턴
        if "patterns" in self.api_patterns:
            summary["interesting_patterns"] = sorted(list(self.api_patterns["patterns"]))

        return summary

    def analyze_network_traffic(self) -> Dict[str, Any]:
        """네트워크 트래픽 분석 (시뮬레이션)"""
        print("\n네트워크 트래픽 분석 시작...")

        # 실제 웹사이트에서 사용하는 API를 시뮬레이션
        test_endpoints = [
            "/api/v2/pois-bounding",
            "/api/v2/ranks/rolling",
            "/api/v2/maps/region",
            "/api/search/apartments",
        ]

        results = {}

        for endpoint in test_endpoints:
            try:
                # 다양한 파라미터 조합으로 테스트
                test_cases = [
                    {"lat": 37.5172, "lng": 127.0473, "aptType": 1, "level": 14},
                    {"lat": 37.5172, "lng": 127.0473, "aptType": 0, "level": 14},
                    {"lat": 37.5172, "lng": 127.0473, "aptType": 1, "level": 15},
                    {"lat": 37.5172, "lng": 127.0473, "category": 1},
                ]

                endpoint_results = []
                for params in test_cases:
                    url = urljoin(self.base_url, endpoint)

                    # 테스트 요청
                    response = requests.get(url, params=params, timeout=5)

                    endpoint_results.append(
                        {
                            "params": params,
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type", ""),
                            "has_data": bool(response.content),
                        }
                    )

                    time.sleep(1.0)

                results[endpoint] = endpoint_results

            except Exception as e:
                results[endpoint] = [{"error": str(e)}]

        return results

    def generate_recommendations(self) -> List[str]:
        """분석 결과 기반 권장사항 생성"""
        recommendations = []

        endpoints = self.api_patterns.get("endpoints", set())
        params = self.api_patterns.get("params", {})

        # 1. 엔드포인트 기반 권장사항
        if "/api/apt/" in str(endpoints):
            recommendations.append("아파트 전용 엔드포인트 발견: /api/apt/ 계열 확인 필요")
        elif "/api/search/apartments" in endpoints:
            recommendations.append(
                "아파트 검색 엔드포인트 발견: /api/search/apartments 테스트 필요"
            )
        else:
            recommendations.append("아파트 전용 엔드포인트 미발견 - POI 엔드포인트만 사용 가능")

        # 2. 파라미터 기반 권장사항
        if "aptType" in params:
            apt_types = params["aptType"]
            recommendations.append(f"aptType 값: {', '.join(apt_types)}")
        else:
            recommendations.append("aptType 파라미터 미발견 - 다른 방식으로 필터링")

        # 3. 패턴 기반 권장사항
        if "patterns" in self.api_patterns:
            patterns = self.api_patterns["patterns"]
            if any("아파트" in p for p in patterns):
                recommendations.append("코드에 아파트 관련 패턴 발견 - 더 깊은 분석 필요")

        # 4. 일반 권장사항
        recommendations.extend(
            [
                "쿠키 및 세션 관리 확인 필요",
                "동적 파라미터 생성 가능성 확인",
                "웹소켓 또는 기타 실시간 통신 확인",
            ]
        )

        return recommendations

    def save_results(self, results: Dict[str, Any]):
        """분석 결과 저장"""
        report = {
            "analysis_time": datetime.now().isoformat(),
            "base_url": self.base_url,
            "api_patterns": self.get_api_patterns_summary(),
            "main_page_analysis": results,
            "recommendations": self.generate_recommendations(),
        }

        # 네트워크 트래픽 분석 추가
        if "network_analysis" in results:
            report["network_analysis"] = results["network_analysis"]

        # 결과 저장
        results_file = self.results_dir / "web_api_analysis.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 요약 출력
        print(f"\n{'=' * 60}")
        print("웹 API 분석 결과 요약")
        print("=" * 60)
        print(f"발견된 엔드포인트: {report['api_patterns']['total_endpoints']}개")
        print(f"발견된 파라미터: {len(report['api_patterns']['params'])}개")

        if "endpoint_groups" in report["api_patterns"]:
            print("\n주요 엔드포인트 그룹:")
            for group, endpoints in report["api_patterns"]["endpoint_groups"].items():
                print(f"  - {group}: {len(endpoints)}개")

        print("\n권장사항:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

        print(f"\n상세 결과: {results_file}")


def main():
    """메인 실행"""
    analyzer = WebAPIPatternAnalyzer()

    print("호갱노노 웹사이트 API 패턴 분석 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 메인 페이지 분석
    main_page_result = analyzer.analyze_main_page()

    # 2. 네트워크 트래픽 분석 (선택적)
    print("\n\n네트워크 트래픽 분석...")
    try:
        network_result = analyzer.analyze_network_traffic()
        main_page_result["network_analysis"] = network_result
    except Exception as e:
        print(f"네트워크 분석 실패: {str(e)}")

    # 3. 결과 저장
    analyzer.save_results(main_page_result)


if __name__ == "__main__":
    main()

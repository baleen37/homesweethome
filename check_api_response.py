#!/usr/bin/env python3
"""호갱노노 API 응답 상세 확인"""

import json
import sys

sys.path.append("/Users/baleen/dev/homesweethome/src")

from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams


def main():
    config = CrawlerConfig.from_env()

    with HogangnonoAPIClient(config) as client:
        # 역삼동 bbox
        yesan_bbox = (127.035, 37.500, 127.055, 37.520)

        search_params = SearchParams(
            bbox=yesan_bbox,
            level=17,  # 높은 줌 레벨
            tradeType=0,  # 매매
            aptType=0,  # 아파트
        )

        response = client.get_apartments_bounding(search_params)

        print(f"Response success: {response.success}")
        print(f"Status code: {response.status_code}")

        if response.success:
            print(f"Response data type: {type(response.data)}")

            # 전체 응답 데이터 출력
            print("\n=== Full Response Data ===")
            print(json.dumps(response.data, indent=2, ensure_ascii=False))

            # data 필드 확인
            if isinstance(response.data, dict):
                print("\n=== Response Keys ===")
                for key in response.data.keys():
                    print(f"- {key}: {type(response.data[key])}")

            # 첫 번째 아파트 데이터 분석
            apartments = []
            if isinstance(response.data, list):
                apartments = response.data
            elif isinstance(response.data, dict) and "data" in response.data:
                apartments = response.data["data"]

            if apartments:
                print("\n=== First Apartment Details ===")
                print(json.dumps(apartments[0], indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.error}")


if __name__ == "__main__":
    main()

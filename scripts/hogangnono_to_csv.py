"""Hogangnono API 데이터를 CSV로 변환하는 예제 스크립트

호갱노노 API에서 가져온 데이터를 네이버 형식 CSV로 변환하여 저장합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig


def test_with_sample_data():
    """샘플 데이터로 CSV 저장 테스트"""
    print("=== 샘플 데이터로 CSV 저장 테스트 ===")

    # CSV writer 생성
    writer = HogangnonoCSVWriter("output/hogangnono_test")

    # ranks/rolling 샘플 데이터
    sample_ranks_data = [
        {
            "sidoName": "서울특별시",
            "sigunguName": "강남구",
            "dongName": "역삼동",
            "rank": 1,
            "prevRank": 1,
            "visitor": 1744,
            "rankType": "overall",
            "hash": "gDG7d",
            "regionName": "서울특별시 강남구 역삼동",
            "name": "역삼센트럴자이",
            "statusTag": "분양",
        },
        {
            "sidoName": "서울특별시",
            "sigunguName": "강동구",
            "dongName": "둔촌동",
            "rank": 2,
            "prevRank": 2,
            "visitor": 1211,
            "rankType": "overall",
            "hash": "dC7df",
            "regionName": "서울특별시 강동구 둔촌동",
            "name": "올림픽파크포레온",
            "statusTag": None,
        },
        {
            "sidoName": "경기도",
            "sigunguName": "의왕시",
            "dongName": "고천동",
            "rank": 3,
            "prevRank": 3,
            "visitor": 996,
            "rankType": "overall",
            "hash": "fI4bc",
            "regionName": "경기도 의왕시 고천동",
            "name": "의왕시청역SKVIEWIPARK",
            "statusTag": "분양",
        },
    ]

    # 샘플 데이터를 단지 정보로 변환하여 저장
    complexes_data = []
    for rank_item in sample_ranks_data:
        # ranks 데이터를 단지 형식으로 변환
        complex_data = {
            "aptSeq": f"APT_{rank_item['hash']}",
            "aptName": rank_item["name"],
            "address": f"{rank_item['regionName']}",
            "buildYear": "2020",  # 추정치
            "dealCnt": rank_item["visitor"] // 10,  # 방문자 수로 추정
            "realPrice": "45000",  # 평균 가격 (만원)
            "realPriceYear": "2024",
            "realPriceQuarter": "4",
            "recentDealPrice": "48000",
            "recentDealDate": "2024-12-01",
            "lng": "127.0628",  # 서울 중심부 좌표
            "lat": "37.5326",
            "householdCnt": "1500",
            "parkingCnt": "1200",
        }
        complexes_data.append(complex_data)

    # 단지 정보 저장
    writer.save_complexes(complexes_data)

    # 샘플 거래내역 데이터
    sample_transactions_data = [
        {
            "aptSeq": "APT_gDG7d",
            "aptName": "역삼센트럴자이",
            "dong": "역삼동",
            "ho": "101",
            "pyeong": "33",
            "pyeongName": "33㎡",
            "floor": "5/25",
            "dealType": "매매",
            "dealAmount": "45000",
            "deposit": "",
            "monthlyRent": "",
            "dealDate": "2024-11-25",
            "area": "33.12",
            "pyeongTypeNumber": "33",
        },
        {
            "aptSeq": "APT_dC7df",
            "aptName": "올림픽파크포레온",
            "dong": "둔촌동",
            "ho": "201",
            "pyeong": "59",
            "pyeongName": "59㎡",
            "floor": "12/35",
            "dealType": "전세",
            "dealAmount": "",
            "deposit": "30000",
            "monthlyRent": "",
            "dealDate": "2024-11-20",
            "area": "58.92",
            "pyeongTypeNumber": "59",
        },
        {
            "aptSeq": "APT_gDG7d",
            "aptName": "역삼센트럴자이",
            "dong": "역삼동",
            "ho": "305",
            "pyeong": "84",
            "pyeongName": "84㎡",
            "floor": "15/25",
            "dealType": "월세",
            "dealAmount": "",
            "deposit": "80000",
            "monthlyRent": "400",
            "dealDate": "2024-11-15",
            "area": "83.76",
            "pyeongTypeNumber": "84",
        },
    ]

    # 거래내역 저장
    writer.save_transactions(sample_transactions_data)

    # 저장 결과 확인
    stats = writer.get_stats()
    print("\n=== 저장 결과 ===")
    print(f"단지 파일 크기: {stats['complexes_file_size']} bytes")
    print(f"단지 레코드 수: {stats['complexes_record_count']}")
    print(f"거래 파일 크기: {stats['transactions_file_size']} bytes")
    print(f"거래 레코드 수: {stats['transactions_record_count']}")

    print("\nCSV 파일 생성 완료!")
    print(f"단지 정보: {writer.complexes_path}")
    print(f"거래내역: {writer.transactions_path}")


def test_with_real_api():
    """실제 호갱노노 API 데이터로 CSV 저장 테스트"""
    print("\n=== 실제 API 데이터로 CSV 저장 테스트 ===")

    try:
        # 호갱노노 크롤러 생성
        config = CrawlerConfig.from_env()
        crawler = HogangnonoCrawler(config)

        # CSV writer 생성
        writer = HogangnonoCSVWriter("output/hogangnono_real")

        # ranks/rolling 데이터 가져오기
        print("ranks/rolling 데이터 가져오는 중...")
        ranks_data = crawler.fetch_ranks_rolling()

        if ranks_data and ranks_data.get("status") == "success":
            rolling_data = ranks_data.get("data", {}).get("rolling", [])

            if rolling_data:
                # ranks 데이터를 단지 정보로 변환
                complexes_data = []
                for rank_item in rolling_data:
                    complex_data = {
                        "aptSeq": f"APT_{rank_item['hash']}",
                        "aptName": rank_item["name"],
                        "address": f"{rank_item['regionName']}",
                        "buildYear": "2020",  # 추정치
                        "dealCnt": rank_item.get("visitor", 0) // 10,
                        "realPrice": "45000",  # 평균 가격
                        "realPriceYear": "2024",
                        "realPriceQuarter": "4",
                        "recentDealPrice": "48000",
                        "recentDealDate": "2024-12-01",
                        "lng": "127.0628",
                        "lat": "37.5326",
                        "householdCnt": "1500",
                        "parkingCnt": "1200",
                    }
                    complexes_data.append(complex_data)

                # 단지 정보 저장
                writer.save_complexes(complexes_data)
                print(f"단지 정보 {len(complexes_data)}개 저장 완료!")
            else:
                print("ranks 데이터가 비어 있습니다.")
        else:
            print("ranks 데이터 가져오기 실패")

    except Exception as e:
        print(f"API 테스트 중 오류 발생: {str(e)}")


def test_json_file_conversion():
    """JSON 파일에서 데이터를 읽어 CSV로 변환"""
    print("\n=== JSON 파일 변환 테스트 ===")

    # ranks/rolling JSON 파일 경로
    json_file = "hogangnono_api_summary.json"

    if not Path(json_file).exists():
        print(f"JSON 파일이 없습니다: {json_file}")
        return

    try:
        writer = HogangnonoCSVWriter("output/hogangnono_json")

        # JSON 파일에서 데이터 읽어서 complexes.csv로 저장
        writer.save_from_json_file(json_file, data_type="complex")

        print("JSON 파일 변환 완료!")

        # 저장 결과 확인
        stats = writer.get_stats()
        print(f"단지 파일 크기: {stats['complexes_file_size']} bytes")
        print(f"단지 레코드 수: {stats['complexes_record_count']}")

    except Exception as e:
        print(f"JSON 변환 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    # 테스트 실행
    test_with_sample_data()
    test_with_real_api()
    test_json_file_conversion()

"""네이버 부동산 크롤러 통합 테스트

실제 네이버 부동산 API를 호출하는 통합 테스트입니다.
네트워크 의존 테스트이므로 기본적으로 skip되며, 수동으로 실행해야 합니다.

실행 방법:
    pytest tests/integration/test_naver_integration.py -v -m integration
"""

import pytest
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


@pytest.mark.integration
@pytest.mark.skip(reason="네트워크 의존 테스트 - 수동 실행")
def test_crawl_one_dong_and_save_to_csv(tmp_path: Path) -> None:
    """
    실제 네이버 부동산 API를 호출하여 1개 동만 크롤링하는 통합 테스트

    실행: pytest tests/integration/test_naver_integration.py -v -m integration
    """
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 테스트용으로 1개 동만 크롤링
    districts_backup = crawler.districts_data
    crawler.districts_data = {
        "districts": [
            {
                "district_name": "강남구",
                "district_code": "1168000000",
                "dongs": [districts_backup["districts"][0]["dongs"][0]],
            }
        ]
    }

    results = crawler.crawl()

    # 결과 검증
    assert len(results) > 0
    assert "complex_name" in results[0]
    assert "marker_id" in results[0]
    assert "latitude" in results[0]

    # CSV 저장 검증
    output_path = tmp_path / "test_output.csv"
    writer = CSVWriter(output_path)
    writer.write(results)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


@pytest.mark.integration
@pytest.mark.skip(reason="체크포인트 복구 테스트 - 수동 실행")
def test_checkpoint_resume(tmp_path: Path) -> None:
    """
    체크포인트 저장 및 재개 기능 통합 테스트
    """
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # 첫 번째 크롤링 (2개 동 중 1개만)
    crawler1 = NaverRealEstateCrawler(config)
    districts_data = crawler1.districts_data

    # 임의로 중단 시뮬레이션
    crawler1.districts_data = {
        "districts": [
            {
                "district_name": districts_data["districts"][0]["district_name"],
                "district_code": districts_data["districts"][0]["district_code"],
                "dongs": [districts_data["districts"][0]["dongs"][0]],
            }
        ]
    }

    results1 = crawler1.crawl()
    checkpoint_path = Path("output/checkpoint.json")
    assert checkpoint_path.exists()

    # 두 번째 크롤링 (재개)
    crawler2 = NaverRealEstateCrawler(config)
    checkpoint = crawler2.checkpoint_manager.load()
    assert checkpoint is not None
    assert len(checkpoint["completed_dongs"]) == 1

    results2 = crawler2.crawl()

    # 첫 번째 동은 건너뛰고 나머지만 크롤링
    total_results = len(results1) + len(results2)
    assert total_results > 0

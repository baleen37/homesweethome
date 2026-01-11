"""아파트+실거래가 E2E 테스트 (실제 서울 데이터)"""

import pytest

from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade


@pytest.mark.e2e
def test_seoul_sample_apt_and_trade_e2e(tmp_path):
    """
    서울 샘플 동 코드에 대한 E2E 테스트
    """
    apt_path = tmp_path / "seoul_apt_list_e2e.csv"
    trade_path = tmp_path / "seoul_trade_price_e2e.csv"

    # 샘플 동 코드 (역삼1동, 삼성동 등)
    dong_codes = ["1150010100", "1150010200"]

    apt_count, trade_count = crawl_apt_and_trade(
        dong_codes=dong_codes,
        apt_output_path=apt_path,
        trade_output_path=trade_path,
        max_per_dong=5,
    )

    # 검증
    assert apt_count > 0
    assert apt_path.exists()

    apt_content = apt_path.read_text(encoding="utf-8")
    lines = apt_content.strip().split("\n")
    assert len(lines) >= 2

    print(f"E2E 결과: {apt_count}개 아파트, {trade_count}개 실거래가")
    print(f"  - 아파트: {apt_path}")
    print(f"  - 실거래가: {trade_path}")

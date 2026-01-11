"""아파트+실거래가 통합 테스트 (실제 API 사용)"""

import pytest

from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade


@pytest.mark.integration
def test_apt_and_trade_full_workflow(tmp_path):
    """
    전체 워크플로우 테스트:
    1. 아파트 목록 + 실거래가 크롤링
    2. 두 CSV 파일 생성
    3. 데이터 검증
    """
    apt_path = tmp_path / "apt_list.csv"
    trade_path = tmp_path / "trade_price.csv"

    apt_count, trade_count = crawl_apt_and_trade(
        dong_codes=["1150010100"],  # 역삼1동
        apt_output_path=apt_path,
        trade_output_path=trade_path,
        max_per_dong=3,  # 최대 3개만 테스트
    )

    # 검증
    assert apt_count > 0, "아파트 목록이 1개 이상이어야 함"
    assert apt_path.exists()
    assert trade_path.exists()

    # CSV 내용 검증
    apt_content = apt_path.read_text(encoding="utf-8")
    trade_content = trade_path.read_text(encoding="utf-8")

    apt_lines = apt_content.strip().split("\n")
    trade_lines = trade_content.strip().split("\n")

    # 헤더 + 데이터
    assert len(apt_lines) >= 2
    assert "seq" in apt_lines[0]

    # 실거래가는 없을 수도 있음
    if trade_count > 0:
        assert len(trade_lines) >= 2
        assert "apt_seq" in trade_lines[0]

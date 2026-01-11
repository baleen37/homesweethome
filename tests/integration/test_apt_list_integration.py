"""아파트 목록 크롤링 통합 테스트"""

import pytest

from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv


@pytest.mark.integration
def test_apt_list_full_workflow(tmp_path):
    """
    전체 워크플로우 테스트:
    1. 아파트 목록 크롤링
    2. CSV 내보내기
    3. 데이터 검증
    """
    apt_path = tmp_path / "apt_list.csv"

    apt_count = crawl_apt_list_to_csv(
        dong_codes=["1150010100"],  # 염창동
        output_path=apt_path,
    )

    # 검증
    assert apt_count > 0, "아파트 목록이 1개 이상이어야 함"
    assert apt_path.exists()

    # CSV 내용 검증
    apt_content = apt_path.read_text(encoding="utf-8")
    apt_lines = apt_content.strip().split("\n")

    # 헤더 + 데이터
    assert len(apt_lines) >= 2
    assert "seq" in apt_lines[0]
    assert "name" in apt_lines[0]

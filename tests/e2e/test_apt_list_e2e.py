"""아파트 목록 크롤링 E2E 테스트"""

import pytest

from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv


@pytest.mark.e2e
def test_seoul_sample_apt_list_e2e(tmp_path):
    """
    서울 샘플 동 코드에 대한 E2E 테스트
    """
    apt_path = tmp_path / "seoul_apt_list_e2e.csv"

    # 샘플 동 코드 (염창동, 등촌동)
    dong_codes = ["1150010100", "1150010200"]

    apt_count = crawl_apt_list_to_csv(
        dong_codes=dong_codes,
        output_path=apt_path,
    )

    # 검증
    assert apt_count > 0
    assert apt_path.exists()

    apt_content = apt_path.read_text(encoding="utf-8")
    lines = apt_content.strip().split("\n")
    assert len(lines) >= 2

    print(f"E2E 결과: {apt_count}개 아파트, 파일: {apt_path}")

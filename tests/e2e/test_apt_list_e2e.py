"""아파트 목록 크롤링 E2E 테스트"""

import pytest

from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv


@pytest.mark.e2e
def test_seoul_sample_apt_list_e2e(
    sample_dong_codes,
    apt_csv_path,
    verify_csv_file,
):
    """
    서울 샘플 동 코드에 대한 E2E 테스트

    검증:
    1. 아파트 데이터 수집 성공
    2. CSV 파일 생성 확인
    3. CSV 내용 검증
    """
    apt_count = crawl_apt_list_to_csv(
        dong_codes=sample_dong_codes,
        output_path=apt_csv_path,
    )

    # CSV 검증
    apt_records = verify_csv_file(
        apt_csv_path,
        min_lines=2,
        required_headers=["seq", "name"],
    )
    assert apt_count > 0, "아파트 데이터가 수집되지 않음"
    assert len(apt_records) == apt_count, (
        f"CSV 레코드 수와 반환된 수 불일치: {len(apt_records)} != {apt_count}"
    )

    print(f"E2E 결과: {apt_count}개 아파트, 파일: {apt_csv_path}")

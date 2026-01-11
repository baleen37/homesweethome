"""아파트+실거래가 E2E 테스트 (실제 서울 데이터)"""

import pytest

from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade


@pytest.mark.e2e
def test_seoul_sample_apt_and_trade_e2e(
    sample_dong_codes,
    apt_csv_path,
    trade_csv_path,
    verify_csv_file,
):
    """
    서울 샘플 동 코드에 대한 E2E 테스트

    검증:
    1. 아파트 데이터 수집 성공
    2. 실거래가 데이터 수집 성공
    3. CSV 파일 생성 확인
    4. CSV 내용 검증
    """
    apt_count, trade_count = crawl_apt_and_trade(
        dong_codes=sample_dong_codes,
        apt_output_path=apt_csv_path,
        trade_output_path=trade_csv_path,
        max_per_dong=5,
    )

    # 아파트 CSV 검증
    apt_records = verify_csv_file(
        apt_csv_path,
        min_lines=2,
        required_headers=["seq", "name"],
    )
    assert apt_count > 0, "아파트 데이터가 수집되지 않음"
    assert len(apt_records) == apt_count, (
        f"아파트 CSV 레코드 수와 반환된 수 불일치: {len(apt_records)} != {apt_count}"
    )

    # 실거래가 CSV 검증 (데이터가 있을 경우만)
    if trade_count > 0:
        trade_records = verify_csv_file(trade_csv_path, min_lines=2)
        assert len(trade_records) == trade_count, (
            f"실거래가 CSV 레코드 수와 반환된 수 불일치: {len(trade_records)} != {trade_count}"
        )
    else:
        # 실거래가 데이터가 없어도 파일은 생성되어야 함 (헤더만 있을 수 있음)
        assert trade_csv_path.exists(), "실거래가 CSV 파일이 생성되지 않음"

    print(f"E2E 결과: {apt_count}개 아파트, {trade_count}개 실거래가")
    print(f"  - 아파트: {apt_csv_path}")
    print(f"  - 실거래가: {trade_csv_path}")

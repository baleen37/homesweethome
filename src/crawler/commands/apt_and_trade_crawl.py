"""아파트 기본정보 + 실거래가 통합 크롤링"""

from pathlib import Path

from src.crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler
from src.crawler.export.csv_export import export_apt_list_to_csv, export_trade_price_to_csv


def crawl_apt_and_trade(
    dong_codes: list[str],
    apt_output_path: Path,
    trade_output_path: Path,
    area_m2: float = 84.0,
    sido_code: int = 11,
    max_per_dong: int = 10,
) -> tuple[int, int]:
    """
    아파트 기본정보와 실거래가를 각각 별도 CSV로 크롤링합니다.

    Args:
        dong_codes: 법정동 코드 리스트
        apt_output_path: 아파트 목록 출력 경로
        trade_output_path: 실거래가 출력 경로
        area_m2: 실거래가 조회 면적 (m²)
        sido_code: 시도 코드 (서울: 11)
        max_per_dong: 동별 최대 조회 수

    Returns:
        (아파트 수, 실거래가 수)
    """
    all_apts = []
    all_trades = []

    for dong_code in dong_codes:
        print(f"동 코드 {dong_code} 조회 중...")
        apt_crawler = AsilAptListCrawler(dong_code=dong_code)
        apt_list = apt_crawler.crawl()
        all_apts.extend(apt_list)

        for apt in apt_list[:max_per_dong]:
            print(f"  - {apt.name} 실거래가 조회 중...")
            trade_crawler = AsilTradePriceCrawler(
                apt_code=apt.seq,
                sido_code=sido_code,
                area_m2=area_m2,
            )
            trade_price = trade_crawler.crawl()

            # (apt_seq, trade_price) 튜플로 저장
            all_trades.append((apt.seq, trade_price))

    export_apt_list_to_csv(all_apts, apt_output_path)
    export_trade_price_to_csv(all_trades, trade_output_path)

    # 실거래가 레코드 수 계산
    trade_count = 0
    for _, trade_prices in all_trades:
        for trade_price in trade_prices:
            if trade_price.val:
                for month in trade_price.val:
                    if month.val:
                        for day in month.val:
                            if day.val:
                                trade_count += len(day.val)

    print(f"완료: {len(all_apts)}개 아파트, {trade_count}개 실거래가")
    print(f"  - 아파트 목록: {apt_output_path}")
    print(f"  - 실거래가: {trade_output_path}")

    return len(all_apts), trade_count

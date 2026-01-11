"""CSV 내보내기 단위 테스트"""

import tempfile
from pathlib import Path


def test_export_trade_price_to_csv():
    """실거래가 CSV 내보내기"""
    from src.crawler.dto.asil_trade_price import (
        AsilTradePriceDayDTO,
        AsilTradePriceDetailDTO,
        AsilTradePriceDTO,
        AsilTradePriceMonthDTO,
    )
    from src.crawler.export.csv_export import export_trade_price_to_csv

    data = [
        (
            "1",
            [
                AsilTradePriceDTO(
                    val=[
                        AsilTradePriceMonthDTO(
                            yyyymm="202401",
                            val=[
                                AsilTradePriceDayDTO(
                                    day=15,
                                    val=[
                                        AsilTradePriceDetailDTO(
                                            money="encrypted_100000",
                                            floor="5",
                                            type="1",
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "trade_price.csv"
        export_trade_price_to_csv(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 1줄
        assert len(lines) >= 2
        assert "apt_seq" in lines[0]


def test_export_apt_list_to_csv():
    """아파트 목록 CSV 내보내기"""
    from src.crawler.dto.asil_apt_list import AsilAptListDTO
    from src.crawler.export.csv_export import export_apt_list_to_csv

    data = [
        AsilAptListDTO(
            seq="1",
            name="테스트아파트",
            dong="1150010100",
            dongname="역삼동",
            build_year="2000",
            household="100",
            lat="37.5",
            lng="127.0",
        ),
        AsilAptListDTO(
            seq="2",
            name="무실거래아파트",
            dong="1150010200",
            dongname="삼성동",
            build_year="1995",
            household="50",
            lat="37.51",
            lng="127.01",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "apt_list.csv"
        export_apt_list_to_csv(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 2줄
        assert len(lines) == 3
        # 헤더 검증
        assert "seq" in lines[0]
        assert "name" in lines[0]

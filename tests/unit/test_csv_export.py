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


def test_export_apt_list_to_csv(sample_dto_factory):
    """아파트 목록 CSV 내보내기"""
    from src.crawler.export.csv_export import export_apt_list_to_csv

    data = [
        sample_dto_factory(
            seq="1",
            name="테스트아파트",
            dong="1150010100",
            dongname="역삼동",
        ),
        sample_dto_factory(
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


def test_export_matched_apts_to_csv():
    """ASIL-Naver 매칭 아파트 목록 CSV 내보내기"""
    from src.crawler.dto.asil_apt_list import AsilAptListDTO
    from src.crawler.export.csv_export import export_matched_apts_to_csv

    data = [
        AsilAptListDTO(
            seq="1",
            name="테스트아파트",
            dong="1150010100",
            dongname="역삼동",
            lat="37.5",
            lng="127.0",
        ),
        AsilAptListDTO(
            seq="2",
            name="매칭실패아파트",
            dong="1150010200",
            dongname="삼성동",
            lat="37.51",
            lng="127.01",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "matched_apts.csv"
        export_matched_apts_to_csv(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 2줄
        assert len(lines) == 3
        # 헤더 검증
        assert "seq" in lines[0]
        assert "name" in lines[0]
        assert "lat" in lines[0]
        assert "lng" in lines[0]


def test_export_naver_articles_with_apt_seq():
    """apt_seq 추가된 네이버 매물 CSV 내보내기"""
    from src.crawler.dto.naver_article import NaverArticleItemDTO
    from src.crawler.export.csv_export import export_naver_articles_with_apt_seq

    data = [
        NaverArticleItemDTO(
            atcl_no="1",
            cortar_no="1150010100",
            atcl_nm="테스트매물",
            atcl_stat_cd="01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
            prc=100000,
            flr_info="5층",
            spc1="80",
            spc2="60",
            direction="남향",
            atcl_fetr_desc="설명",
            bild_nm="101동",
            apt_seq="APT001",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "articles.csv"
        export_naver_articles_with_apt_seq(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 1줄
        assert len(lines) == 2
        # 헤더에 apt_seq 포함 확인
        assert "apt_seq" in lines[0]
        # 데이터에 apt_seq 포함 확인
        assert "APT001" in lines[1]

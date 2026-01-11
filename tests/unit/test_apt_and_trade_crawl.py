"""아파트+실거래가 통합 크롤링 단위 테스트"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

_APT_CRAWLER_PATH = "src.crawler.commands.apt_and_trade_crawl.AsilAptListCrawler"
_TRADE_CRAWLER_PATH = "src.crawler.commands.apt_and_trade_crawl.AsilTradePriceCrawler"


def test_crawl_apt_and_trade():
    """통합 크롤링 함수 테스트"""
    from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
    from src.crawler.dto.asil_apt_list import AsilAptListDTO
    from src.crawler.dto.asil_trade_price import (
        AsilTradePriceDayDTO,
        AsilTradePriceDetailDTO,
        AsilTradePriceDTO,
        AsilTradePriceMonthDTO,
    )

    # Mock 크롤러
    with (
        patch(_APT_CRAWLER_PATH) as mock_apt_crawler_cls,
        patch(_TRADE_CRAWLER_PATH) as mock_trade_crawler_cls,
    ):
        # Mock 설정
        mock_apt_crawler = Mock()
        mock_apt_crawler.crawl.return_value = [
            AsilAptListDTO(
                seq="1",
                name="테스트",
                dong="1150010100",
                dongname="역삼동",
                build_year="2000",
                household="100",
                lat="37.5",
                lng="127.0",
            )
        ]
        mock_apt_crawler_cls.return_value = mock_apt_crawler

        mock_trade_crawler = Mock()
        mock_trade_crawler.crawl.return_value = [
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
        ]
        mock_trade_crawler_cls.return_value = mock_trade_crawler

        with tempfile.TemporaryDirectory() as tmpdir:
            apt_path = Path(tmpdir) / "apt.csv"
            trade_path = Path(tmpdir) / "trade.csv"

            apt_count, trade_count = crawl_apt_and_trade(
                dong_codes=["1150010100"],
                apt_output_path=apt_path,
                trade_output_path=trade_path,
                max_per_dong=1,
            )

            assert apt_count == 1
            assert trade_count == 1
            assert apt_path.exists()
            assert trade_path.exists()

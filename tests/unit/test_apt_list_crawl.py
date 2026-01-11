"""아파트 목록 크롤링 단위 테스트"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


def test_crawl_apt_list_to_csv(sample_dto_factory):
    """아파트 목록 크롤링 함수 테스트"""
    from src.crawler.commands.apt_list_crawl import crawl_apt_list_to_csv

    # Mock 크롤러
    with patch("src.crawler.commands.apt_list_crawl.AsilAptListCrawler") as MockAptCrawler:
        # Mock 설정
        mock_apt_crawler = Mock()
        mock_apt_crawler.crawl.return_value = [
            sample_dto_factory(
                seq="1",
                name="테스트",
                dongname="역삼동",
            )
        ]
        MockAptCrawler.return_value = mock_apt_crawler

        with tempfile.TemporaryDirectory() as tmpdir:
            apt_path = Path(tmpdir) / "apt.csv"

            apt_count = crawl_apt_list_to_csv(
                dong_codes=["1150010100"],
                output_path=apt_path,
            )

            assert apt_count == 1
            assert apt_path.exists()

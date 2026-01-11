"""아파트 CLI 공통 유틸리티 테스트"""

from unittest.mock import patch

from crawler.commands.apt_cli import parse_args as apt_cli_parse_args
from crawler.commands.apt_trade_cli import parse_args as apt_trade_parse_args


class TestAptCliParseArgs:
    """apt_cli.py parse_args 함수 테스트"""

    def test_dong_code_단일_파싱(self):
        """단일 dong-code 파싱"""
        with patch("sys.argv", ["apt_cli", "--dong-code", "1150010100"]):
            args = apt_cli_parse_args()
            assert args.dong_code == ["1150010100"]

    def test_dong_code_여러_개_파싱(self):
        """여러 dong-code 파싱"""
        argv = ["apt_cli", "--dong-code", "1150010100", "--dong-code", "1150010200"]
        with patch("sys.argv", argv):
            args = apt_cli_parse_args()
            assert args.dong_code == ["1150010100", "1150010200"]

    def test_all_플래그_파싱(self):
        """--all 플래그 파싱"""
        with patch("sys.argv", ["apt_cli", "--all"]):
            args = apt_cli_parse_args()
            assert args.all is True

    def test_output_기본값(self):
        """output 기본값 확인"""
        with patch("sys.argv", ["apt_cli"]):
            args = apt_cli_parse_args()
            assert args.output == "output/apt_list.csv"

    def test_output_커스텀값(self):
        """output 커스텀값 파싱"""
        with patch("sys.argv", ["apt_cli", "--output", "custom/test.csv"]):
            args = apt_cli_parse_args()
            assert args.output == "custom/test.csv"


class TestAptTradeCliParseArgs:
    """apt_trade_cli.py parse_args 함수 테스트"""

    def test_dong_code_단일_파싱(self):
        """단일 dong-code 파싱"""
        with patch("sys.argv", ["apt_trade_cli", "--dong-code", "1150010100"]):
            args = apt_trade_parse_args()
            assert args.dong_code == ["1150010100"]

    def test_dong_code_여러_개_파싱(self):
        """여러 dong-code 파싱"""
        argv = ["apt_trade_cli", "--dong-code", "1150010100", "--dong-code", "1150010200"]
        with patch("sys.argv", argv):
            args = apt_trade_parse_args()
            assert args.dong_code == ["1150010100", "1150010200"]

    def test_output_기본값(self):
        """output 기본값 확인"""
        with patch("sys.argv", ["apt_trade_cli"]):
            args = apt_trade_parse_args()
            assert args.output == "output"

    def test_output_커스텀값(self):
        """output 커스텀값 파싱"""
        with patch("sys.argv", ["apt_trade_cli", "--output", "custom"]):
            args = apt_trade_parse_args()
            assert args.output == "custom"

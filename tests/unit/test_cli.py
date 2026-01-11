"""CLI 모듈 유닛 테스트

비대화형 CLI 모드를 위한 테스트입니다.
"""

from unittest.mock import patch

import pytest

from crawler.commands.cli import (
    build_config_from_args,
    parse_args,
    parse_selection,
    select_gu_from_args,
)


class TestParseSelection:
    """parse_selection 함수 테스트"""

    def test_parse_single_number(self):
        """단일 숫자 파싱"""
        result = parse_selection("5", 10)
        assert result == [5]

    def test_parse_multiple_numbers_comma(self):
        """콤마로 구분된 여러 숫자 파싱"""
        result = parse_selection("1,3,5", 10)
        assert result == [1, 3, 5]

    def test_parse_range(self):
        """범위 파싱 (1-5)"""
        result = parse_selection("1-5", 10)
        assert result == [1, 2, 3, 4, 5]

    def test_parse_mixed(self):
        """혼합 파싱 (1,3,5-7)"""
        result = parse_selection("1,3,5-7", 10)
        assert result == [1, 3, 5, 6, 7]

    def test_parse_deduplication(self):
        """중복 제거"""
        result = parse_selection("1,1,2,2", 10)
        assert result == [1, 2]

    def test_parse_sorting(self):
        """정렬"""
        result = parse_selection("5,1,3", 10)
        assert result == [1, 3, 5]

    def test_parse_out_of_range_filter(self):
        """범위를 벗어난 값 필터링"""
        result = parse_selection("1,5,15", 10)
        assert result == [1, 5]

    def test_parse_zero_filtered(self):
        """0은 필터링됨"""
        result = parse_selection("0,1,2", 10)
        assert result == [1, 2]


class TestParseArgs:
    """parse_args 함수 테스트"""

    def test_parse_no_args_defaults_to_interactive(self, capsys):
        """인자가 없으면 대화형 모드로 설정"""
        with patch("sys.argv", ["cli"]):
            args = parse_args()
            assert args.interactive is True

    def test_parse_gu_code(self):
        """--gu-code 인자 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            assert args.gu_code == ["11560"]
            assert args.interactive is False

    def test_parse_multiple_gu_codes(self):
        """여러 --gu-code 인자 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--gu-code", "11680"]):
            args = parse_args()
            assert args.gu_code == ["11560", "11680"]

    def test_parse_all_flag(self):
        """--all 플래그 파싱"""
        with patch("sys.argv", ["cli", "--all"]):
            args = parse_args()
            assert args.all is True
            assert args.interactive is False

    def test_parse_min_household(self):
        """--min-household 인자 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--min-household", "100"]):
            args = parse_args()
            assert args.min_household == 100

    def test_parse_min_household_default(self):
        """--min-household 기본값"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            assert args.min_household is None

    def test_parse_output(self):
        """--output 인자 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--output", "output/test.csv"]):
            args = parse_args()
            assert args.output == "output/test.csv"

    def test_parse_output_default(self):
        """--output 기본값"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            assert args.output is None

    def test_parse_require_valid_coords(self):
        """--require-valid-coords 플래그 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--require-valid-coords"]):
            args = parse_args()
            assert args.require_valid_coords is True

    def test_parse_require_valid_coords_default(self):
        """--require-valid-coords 기본값"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            assert args.require_valid_coords is False

    def test_parse_no_require_valid_coords(self):
        """--no-require-valid-coords 플래그 파싱"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--no-require-valid-coords"]):
            args = parse_args()
            assert args.require_valid_coords is False


class TestBuildConfigFromArgs:
    """build_config_from_args 함수 테스트"""

    def test_build_config_default(self):
        """기본 설정으로 config 생성"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            config = build_config_from_args(args)
            assert config.output_dir == "output"
            # SeoulCrawlConfig 기본값은 FilterOptions.moderate() (min_household=1)
            assert config.filter_options.min_household == 1
            assert config.filter_options.require_valid_coords is False

    def test_build_config_with_min_household(self):
        """min_household 설정으로 config 생성"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--min-household", "50"]):
            args = parse_args()
            config = build_config_from_args(args)
            assert config.filter_options.min_household == 50

    def test_build_config_with_output(self):
        """output 설정으로 config 생성"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--output", "custom/output.csv"]):
            args = parse_args()
            config = build_config_from_args(args)
            assert config.output_dir == "custom"

    def test_build_config_with_require_valid_coords(self):
        """require_valid_coords 설정으로 config 생성"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--require-valid-coords"]):
            args = parse_args()
            config = build_config_from_args(args)
            assert config.filter_options.require_valid_coords is True

    def test_build_custom_output_file(self):
        """커스텀 output 파일명 설정"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--output", "output/test.csv"]):
            args = parse_args()
            config = build_config_from_args(args)
            # output_dir만 변경되고, output_file은 timestamp가 포함된 기본값 사용
            assert config.output_dir == "output"
            assert "test.csv" not in config.output_file


class TestSelectGuFromArgs:
    """select_gu_from_args 함수 테스트"""

    def test_select_gu_single_code(self):
        """단일 구 코드 선택"""
        with patch("sys.argv", ["cli", "--gu-code", "11560"]):
            args = parse_args()
            gu_list = select_gu_from_args(args)
            assert len(gu_list) == 1
            assert gu_list[0] == ("11560", "영등포구")

    def test_select_gu_multiple_codes(self):
        """여러 구 코드 선택"""
        with patch("sys.argv", ["cli", "--gu-code", "11560", "--gu-code", "11680"]):
            args = parse_args()
            gu_list = select_gu_from_args(args)
            assert len(gu_list) == 2
            assert ("11560", "영등포구") in gu_list
            assert ("11680", "강남구") in gu_list

    def test_select_gu_all(self):
        """--all 플래그로 모든 구 선택"""
        with patch("sys.argv", ["cli", "--all"]):
            args = parse_args()
            gu_list = select_gu_from_args(args)
            assert len(gu_list) == 25
            assert ("11560", "영등포구") in gu_list
            assert ("11680", "강남구") in gu_list
            assert ("11545", "금천구") in gu_list

    def test_select_gu_invalid_code(self):
        """잘못된 구 코드 처리"""
        with patch("sys.argv", ["cli", "--gu-code", "99999"]):
            args = parse_args()
            with pytest.raises(ValueError, match="유효하지 않은 구 코드"):
                select_gu_from_args(args)

    def test_select_gu_no_selection(self):
        """구 코드와 --all 플래그 모두 없는 경우"""
        with patch("sys.argv", ["cli"]):
            args = parse_args()
            with pytest.raises(ValueError, match="구 코드를 지정하거나 --all 플래그를 사용하세요"):
                select_gu_from_args(args)

    def test_select_gu_empty_list(self):
        """빈 구 코드 리스트 처리"""
        with patch("sys.argv", ["cli"]):
            args = parse_args()
            args.gu_code = []
            args.all = False
            with pytest.raises(ValueError, match="구 코드를 지정하거나 --all 플래그를 사용하세요"):
                select_gu_from_args(args)

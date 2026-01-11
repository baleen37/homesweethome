"""CLI 공통 유틸리티 유닛 테스트

cli_common 모듈의 함수들을 테스트합니다.
"""

from unittest.mock import patch

from crawler.commands.cli_common import (
    add_all_argument,
    add_output_argument,
    create_dong_code_parser,
    resolve_dong_codes,
)


class TestCreateDongCodeParser:
    """create_dong_code_parser 함수 테스트"""

    def test_creates_parser_with_dong_code_argument(self):
        """--dong-code 인자를 포함한 파서 생성"""
        parser = create_dong_code_parser("테스트 설명")

        # 파서가 생성되었는지 확인
        assert parser is not None
        assert parser.description == "테스트 설명"

        # --dong-code 인자가 있는지 확인
        with patch("sys.argv", ["test", "--dong-code", "1150010100"]):
            args = parser.parse_args()
            assert args.dong_code == ["1150010100"]

    def test_dong_code_argument_is_append_action(self):
        """--dong-code 인자는 여러 번 사용 가능"""
        parser = create_dong_code_parser("테스트 설명")

        with patch("sys.argv", ["test", "--dong-code", "1150010100", "--dong-code", "1150010200"]):
            args = parser.parse_args()
            assert args.dong_code == ["1150010100", "1150010200"]

    def test_dong_code_argument_defaults_to_none(self):
        """--dong-code 인자 기본값은 None"""
        parser = create_dong_code_parser("테스트 설명")

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            assert args.dong_code is None


class TestAddAllArgument:
    """add_all_argument 함수 테스트"""

    def test_adds_all_flag_to_parser(self):
        """--all 플래그를 파서에 추가"""
        parser = create_dong_code_parser("테스트 설명")
        add_all_argument(parser)

        # --all 플래그가 있는지 확인
        with patch("sys.argv", ["test", "--all"]):
            args = parser.parse_args()
            assert args.all is True

    def test_all_flag_defaults_to_false(self):
        """--all 플래그 기본값은 False"""
        parser = create_dong_code_parser("테스트 설명")
        add_all_argument(parser)

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            assert args.all is False


class TestAddOutputArgument:
    """add_output_argument 함수 테스트"""

    def test_adds_output_argument_with_custom_default(self):
        """커스텀 기본값으로 --output 인자 추가"""
        parser = create_dong_code_parser("테스트 설명")
        add_output_argument(parser, default="default_output.csv", help="커스텀 도움말")

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            assert args.output == "default_output.csv"

    def test_output_argument_can_be_overridden(self):
        """--output 인자 값 오버라이드"""
        parser = create_dong_code_parser("테스트 설명")
        add_output_argument(parser, default="default.csv", help="도움말")

        with patch("sys.argv", ["test", "--output", "custom_output.csv"]):
            args = parser.parse_args()
            assert args.output == "custom_output.csv"

    def test_output_argument_with_custom_help(self):
        """커스텀 도움말 텍스트 확인"""
        parser = create_dong_code_parser("테스트 설명")
        add_output_argument(parser, default="output.csv", help="출력 파일 경로")

        # 도움말 텍스트가 포함되어 있는지 확인
        help_text = parser.format_help()
        assert "출력 파일 경로" in help_text


class TestResolveDongCodes:
    """resolve_dong_codes 함수 테스트"""

    def test_returns_all_dong_codes_when_all_flag_is_true(self):
        """--all 플래그가 True이면 서울 전체 법정동 코드 반환"""
        parser = create_dong_code_parser("테스트 설명")
        add_all_argument(parser)

        from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES

        with patch("sys.argv", ["test", "--all"]):
            args = parser.parse_args()
            dong_codes = resolve_dong_codes(args, has_all_flag=True)

            assert dong_codes == list(SEOUL_LEGAL_DONG_CODES.keys())
            assert len(dong_codes) > 0

    def test_returns_provided_dong_codes_when_dong_code_argument_given(self):
        """--dong-code 인자가 제공되면 해당 동 코드 반환"""
        parser = create_dong_code_parser("테스트 설명")
        add_all_argument(parser)

        with patch("sys.argv", ["test", "--dong-code", "1150010100", "--dong-code", "1150010200"]):
            args = parser.parse_args()
            dong_codes = resolve_dong_codes(args, has_all_flag=True)

            assert dong_codes == ["1150010100", "1150010200"]

    def test_returns_first_five_dong_codes_when_no_argument_provided(self):
        """인자가 없으면 기본값으로 5개 샘플 동 반환"""
        parser = create_dong_code_parser("테스트 설명")

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            dong_codes = resolve_dong_codes(args, has_all_flag=True)

            from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES

            expected = list(SEOUL_LEGAL_DONG_CODES.keys())[:5]
            assert dong_codes == expected
            assert len(dong_codes) == 5

    def test_ignores_all_flag_when_has_all_flag_is_false(self):
        """has_all_flag가 False이면 --all 플래그 무시"""
        parser = create_dong_code_parser("테스트 설명")

        # --all 플래그가 있지만 has_all_flag=False인 경우
        with patch("sys.argv", ["test", "--dong-code", "1150010100"]):
            args = parser.parse_args()
            # all 속성이 없는 경우를 테스트하기 위해 속성 제거
            if hasattr(args, "all"):
                delattr(args, "all")

            dong_codes = resolve_dong_codes(args, has_all_flag=False)
            assert dong_codes == ["1150010100"]

    def test_ignores_all_flag_when_has_all_flag_false_and_no_dong_code(self):
        """has_all_flag=False이고 dong_code가 없으면 기본값 반환"""
        parser = create_dong_code_parser("테스트 설명")

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            # all 속성이 없는 경우
            if hasattr(args, "all"):
                delattr(args, "all")

            dong_codes = resolve_dong_codes(args, has_all_flag=False)

            from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES

            expected = list(SEOUL_LEGAL_DONG_CODES.keys())[:5]
            assert dong_codes == expected

    def test_all_flag_takes_precedence_over_dong_code(self):
        """--all 플래그가 --dong-code 인자보다 우선순위 높음"""
        parser = create_dong_code_parser("테스트 설명")
        add_all_argument(parser)

        from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES

        with patch("sys.argv", ["test", "--all", "--dong-code", "1150010100"]):
            args = parser.parse_args()
            dong_codes = resolve_dong_codes(args, has_all_flag=True)

            # --all이 --dong-code보다 우선
            assert dong_codes == list(SEOUL_LEGAL_DONG_CODES.keys())
            assert len(dong_codes) > 1

    def test_empty_dong_code_list_returns_default(self):
        """빈 dong_code 리스트는 기본값 5개 반환"""
        parser = create_dong_code_parser("테스트 설명")

        with patch("sys.argv", ["test"]):
            args = parser.parse_args()
            args.dong_code = []

            dong_codes = resolve_dong_codes(args, has_all_flag=True)

            from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES

            expected = list(SEOUL_LEGAL_DONG_CODES.keys())[:5]
            assert dong_codes == expected

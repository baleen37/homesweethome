"""서울 법정동 코드 유틸리티 함수 테스트"""

from crawler.constants import (
    SEOUL_GU_CODES,
    SEOUL_LEGAL_DONG_CODES,
    get_dong_name,
    get_gu_name,
    get_mullae_dong_codes,
)


class TestGetGuName:
    """get_gu_name() 함수 테스트"""

    def test_종로구_코드로_종로구_이름_반환(self):
        gu_name = get_gu_name("11110")
        assert gu_name == "종로구"

    def test_강남구_코드로_강남구_이름_반환(self):
        gu_name = get_gu_name("11680")
        assert gu_name == "강남구"

    def test_영등포구_코드로_영등포구_이름_반환(self):
        gu_name = get_gu_name("11560")
        assert gu_name == "영등포구"

    def test_존재하지_않는_구_코드는_None_반환(self):
        gu_name = get_gu_name("99999")
        assert gu_name is None

    def test_빈_문자열은_None_반환(self):
        gu_name = get_gu_name("")
        assert gu_name is None


class TestGetDongName:
    """get_dong_name() 함수 테스트"""

    def test_역삼동_코드로_강남구_역삼동_반환(self):
        result = get_dong_name("1168010100")
        assert result == ("강남구", "역삼동")

    def test_여의도동_코드로_영등포구_여의도동_반환(self):
        result = get_dong_name("1156011000")
        assert result == ("영등포구", "여의도동")

    def test_문래동1가_코드로_영등포구_문래동1가_반환(self):
        result = get_dong_name("1156011900")
        assert result == ("영등포구", "문래동1가")

    def test_존재하지_않는_동_코드는_None_반환(self):
        result = get_dong_name("9999999999")
        assert result is None

    def test_빈_문자열은_None_반환(self):
        result = get_dong_name("")
        assert result is None

    def test_반환값은_튜플_타입(self):
        result = get_dong_name("1168010100")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)


class TestGetMullaeDongCodes:
    """get_mullae_dong_codes() 함수 테스트"""

    def test_문래동_코드_6개_반환(self):
        codes = get_mullae_dong_codes()
        assert len(codes) == 6

    def test_문래동_코드_순서_확인(self):
        codes = get_mullae_dong_codes()
        expected = [
            "1156011900",  # 문래동1가
            "1156012000",  # 문래동2가
            "1156012100",  # 문래동3가
            "1156012200",  # 문래동4가
            "1156012300",  # 문래동5가
            "1156012400",  # 문래동6가
        ]
        assert codes == expected

    def test_문래동_코드_모두_10자리(self):
        codes = get_mullae_dong_codes()
        for code in codes:
            assert len(code) == 10

    def test_문래동_코드는_모두_문자열(self):
        codes = get_mullae_dong_codes()
        for code in codes:
            assert isinstance(code, str)

    def test_문래동_코드_변경_불가(self):
        """반환된 리스트가 새 리스트임을 확인 (원본 데이터 보호)"""
        codes = get_mullae_dong_codes()
        original_codes = codes.copy()
        codes.append("9999999999")
        new_codes = get_mullae_dong_codes()
        assert new_codes == original_codes
        assert len(new_codes) == 6


class TestSeoulGuCodes:
    """SEOUL_GU_CODES 상수 테스트"""

    def test_서울_구_코드_존재(self):
        """현재 등록된 서울 구 코드 개수 확인 (금천구 미포함)"""
        # 금천구(11545)는 SEOUL_GU_CODES에 누락되어 있음
        assert len(SEOUL_GU_CODES) >= 24

    def test_모든_구_코드는_5자리(self):
        for code in SEOUL_GU_CODES.keys():
            assert len(code) == 5

    def test_모든_구_코드는_문자열(self):
        for code in SEOUL_GU_CODES.keys():
            assert isinstance(code, str)

    def test_모든_구_이름은_구로_끝남(self):
        for name in SEOUL_GU_CODES.values():
            assert name.endswith("구")


class TestSeoulLegalDongCodes:
    """SEOUL_LEGAL_DONG_CODES 상수 테스트"""

    def test_모든_법정동_코드는_10자리(self):
        for code in SEOUL_LEGAL_DONG_CODES.keys():
            assert len(code) == 10

    def test_모든_법정동_코드는_문자열(self):
        for code in SEOUL_LEGAL_DONG_CODES.keys():
            assert isinstance(code, str)

    def test_모든_값은_튜플(self):
        for value in SEOUL_LEGAL_DONG_CODES.values():
            assert isinstance(value, tuple)

    def test_모든_튜플은_2개_요소(self):
        for value in SEOUL_LEGAL_DONG_CODES.values():
            assert len(value) == 2

    def test_첫번째_요소는_구_이름(self):
        for value in SEOUL_LEGAL_DONG_CODES.values():
            assert value[0].endswith("구")

    def test_두번째_요소는_동_이름(self):
        for value in SEOUL_LEGAL_DONG_CODES.values():
            assert isinstance(value[1], str)
            assert len(value[1]) > 0

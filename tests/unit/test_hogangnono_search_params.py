"""SearchParams 클래스 단위 테스트"""

import pytest

from crawler.api.hogangnono_client import SearchParams

# Import test setup to configure path and mocks


class TestSearchParams:
    """SearchParams 클래스 테스트"""

    def test_default_initialization(self):
        """기본값으로 초기화 테스트"""
        params = SearchParams()

        assert params.level == 17
        assert params.tradeType == 0
        assert params.aptType == -1
        assert params.priceType == 0
        assert params.rentType == 0
        assert params.map == "google"
        assert params.startX is None
        assert params.endX is None
        assert params.startY is None
        assert params.endY is None

    def test_initialization_with_bbox(self):
        """bbox 파라미터로 초기화 테스트"""
        bbox = (126.734086, 37.413294, 127.183394, 37.715133)
        params = SearchParams(bbox=bbox)

        assert params.startX == 126.734086
        assert params.startY == 37.413294
        assert params.endX == 127.183394
        assert params.endY == 37.715133

    def test_initialization_with_individual_coordinates(self):
        """개별 좌표로 초기화 테스트"""
        params = SearchParams(startX=126.7, endX=127.0, startY=37.4, endY=37.5)

        assert params.startX == 126.7
        assert params.endX == 127.0
        assert params.startY == 37.4
        assert params.endY == 37.5

    def test_invalid_level_raises_value_error(self):
        """유효하지 않은 level 값에 대한 예외 처리 테스트"""
        with pytest.raises(ValueError, match="level must be between 1 and 18"):
            SearchParams(level=0)

        with pytest.raises(ValueError, match="level must be between 1 and 18"):
            SearchParams(level=19)

        with pytest.raises(ValueError, match="level must be between 1 and 18"):
            SearchParams(level=-1)

    def test_valid_level_acceptance(self):
        """유효한 level 값 허용 테스트"""
        for level in range(1, 19):
            params = SearchParams(level=level)
            assert params.level == level

    def test_invalid_trade_type_raises_value_error(self):
        """유효하지 않은 tradeType 값에 대한 예외 처리 테스트"""
        with pytest.raises(ValueError, match="tradeType must be one of"):
            SearchParams(tradeType=3)

        with pytest.raises(ValueError, match="tradeType must be one of"):
            SearchParams(tradeType=-1)

    def test_valid_trade_type_acceptance(self):
        """유효한 tradeType 값 허용 테스트"""
        valid_types = [0, 1, 2]  # 매매, 전세, 월세
        for trade_type in valid_types:
            params = SearchParams(tradeType=trade_type)
            assert params.tradeType == trade_type

    def test_invalid_apt_type_raises_value_error(self):
        """유효하지 않은 aptType 값에 대한 예외 처리 테스트"""
        with pytest.raises(ValueError, match="aptType must be one of"):
            SearchParams(aptType=3)

        with pytest.raises(ValueError, match="aptType must be one of"):
            SearchParams(aptType=-2)

    def test_valid_apt_type_acceptance(self):
        """유효한 aptType 값 허용 테스트"""
        valid_types = [-1, 0, 1, 2]  # 전체, 아파트, 주상복합, 오피스텔
        for apt_type in valid_types:
            params = SearchParams(aptType=apt_type)
            assert params.aptType == apt_type

    def test_to_dict_with_all_parameters(self):
        """모든 파라미터가 포함된 to_dict 테스트"""
        params = SearchParams(
            startX=126.7,
            endX=127.0,
            startY=37.4,
            endY=37.5,
            level=15,
            tradeType=1,
            areaFrom=30.0,
            areaTo=100.0,
            priceFrom=50000,
            priceTo=200000,
            aptType=0,
            priceType=1,
            rentType=2,
        )

        result = params.to_dict()

        # 필수 파라미터 확인
        assert result["startX"] == 126.7
        assert result["endX"] == 127.0
        assert result["startY"] == 37.4
        assert result["endY"] == 37.5

        # 선택적 파라미터 확인
        assert result["level"] == "15"  # 문자열로 변환되어야 함
        assert result["tradeType"] == 1
        assert result["areaFrom"] == 30.0
        assert result["areaTo"] == 100.0
        assert result["priceFrom"] == 50000
        assert result["priceTo"] == 200000
        assert result["aptType"] == 0
        assert result["priceType"] == 1
        assert result["rentType"] == 2

        # 항상 포함되는 파라미터
        assert result["map"] == "google"
        assert result["screenWidth"] == 1200
        assert result["screenHeight"] == 924
        assert result["apt"] == ""

    def test_to_dict_with_minimal_parameters(self):
        """최소 파라미터만 포함된 to_dict 테스트"""
        params = SearchParams()

        result = params.to_dict()

        # 기본 파라미터만 포함
        assert "startX" not in result
        assert "endX" not in result
        assert "startY" not in result
        assert "endY" not in result

        # 기본값 포함
        assert result["level"] == "17"
        assert result["tradeType"] == 0
        assert result["aptType"] == -1

        # 항상 포함되는 파라미터
        assert result["map"] == "google"
        assert result["screenWidth"] == 1200
        assert result["screenHeight"] == 924
        assert result["apt"] == ""

    def test_to_dict_with_none_values(self):
        """None 값이 제외되는지 테스트"""
        params = SearchParams(
            startX=126.7,
            endX=None,  # None 값
            startY=37.4,
            endY=None,  # None 값
            areaFrom=None,  # None 값
        )

        result = params.to_dict()

        # None이 아닌 값만 포함
        assert result["startX"] == 126.7
        assert result["startY"] == 37.4

        # None 값은 포함되지 않음
        assert "endX" not in result
        assert "endY" not in result
        assert "areaFrom" not in result

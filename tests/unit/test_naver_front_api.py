"""네이버 부동산 Front API 단위 테스트

네이버 부동산 Front API (https://fin.land.naver.com)의 엔드포인트를 테스트합니다.

API 엔드포인트:
- /front-api/v1/article/key - 매물 연관 키 조회
- /front-api/v1/article/basicInfo - 매물 상세 정보
- /front-api/v1/complex - 단지 정보
- /front-api/v1/complex/evStaion - 전기차 충전소 (오타 주의)
"""

import pytest

# 이 import는 NaverFrontAPIClient가 존재하지 않으므로 실패할 것입니다 (Red Phase)
from crawler.naver_front_api import NaverFrontAPIClient

# =============================================================================
# Article Key 관련 테스트
# =============================================================================


class TestGetArticleKeyURL:
    """매물 연관 키 조회 URL 빌드 테스트"""

    @pytest.mark.unit
    def test_get_article_key_url_with_article_id(self):
        """articleId 파라미터로 올바른 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        article_id = "12345678"

        url = client.get_article_key_url(article_id)

        # Base URL 확인
        assert url.startswith("https://fin.land.naver.com/front-api/v1/article/key")

        # articleId 파라미터 포함 확인
        assert "articleId=12345678" in url or "articleId=%2212345678%22" in url

    @pytest.mark.unit
    def test_get_article_key_url_with_different_article_id(self):
        """다른 articleId로 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        article_id = "87654321"

        url = client.get_article_key_url(article_id)

        assert "articleId=87654321" in url or "articleId=%2287654321%22" in url


class TestParseArticleKeyResponse:
    """매물 연관 키 응답 파싱 테스트"""

    @pytest.mark.unit
    def test_parse_article_key_response_extracts_complex_number(self):
        """응답에서 complexNumber를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexNumber": "12345",
                "pyeongTypeNumber": "1",
                "articleId": "67890",
            }
        }

        result = client.parse_article_key_response(response)

        assert result["complexNumber"] == "12345"

    @pytest.mark.unit
    def test_parse_article_key_response_extracts_pyeong_type_number(self):
        """응답에서 pyeongTypeNumber를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexNumber": "12345",
                "pyeongTypeNumber": "2",
                "articleId": "67890",
            }
        }

        result = client.parse_article_key_response(response)

        assert result["pyeongTypeNumber"] == "2"

    @pytest.mark.unit
    def test_parse_article_key_response_extracts_article_id(self):
        """응답에서 articleId를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexNumber": "12345",
                "pyeongTypeNumber": "1",
                "articleId": "67890",
            }
        }

        result = client.parse_article_key_response(response)

        assert result["articleId"] == "67890"

    @pytest.mark.unit
    def test_parse_article_key_response_handles_empty_response(self):
        """빈 응답을 처리해야 함"""
        client = NaverFrontAPIClient()
        response = {}

        result = client.parse_article_key_response(response)

        # 빈 결과 반환 또는 None 반환
        assert result is None or result == {}

    @pytest.mark.unit
    def test_parse_article_key_response_handles_missing_result_key(self):
        """result 키가 없는 응답을 처리해야 함"""
        client = NaverFrontAPIClient()
        response = {"data": {}}

        result = client.parse_article_key_response(response)

        # 적절하게 처리해야 함
        assert result is None or "complexNumber" not in result


# =============================================================================
# Article Basic Info 관련 테스트
# =============================================================================


class TestGetArticleBasicInfoURL:
    """매물 상세 정보 URL 빌드 테스트"""

    @pytest.mark.unit
    def test_get_article_basic_info_url_with_all_params(self):
        """모든 파라미터로 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        article_id = "12345678"
        real_estate_type = "APT"
        trade_type = "A1"

        url = client.get_article_basic_info_url(article_id, real_estate_type, trade_type)

        # Base URL 확인
        assert url.startswith("https://fin.land.naver.com/front-api/v1/article/basicInfo")

        # 파라미터 포함 확인
        assert "articleId=12345678" in url or "articleId=%2212345678%22" in url
        assert "realEstateType=APT" in url or "realEstateType=%22APT%22" in url
        assert "tradeType=A1" in url or "tradeType=%22A1%22" in url

    @pytest.mark.unit
    def test_get_article_basic_info_url_with_different_params(self):
        """다른 파라미터로 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        article_id = "99999999"
        real_estate_type = "OPST"
        trade_type = "B1"

        url = client.get_article_basic_info_url(article_id, real_estate_type, trade_type)

        assert "articleId=99999999" in url or "articleId=%2299999999%22" in url
        assert "realEstateType=OPST" in url or "realEstateType=%22OPST%22" in url
        assert "tradeType=B1" in url or "tradeType=%22B1%22" in url


class TestParseBasicInfoPrice:
    """매물 상세 정보 가격 파싱 테스트"""

    @pytest.mark.unit
    def test_parse_basic_info_price_extracts_deal_price(self):
        """매매 가격을 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "dealPrice": "50000",
                    "warrantPrice": "40000",
                }
            }
        }

        result = client.parse_basic_info_price(response)

        assert "dealPrice" in result
        assert result["dealPrice"] == "50000"

    @pytest.mark.unit
    def test_parse_basic_info_price_extracts_warrant_price(self):
        """전세 가격을 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "dealPrice": "50000",
                    "warrantPrice": "40000",
                }
            }
        }

        result = client.parse_basic_info_price(response)

        assert "warrantPrice" in result
        assert result["warrantPrice"] == "40000"

    @pytest.mark.unit
    def test_parse_basic_info_price_handles_missing_prices(self):
        """가격 정보가 없는 경우를 처리해야 함"""
        client = NaverFrontAPIClient()
        response = {"result": {"articleDetail": {}}}

        result = client.parse_basic_info_price(response)

        # 빈 값 또는 None 처리
        assert result is None or result.get("dealPrice") is None


class TestParseBasicInfoDetail:
    """매물 상세 정보 파싱 테스트 (층수, 방수, 방향)"""

    @pytest.mark.unit
    def test_parse_basic_info_detail_extracts_floor(self):
        """층수 정보를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "floorInfo": "5층",
                    "roomCount": "3",
                    "direction": "남향",
                }
            }
        }

        result = client.parse_basic_info_detail(response)

        assert "floorInfo" in result
        assert result["floorInfo"] == "5층"

    @pytest.mark.unit
    def test_parse_basic_info_detail_extracts_room_count(self):
        """방수 정보를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "floorInfo": "5층",
                    "roomCount": "3",
                    "direction": "남향",
                }
            }
        }

        result = client.parse_basic_info_detail(response)

        assert "roomCount" in result
        assert result["roomCount"] == "3"

    @pytest.mark.unit
    def test_parse_basic_info_detail_extracts_direction(self):
        """방향 정보를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "floorInfo": "5층",
                    "roomCount": "3",
                    "direction": "남향",
                }
            }
        }

        result = client.parse_basic_info_detail(response)

        assert "direction" in result
        assert result["direction"] == "남향"


class TestParseBasicInfoSize:
    """매물 면적 정보 파싱 테스트"""

    @pytest.mark.unit
    def test_parse_basic_info_size_extracts_area1(self):
        """공급 면적(area1)을 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "area1": "84.95",
                    "area2": "59.95",
                }
            }
        }

        result = client.parse_basic_info_size(response)

        assert "area1" in result
        assert result["area1"] == "84.95"

    @pytest.mark.unit
    def test_parse_basic_info_size_extracts_area2(self):
        """전용 면적(area2)을 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "articleDetail": {
                    "area1": "84.95",
                    "area2": "59.95",
                }
            }
        }

        result = client.parse_basic_info_size(response)

        assert "area2" in result
        assert result["area2"] == "59.95"


# =============================================================================
# Complex 관련 테스트
# =============================================================================


class TestGetComplexURL:
    """단지 정보 URL 빌드 테스트"""

    @pytest.mark.unit
    def test_get_complex_url_with_complex_number(self):
        """complexNumber 파라미터로 올바른 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        complex_number = "12345"

        url = client.get_complex_url(complex_number)

        # Base URL 확인
        assert url.startswith("https://fin.land.naver.com/front-api/v1/complex")

        # complexNumber 파라미터 포함 확인
        assert "complexNumber=12345" in url or "complexNumber=%2212345%22" in url

    @pytest.mark.unit
    def test_get_complex_url_with_different_complex_number(self):
        """다른 complexNumber로 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        complex_number = "99999"

        url = client.get_complex_url(complex_number)

        assert "complexNumber=99999" in url or "complexNumber=%2299999%22" in url


class TestParseComplexResponse:
    """단지 정보 응답 파싱 테스트"""

    @pytest.mark.unit
    def test_parse_complex_response_extracts_complex_name(self):
        """응답에서 단지명을 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexName": "테스트아파트",
                "address": "서울시 강남구",
                "houseHoldCount": "100",
            }
        }

        result = client.parse_complex_response(response)

        assert result["complexName"] == "테스트아파트"

    @pytest.mark.unit
    def test_parse_complex_response_extracts_address(self):
        """응답에서 주소를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexName": "테스트아파트",
                "address": "서울시 강남구 테스트로 123",
                "houseHoldCount": "100",
            }
        }

        result = client.parse_complex_response(response)

        assert "address" in result
        assert result["address"] == "서울시 강남구 테스트로 123"

    @pytest.mark.unit
    def test_parse_complex_response_extracts_house_hold_count(self):
        """응답에서 세대수를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexName": "테스트아파트",
                "address": "서울시 강남구",
                "houseHoldCount": "500",
            }
        }

        result = client.parse_complex_response(response)

        assert "houseHoldCount" in result
        assert result["houseHoldCount"] == "500"

    @pytest.mark.unit
    def test_parse_complex_response_handles_empty_response(self):
        """빈 응답을 처리해야 함"""
        client = NaverFrontAPIClient()
        response = {}

        result = client.parse_complex_response(response)

        # 빈 결과 반환 또는 None 반환
        assert result is None or result == {}

    @pytest.mark.unit
    def test_parse_complex_response_extracts_all_fields(self):
        """모든 필드를 추출해야 함"""
        client = NaverFrontAPIClient()
        response = {
            "result": {
                "complexName": "테스트아파트",
                "address": "서울시 강남구",
                "houseHoldCount": "300",
                "builtYear": "2000",
                "maxFloor": "20",
            }
        }

        result = client.parse_complex_response(response)

        assert result["complexName"] == "테스트아파트"
        assert result["address"] == "서울시 강남구"
        assert result["houseHoldCount"] == "300"
        # 추가 필드도 파싱되는지 확인
        assert "builtYear" in result or len(result) >= 3


# =============================================================================
# 전기차 충전소 관련 테스트 (evStaion 오타 주의)
# =============================================================================


class TestGetEVStationURL:
    """전기차 충전소 URL 빌드 테스트"""

    @pytest.mark.unit
    def test_get_ev_station_url_with_complex_number(self):
        """complexNumber 파라미터로 올바른 URL을 빌드해야 함"""
        client = NaverFrontAPIClient()
        complex_number = "12345"

        url = client.get_ev_station_url(complex_number)

        # Base URL 확인 (오타 주의: evStaion)
        assert url.startswith("https://fin.land.naver.com/front-api/v1/complex/evStaion")

        # complexNumber 파라미터 포함 확인
        assert "complexNumber=12345" in url or "complexNumber=%2212345%22" in url

    @pytest.mark.unit
    def test_get_ev_station_url_maintains_typo_in_endpoint(self):
        """API 엔드포인트의 오타(evStaion)를 유지해야 함"""
        client = NaverFrontAPIClient()
        complex_number = "12345"

        url = client.get_ev_station_url(complex_number)

        # 오타가 포함되어 있는지 확인
        assert "/evStaion" in url
        # 올바른 철자가 없어야 함
        assert "/evStation" not in url

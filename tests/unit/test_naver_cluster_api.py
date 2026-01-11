"""네이버 부동산 Cluster API 단위 테스트

Cluster API는 모바일 네이버 부동산의 매물 목록 API입니다.
- Endpoint: https://m.land.naver.com/cluster/ajax/articleList
- Method: GET
- 주요 기능: 지도 경계 내 매물 조회, 필터링, 페이지네이션
"""

from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from crawler.naver_cluster_api import (
    NaverClusterAPIClient,
    build_cluster_url,
    parse_article_item,
    parse_cluster_response,
)

# =============================================================================
# test_build_url_with_coordinates_only - 기본 좌표만으로 URL 빌드
# =============================================================================


@pytest.mark.unit
def test_build_url_with_coordinates_only():
    """기본 좌표만으로 URL 빌드 확인

    필수 파라미터:
    - z: 줌 레벨 (13)
    - lat, lon: 중심 좌표 (서울시청)
    - btm, lft, top, rgt: 지도 경계
    """
    url = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
    )

    # URL이 문자열이어야 함
    assert isinstance(url, str)
    assert url.startswith("https://m.land.naver.com/cluster/ajax/articleList")

    # URL 파싱으로 파라미터 검증
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # 필수 파라미터 존재 확인
    assert "z" in params
    assert params["z"][0] == "13"
    assert "lat" in params
    assert params["lat"][0] == "37.5665"
    assert "lon" in params
    assert params["lon"][0] == "126.9780"
    assert "btm" in params
    assert params["btm"][0] == "37.5600"
    assert "lft" in params
    assert params["lft"][0] == "126.9700"
    assert "top" in params
    assert params["top"][0] == "37.5730"
    assert "rgt" in params
    assert params["rgt"][0] == "126.9860"


# =============================================================================
# test_build_url_with_filters - 필터 포함 URL 빌드
# =============================================================================


@pytest.mark.unit
def test_build_url_with_filters():
    """필터 포함 URL 빌드 확인

    필터 파라미터:
    - cortarNo: 법정동코드
    - rletTpCd: 부동산유형 (A01:A02 - 아파트:오피스텔)
    - tradTpCd: 거래유형 (A1:B2 - 매매:전세)
    - spcMin/Max: 면적 필터
    - dprcMin/Max: 매매가 필터
    """
    url = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        cortar_no="1150010100",  # 사직동
        rlet_tp_cd="A01:A02",  # 아파트:오피스텔
        trad_tp_cd="A1:B2",  # 매매:전세
        spc_min=30,  # 30㎡ 이상
        spc_max=150,  # 150㎡ 이하
        dprc_min=50000,  # 5억 이상
        dprc_max=200000,  # 20억 이하
    )

    # URL 파싱으로 필터 파라미터 검증
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # 필수 파라미터 확인
    assert "cortarNo" in params
    assert params["cortarNo"][0] == "1150010100"

    assert "rletTpCd" in params
    assert params["rletTpCd"][0] == "A01:A02"

    assert "tradTpCd" in params
    assert params["tradTpCd"][0] == "A1:B2"

    assert "spcMin" in params
    assert params["spcMin"][0] == "30"

    assert "spcMax" in params
    assert params["spcMax"][0] == "150"

    assert "dprcMin" in params
    assert params["dprcMin"][0] == "50000"

    assert "dprcMax" in params
    assert params["dprcMax"][0] == "200000"


@pytest.mark.unit
def test_build_url_with_single_trade_type():
    """단일 거래유형 필터 URL 빌드 확인"""
    url = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        trad_tp_cd="A1",  # 매매만
    )

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert params["tradTpCd"][0] == "A1"


# =============================================================================
# test_parse_response_basic_fields - 기본 응답 파싱
# =============================================================================


@pytest.mark.unit
def test_parse_response_basic_fields():
    """기본 응답 필드 파싱 확인

    Response 구조:
    {
        "code": "string",
        "hasPaidPreSale": boolean,
        "more": boolean,
        "z": number,
        "page": number,
        "body": [...]
    }
    """
    response_data = {
        "code": "200",
        "hasPaidPreSale": False,
        "more": True,
        "z": 13,
        "page": 1,
        "body": [
            {
                "atclNo": "12345",
                "cortarNo": "1150010100",
                "atclNm": "테스트아파트",
                "rletTpCd": "A01",
                "tradTpCd": "A1",
                "prc": 50000,
                "rentPrc": 150,
                "flrInfo": "7/10",
                "spc1": "46",
                "spc2": "29.93",
                "lat": 37.523,
                "lng": 126.901,
                "atclFetrDesc": "설명",
                "tagList": ["2년이내", "융자금없는"],
            }
        ],
    }

    result = parse_cluster_response(response_data)

    # 기본 응답 필드 확인
    assert result.code == "200"
    assert result.has_paid_presale is False
    assert result.more is True
    assert result.zoom == 13
    assert result.page == 1
    assert len(result.articles) == 1


@pytest.mark.unit
def test_parse_response_empty_body():
    """빈 응답 파싱 확인"""
    response_data = {
        "code": "200",
        "hasPaidPreSale": False,
        "more": False,
        "z": 13,
        "page": 1,
        "body": [],
    }

    result = parse_cluster_response(response_data)

    assert result.code == "200"
    assert len(result.articles) == 0


# =============================================================================
# test_parse_article_item - 개별 매물 아이템 파싱
# =============================================================================


@pytest.mark.unit
def test_parse_article_item_basic():
    """매물 아이템 기본 필드 파싱 확인"""
    article_data = {
        "atclNo": "12345",
        "cortarNo": "1150010100",
        "atclNm": "테스트아파트 101동",
        "rletTpCd": "A01",
        "tradTpCd": "A1",
        "prc": 50000,
        "rentPrc": 150,
        "flrInfo": "7/10",
        "spc1": "46",
        "spc2": "29.93",
        "lat": 37.523,
        "lng": 126.901,
        "atclFetrDesc": "강남역 도보 5분, 신축급 리모델링 완료",
        "tagList": ["2년이내", "융자금없는", "반려동물가능"],
    }

    article = parse_article_item(article_data)

    # 기본 필드 확인
    assert article.atcl_no == "12345"
    assert article.cortar_no == "1150010100"
    assert article.atcl_nm == "테스트아파트 101동"
    assert article.rlet_tp_cd == "A01"
    assert article.trad_tp_cd == "A1"

    # 가격 정보
    assert article.prc == 50000
    assert article.rent_prc == 150

    # 상세 정보
    assert article.flr_info == "7/10"
    assert article.spc1 == "46"
    assert article.spc2 == "29.93"

    # 좌표
    assert article.lat == 37.523
    assert article.lng == 126.901

    # 설명과 태그
    assert article.atcl_fetr_desc == "강남역 도보 5분, 신축급 리모델링 완료"
    assert article.tag_list == ["2년이내", "융자금없는", "반려동물가능"]


@pytest.mark.unit
def test_parse_article_item_optional_fields():
    """선택적 필드가 없는 경우 파싱 확인"""
    article_data = {
        "atclNo": "67890",
        "cortarNo": "1168010100",
        "atclNm": "최소필드아파트",
        "rletTpCd": "A02",
        "tradTpCd": "B2",
        # prc, rentPrc 없음 (전세의 경우 prc만 있을 수 있음)
        "flrInfo": "3/5",
        # spc1, spc2 없음
        "lat": 37.520,
        "lng": 126.900,
        # atclFetrDesc 없음
        # tagList 없음
    }

    article = parse_article_item(article_data)

    # 필수 필드 확인
    assert article.atcl_no == "67890"
    assert article.cortar_no == "1168010100"
    assert article.atcl_nm == "최소필드아파트"
    assert article.rlet_tp_cd == "A02"
    assert article.trad_tp_cd == "B2"
    assert article.flr_info == "3/5"
    assert article.lat == 37.520
    assert article.lng == 126.900

    # 선택적 필드는 None 또는 빈 값
    assert article.prc is None
    assert article.rent_prc is None
    assert article.spc1 == ""
    assert article.spc2 == ""
    assert article.atcl_fetr_desc == ""
    assert article.tag_list == []


@pytest.mark.unit
def test_parse_article_item_jeonse():
    """전세 매물 파싱 확인 (전세는 prc만 있고 rentPrc는 없음)"""
    article_data = {
        "atclNo": "11111",
        "cortarNo": "1150010100",
        "atclNm": "전세매물",
        "rletTpCd": "A01",
        "tradTpCd": "B1",  # 전세
        "prc": 30000,  # 전세 보증금
        "flrInfo": "5/15",
        "spc1": "59",
        "spc2": "42",
        "lat": 37.510,
        "lng": 126.890,
    }

    article = parse_article_item(article_data)

    assert article.trad_tp_cd == "B1"
    assert article.prc == 30000  # 전세 보증금
    assert article.rent_prc is None  # 전세는 월세 없음


@pytest.mark.unit
def test_parse_article_item_wolse():
    """월세 매물 파싱 확인 (월세는 prc와 rentPrc 둘 다 있음)"""
    article_data = {
        "atclNo": "22222",
        "cortarNo": "1150010100",
        "atclNm": "월세매물",
        "rletTpCd": "A01",
        "tradTpCd": "B2",  # 월세
        "prc": 5000,  # 보증금
        "rentPrc": 50,  # 월세
        "flrInfo": "2/10",
        "spc1": "33",
        "spc2": "19",
        "lat": 37.515,
        "lng": 126.895,
    }

    article = parse_article_item(article_data)

    assert article.trad_tp_cd == "B2"
    assert article.prc == 5000  # 보증금
    assert article.rent_prc == 50  # 월세


# =============================================================================
# test_pagination_page_parameter - 페이지 파라미터 처리
# =============================================================================


@pytest.mark.unit
def test_pagination_page_parameter():
    """페이지 파라미터 처리 확인"""
    # 페이지 1
    url_page1 = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        page=1,
    )

    parsed1 = urlparse(url_page1)
    params1 = parse_qs(parsed1.query)

    assert "page" in params1
    assert params1["page"][0] == "1"

    # 페이지 2
    url_page2 = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        page=2,
    )

    parsed2 = urlparse(url_page2)
    params2 = parse_qs(parsed2.query)

    assert params2["page"][0] == "2"


@pytest.mark.unit
def test_pagination_default_page():
    """페이지 파라미터 기본값 확인"""
    url = build_cluster_url(
        zoom=13,
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        # page 파라미터 미지정
    )

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # 기본값은 1이어야 함
    assert "page" in params
    assert params["page"][0] == "1"


@pytest.mark.unit
def test_parse_response_with_page_info():
    """응답의 페이지 정보 파싱 확인"""
    response_data = {
        "code": "200",
        "hasPaidPreSale": False,
        "more": True,
        "z": 13,
        "page": 2,
        "body": [
            {
                "atclNo": "99999",
                "cortarNo": "1150010100",
                "atclNm": "2페이지매물",
                "rletTpCd": "A01",
                "tradTpCd": "A1",
                "prc": 60000,
                "lat": 37.530,
                "lng": 126.910,
            }
        ],
    }

    result = parse_cluster_response(response_data)

    assert result.page == 2
    assert result.more is True  # 다음 페이지 존재
    assert len(result.articles) == 1


# =============================================================================
# test_client_initialization - 클라이언트 초기화
# =============================================================================


@pytest.mark.unit
def test_client_initialization_with_default_values():
    """기본값으로 클라이언트 초기화 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
    )

    assert client.lat == 37.5665
    assert client.lon == 126.9780
    assert client.bottom == 37.5600
    assert client.left == 126.9700
    assert client.top == 37.5730
    assert client.right == 126.9860


@pytest.mark.unit
def test_client_initialization_with_filters():
    """필터와 함께 클라이언트 초기화 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        cortar_no="1150010100",
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        spc_min=30,
        spc_max=150,
        dprc_min=50000,
        dprc_max=200000,
    )

    assert client.cortar_no == "1150010100"
    assert client.rlet_tp_cd == "A01"
    assert client.trad_tp_cd == "A1"
    assert client.spc_min == 30
    assert client.spc_max == 150
    assert client.dprc_min == 50000
    assert client.dprc_max == 200000


@pytest.mark.unit
def test_client_build_url_method():
    """클라이언트의 build_url 메서드 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
        zoom=14,
    )

    url = client.build_url()

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # 클라이언트 설정이 URL에 반영되어야 함
    assert params["z"][0] == "14"
    assert params["lat"][0] == "37.5665"
    assert params["lon"][0] == "126.9780"


# =============================================================================
# test_rate_limiting - Rate Limiting 기능
# =============================================================================


@pytest.mark.unit
def test_fetch_applies_rate_limit():
    """fetch 메서드가 rate limiting을 적용하는지 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
    )

    mock_response = Mock()
    mock_response.json.return_value = {"code": "200", "body": []}
    mock_response.url = "https://m.land.naver.com/cluster/ajax/articleList"
    mock_response.raise_for_status = Mock()

    with (
        patch("crawler.naver_cluster_api.time.sleep") as mock_sleep,
        patch(
            "crawler.naver_cluster_api.requests.get",
            return_value=mock_response,
        ),
    ):
        client.fetch("https://example.com/api")

        # sleep이 호출되어야 함
        mock_sleep.assert_called_once()
        # 딜레이 시간이 MIN과 MAX 사이여야 함
        delay_arg = mock_sleep.call_args[0][0]
        assert client.MIN_DELAY_SECONDS <= delay_arg <= client.MAX_DELAY_SECONDS


@pytest.mark.unit
def test_rate_limit_delay_range():
    """Rate Limiting 딜레이 범위 상수 확인"""
    assert NaverClusterAPIClient.MIN_DELAY_SECONDS == 5.0
    assert NaverClusterAPIClient.MAX_DELAY_SECONDS == 10.0


# =============================================================================
# test_abuse_bypass - Abuse 페이지 우회 기능
# =============================================================================


@pytest.mark.unit
def test_fetch_triggers_playwright_on_abuse_detection():
    """Abuse 페이지 감지 시 Playwright 우회가 호출되는지 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
    )

    # Abuse 리다이렉트 응답 모킹
    abuse_response = Mock()
    abuse_response.url = "https://m.land.naver.com/error/abuse"
    abuse_response.raise_for_status = Mock()

    with (
        patch("crawler.naver_cluster_api.time.sleep"),
        patch(
            "crawler.naver_cluster_api.requests.get",
            return_value=abuse_response,
        ),
        patch.object(
            client, "_fetch_with_playwright", return_value={"code": "200", "body": []}
        ) as mock_playwright,
    ):
        result = client.fetch("https://example.com/api")

        # Playwright 우회가 호출되어야 함
        mock_playwright.assert_called_once_with("https://example.com/api")
        assert result == {"code": "200", "body": []}


@pytest.mark.unit
def test_fetch_triggers_playwright_on_request_exception():
    """요청 예외 발생 시 Playwright 우회가 호출되는지 확인"""
    client = NaverClusterAPIClient(
        lat=37.5665,
        lon=126.9780,
        bottom=37.5600,
        left=126.9700,
        top=37.5730,
        right=126.9860,
    )

    with (
        patch("crawler.naver_cluster_api.time.sleep"),
        patch(
            "crawler.naver_cluster_api.requests.get",
            side_effect=requests.RequestException("Network error"),
        ),
        patch.object(
            client, "_fetch_with_playwright", return_value={"code": "200", "body": []}
        ) as mock_playwright,
    ):
        result = client.fetch("https://example.com/api")

        # Playwright 우회가 호출되어야 함
        mock_playwright.assert_called_once_with("https://example.com/api")
        assert result == {"code": "200", "body": []}


@pytest.mark.unit
def test_abuse_detection_path_constant():
    """Abuse 감지 경로 상수 확인"""
    assert NaverClusterAPIClient.ABUSE_DETECTION_PATH == "/error/abuse"


@pytest.mark.unit
def test_default_user_agent_constant():
    """기본 User-Agent 상수 확인"""
    expected = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    )
    assert NaverClusterAPIClient.DEFAULT_USER_AGENT == expected

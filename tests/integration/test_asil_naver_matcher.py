"""AsilNaverMatcher 통합 테스트

ASIL-Naver 아파트 매칭 로직의 통합 테스트입니다.
실제 매칭 로직을 사용하며, fixtures로 테스트 데이터를 제공합니다.
"""

import pytest

from crawler.dto.asil_offer_detail import AsilOfferDetailDTO
from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.dto.naver_listing import NaverAptDTO
from crawler.matching.asil_naver_matcher import AsilNaverMatcher
from crawler.matching.dto import MatchMethod, MatchResultDTO

# =============================================================================
# Helper Functions
# =============================================================================


def create_asil_detail(
    mm_uid: str = "test123",
    BLDNM: str = "테스트아파트",  # noqa: N803
    naver_uid: str = "",
    MAP_X: str = "",  # noqa: N803
    MAP_Y: str = "",  # noqa: N803
) -> AsilOfferDetailDTO:
    """테스트용 AsilOfferDetailDTO 생성 헬퍼 함수"""
    return AsilOfferDetailDTO(
        mm_uid=mm_uid,
        RLSTTYPE_CD="A01",
        RLSTTYPE_NM="아파트",
        DEALTYPE_CD="B01",
        DEALTYPE_NM="전세",
        BLDNM=BLDNM,
        naver_uid=naver_uid,
        MAP_X=MAP_X,
        MAP_Y=MAP_Y,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def yeoksam_xi_asil():
    """역삼자이 ASIL DTO fixture"""
    return create_asil_detail(
        mm_uid="asil001",
        BLDNM="역삼자이",
        naver_uid="2602100872",
        MAP_X="127.036425",
        MAP_Y="37.500581",
    )


@pytest.fixture
def yeoksam_xi_candidates():
    """역삼자이 Naver 후보 fixture"""
    return [
        NaverAptDTO(
            complex_no="2602100872",
            complex_name="역삼자이",
            latitude=37.500581,
            longitude=127.036425,
            build_year=2007,
            household_count=586,
        ),
        NaverAptDTO(
            complex_no="2603000001",
            complex_name="역삼자이2차",
            latitude=37.501000,
            longitude=127.036500,
            build_year=2010,
            household_count=400,
        ),
    ]


@pytest.fixture
def ramean_gangnam_asil():
    """래미안강남 ASIL DTO fixture"""
    return create_asil_detail(
        mm_uid="asil002",
        BLDNM="래미안강남",
        naver_uid="",  # naver_uid 없음
        MAP_X="127.0473",
        MAP_Y="37.5172",
    )


@pytest.fixture
def ramean_gangnam_candidates():
    """래미안강남 Naver 후보 fixture"""
    return [
        NaverAptDTO(
            complex_no="111111",
            complex_name="래미안강남",
            latitude=37.5172,
            longitude=127.0473,
        ),
    ]


@pytest.fixture
def article_item_candidates():
    """NaverArticleItemDTO 후보 fixture"""
    return [
        NaverArticleItemDTO(
            atcl_no="12345",
            cortar_no="1168010300",
            atcl_nm="래미안강남",
            atcl_stat_cd="R01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
            prc=250000,
            lat=37.5172,
            lng=127.0473,
        ),
        NaverArticleItemDTO(
            atcl_no="12346",
            cortar_no="1168010300",
            atcl_nm="래미안강남",
            atcl_stat_cd="R01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="B1",
            trad_tp_nm="전세",
            prc=180000,
            lat=37.5173,
            lng=127.0474,
        ),
    ]


@pytest.fixture
def mixed_candidates():
    """NaverAptDTO와 NaverArticleItemDTO 혼합 후보 fixture"""
    return [
        NaverAptDTO(
            complex_no="far_apt",
            complex_name="먼아파트",
            latitude=37.5000,
            longitude=127.0000,
        ),
        NaverArticleItemDTO(
            atcl_no="close_article",
            cortar_no="1168010300",
            atcl_nm="래미안강남",
            atcl_stat_cd="R01",
            rlet_tp_cd="A01",
            rlet_tp_nm="아파트",
            trad_tp_cd="A1",
            trad_tp_nm="매매",
            prc=250000,
            lat=37.5173,
            lng=127.0474,
        ),
    ]


# =============================================================================
# Test Direct ID Matching
# =============================================================================


@pytest.mark.integration
class TestDirectIdMatching:
    """Direct naver_uid 매칭 통합 테스트"""

    def test_direct_id_with_valid_naver_uid(self, yeoksam_xi_asil):
        """유효한 naver_uid로 직접 매칭 성공"""
        result = AsilNaverMatcher.match_by_direct_id(yeoksam_xi_asil)

        assert result is not None
        assert isinstance(result, MatchResultDTO)
        assert result.asil_apt_code == "asil001"
        assert result.naver_apt_code == "2602100872"
        assert result.naver_apt_name == "역삼자이"
        assert result.confidence == 1.0
        assert result.method == MatchMethod.DIRECT_ID
        assert result.distance_m is None

    def test_direct_id_with_empty_naver_uid(self, ramean_gangnam_asil):
        """빈 naver_uid로 매칭 실패"""
        result = AsilNaverMatcher.match_by_direct_id(ramean_gangnam_asil)
        assert result is None

    def test_direct_id_with_whitespace_naver_uid(self):
        """공백만 있는 naver_uid로 매칭 실패"""
        asil = create_asil_detail(naver_uid="   ")
        result = AsilNaverMatcher.match_by_direct_id(asil)
        assert result is None


# =============================================================================
# Test Coordinate Matching
# =============================================================================


@pytest.mark.integration
class TestCoordinateMatching:
    """좌표 기반 매칭 통합 테스트"""

    def test_exact_coordinate_match(self, ramean_gangnam_asil, ramean_gangnam_candidates):
        """정확한 좌표 일치 시 최고 신뢰도"""
        result = AsilNaverMatcher.match_by_coordinate(
            ramean_gangnam_asil, ramean_gangnam_candidates
        )

        assert result is not None
        assert result.naver_apt_code == "111111"
        assert result.naver_apt_name == "래미안강남"
        assert result.confidence == 1.0
        assert result.distance_m == 0
        assert result.method == MatchMethod.COORDINATE

    def test_nearby_coordinate_match(self):
        """근처 좌표 매칭 시 높은 신뢰도"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.036425", MAP_Y="37.500581")

        candidates = [
            NaverAptDTO(
                complex_no="nearby",
                complex_name="근처아파트",
                latitude=37.501000,
                longitude=127.036500,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, candidates)

        assert result is not None
        assert result.distance_m < 100
        assert result.confidence >= 0.7

    def test_far_coordinate_no_match(self):
        """먼 좌표는 매칭 실패"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.036425", MAP_Y="37.500581")

        candidates = [
            NaverAptDTO(
                complex_no="far",
                complex_name="먼아파트",
                latitude=37.530000,
                longitude=127.070000,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
        assert result is None

    def test_selects_closest_candidate(self):
        """가장 가까운 후보 선택"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.036425", MAP_Y="37.500581")

        candidates = [
            NaverAptDTO(
                complex_no="far",
                complex_name="먼아파트",
                latitude=37.510000,
                longitude=127.050000,
            ),
            NaverAptDTO(
                complex_no="close",
                complex_name="가까운아파트",
                latitude=37.500600,
                longitude=127.036500,
            ),
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
        assert result.naver_apt_code == "close"

    def test_empty_candidates_returns_none(self, ramean_gangnam_asil):
        """빈 후보 목록 시 None 반환"""
        result = AsilNaverMatcher.match_by_coordinate(ramean_gangnam_asil, [])
        assert result is None

    def test_missing_asil_coordinates(self):
        """ASIL 좌표 없음 시 None 반환"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="", MAP_Y="")

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="테스트아파트",
                latitude=37.500581,
                longitude=127.036425,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
        assert result is None

    def test_confidence_calculation_by_distance(self):
        """거리별 신뢰도 계산 검증"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.036425", MAP_Y="37.500581")

        # 다양한 거리의 후보들 (실제 좌표로 거리 계산)
        # ASIL 좌표: (37.500581, 127.036425)
        test_cases = [
            # (위도, 경도, 예상 최소 신뢰도, 설명)
            (37.500581, 127.036425, 1.0, "0m 정확히 일치"),
            (37.500800, 127.036425, 0.7, "약 24m - 높은 신뢰도"),
            (37.501000, 127.036500, 0.5, "약 50m - 중간 신뢰도"),
            (37.501500, 127.036500, 0.5, "약 100m 이내 - 최소 신뢰도"),
        ]

        for lat, lng, expected_min_confidence, desc in test_cases:
            candidates = [
                NaverAptDTO(
                    complex_no=f"test_{lat}_{lng}",
                    complex_name="테스트",
                    latitude=lat,
                    longitude=lng,
                )
            ]

            result = AsilNaverMatcher.match_by_coordinate(asil, candidates)

            # 100m 이내만 매칭되어야 함
            if result is not None:
                msg = (
                    f"{desc}: 신뢰도 부족 "
                    f"(거리: {result.distance_m:.1f}m, "
                    f"신뢰도: {result.confidence:.2f})"
                )
                assert result.confidence >= expected_min_confidence - 0.1, msg
                assert result.distance_m <= 100, (
                    f"{desc}: 거리가 100m 초과 (거리: {result.distance_m:.1f}m)"
                )
            else:
                # 100m 이상인 경우 매칭 실패해야 함
                distance = AsilNaverMatcher.haversine((37.500581, 127.036425), (lat, lng))
                assert distance > 100, f"{desc}: 거리 {distance:.1f}m가 100m 이하임에도 매칭 실패"


# =============================================================================
# Test Fuzzy Name Matching
# =============================================================================


@pytest.mark.integration
class TestFuzzyNameMatching:
    """퍼지 이름 매칭 통합 테스트"""

    def test_exact_name_match(self):
        """정확한 이름 일치 시 최고 신뢰도"""
        asil = create_asil_detail(BLDNM="역삼자이")

        candidates = [NaverAptDTO(complex_no="123", complex_name="역삼자이")]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)

        assert result is not None
        assert result.confidence == 1.0
        assert result.method == MatchMethod.FUZZY_NAME

    def test_similar_name_match(self):
        """유사한 이름 매칭 (공백 차이)"""
        asil = create_asil_detail(BLDNM="역삼자이")

        candidates = [NaverAptDTO(complex_no="123", complex_name="역삼 자이")]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)

        assert result is not None
        assert result.confidence >= 0.8

    def test_selects_most_similar_name(self):
        """가장 유사한 이름 선택"""
        asil = create_asil_detail(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(complex_no="low", complex_name="완전다른이름"),
            NaverAptDTO(complex_no="high", complex_name="역삼자이2차"),
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)
        assert result.naver_apt_code == "high"

    def test_low_similarity_no_match(self):
        """낮은 유사도 시 매칭 실패"""
        asil = create_asil_detail(BLDNM="역삼자이")

        candidates = [NaverAptDTO(complex_no="123", complex_name="완전다른아파트")]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)
        assert result is None

    def test_empty_candidates_returns_none(self):
        """빈 후보 목록 시 None 반환"""
        asil = create_asil_detail(BLDNM="테스트아파트")
        result = AsilNaverMatcher.match_by_fuzzy_name(asil, [])
        assert result is None

    def test_brand_name_matching(self):
        """브랜드명 기반 매칭"""
        asil = create_asil_detail(BLDNM="역삼자이")

        candidates = [NaverAptDTO(complex_no="123", complex_name="역삼 자이2차")]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)
        assert result is not None
        assert result.confidence >= 0.5


# =============================================================================
# Test Mixed DTO Types
# =============================================================================


@pytest.mark.integration
class TestMixedDtoTypes:
    """혼합 DTO 타입 매칭 통합 테스트"""

    def test_coordinate_match_with_article_item(self, ramean_gangnam_asil, article_item_candidates):
        """NaverArticleItemDTO 좌표 매칭"""
        result = AsilNaverMatcher.match_by_coordinate(ramean_gangnam_asil, article_item_candidates)

        assert result is not None
        assert result.naver_apt_code == "12345"  # atcl_no
        assert result.naver_apt_name == "래미안강남"
        assert result.confidence == 1.0
        assert result.distance_m == 0

    def test_fuzzy_name_match_with_article_item(self, article_item_candidates):
        """NaverArticleItemDTO 퍼지 이름 매칭"""
        asil = create_asil_detail(BLDNM="래미안강남")

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, article_item_candidates)

        assert result is not None
        assert result.naver_apt_code == "12345"
        assert result.confidence >= 0.8

    def test_mixed_candidates_selects_closest(self, ramean_gangnam_asil, mixed_candidates):
        """혼합 타입 후보 중 가장 가까운 선택"""
        result = AsilNaverMatcher.match_by_coordinate(ramean_gangnam_asil, mixed_candidates)

        assert result is not None
        assert result.naver_apt_code == "close_article"
        assert result.distance_m < 50

    def test_article_item_without_coordinates_skipped(self):
        """좌표 없는 NaverArticleItemDTO 건너뜀"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.0473", MAP_Y="37.5172")

        candidates = [
            NaverArticleItemDTO(
                atcl_no="12345",
                cortar_no="1168010300",
                atcl_nm="테스트아파트",
                atcl_stat_cd="R01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                prc=250000,
                lat=None,
                lng=None,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
        assert result is None


# =============================================================================
# Test Priority Order
# =============================================================================


@pytest.mark.integration
class TestMatchingPriorityOrder:
    """매칭 우선순위 통합 테스트

    우선순위: DIRECT_ID > COORDINATE > FUZZY_NAME
    """

    def test_direct_id_has_highest_priority(self, yeoksam_xi_asil):
        """naver_uid가 있으면 DIRECT_ID가 최우선"""
        # naver_uid가 있으므로 직접 매칭
        result = AsilNaverMatcher.match_by_direct_id(yeoksam_xi_asil)

        assert result is not None
        assert result.method == MatchMethod.DIRECT_ID
        assert result.confidence == 1.0

    def test_coordinate_fallback_when_no_direct_id(
        self, ramean_gangnam_asil, ramean_gangnam_candidates
    ):
        """naver_uid 없으면 좌표 매칭 시도"""
        # naver_uid 없음
        direct_result = AsilNaverMatcher.match_by_direct_id(ramean_gangnam_asil)
        assert direct_result is None

        # 좌표 매칭 성공
        coord_result = AsilNaverMatcher.match_by_coordinate(
            ramean_gangnam_asil, ramean_gangnam_candidates
        )
        assert coord_result is not None
        assert coord_result.method == MatchMethod.COORDINATE

    def test_fuzzy_name_fallback_when_no_coordinates(self):
        """좌표 없으면 퍼지 이름 매칭 시도"""
        asil = create_asil_detail(BLDNM="역삼자이", MAP_X="", MAP_Y="")

        candidates = [NaverAptDTO(complex_no="123", complex_name="역삼자이")]

        # 좌표 매칭 실패
        coord_result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
        assert coord_result is None

        # 퍼지 이름 매칭 성공
        fuzzy_result = AsilNaverMatcher.match_by_fuzzy_name(asil, candidates)
        assert fuzzy_result is not None
        assert fuzzy_result.method == MatchMethod.FUZZY_NAME


# =============================================================================
# Test Edge Cases
# =============================================================================


@pytest.mark.integration
class TestEdgeCases:
    """엣지 케이스 통합 테스트"""

    def test_haversine_distance_calculation(self):
        """Haversine 거리 계산 정확도 검증"""
        # 강남역-역삼역 약 830m
        gangnam = (37.497984, 127.027614)
        yeoksam = (37.500581, 127.036425)

        distance = AsilNaverMatcher.haversine(gangnam, yeoksam)
        assert 810 <= distance <= 850

    def test_same_coordinates_zero_distance(self):
        """동일 좌표 시 거리 0"""
        coord = (37.5, 127.0)
        distance = AsilNaverMatcher.haversine(coord, coord)
        assert distance == 0

    def test_name_normalization(self):
        """이름 정규화 기능 검증"""
        test_cases = [
            ("역삼 자이", "역삼자이"),
            ("래미안(강남)", "래미안강남"),
            ("힐스테이트~역삼", "힐스테이트역삼"),
            ("테스트,아파트", "테스트아파트"),
        ]

        for original, expected in test_cases:
            result = AsilNaverMatcher.normalize_name(original)
            assert result == expected

    def test_name_similarity_score_range(self):
        """이름 유사도 점수 범위 검증"""
        # 완전 일치
        score1 = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이")
        assert score1 == 1.0

        # 전혀 다름
        score2 = AsilNaverMatcher.name_similarity("역삼자이", "완전다른이름")
        assert 0.0 <= score2 < 0.5

        # 부분 일치
        score3 = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이2차")
        assert 0.5 <= score3 < 1.0

    def test_confidence_always_between_0_and_1(self):
        """신뢰도 항상 0.0-1.0 범위"""
        asil = create_asil_detail(BLDNM="테스트", MAP_X="127.0", MAP_Y="37.5")

        # 다양한 거리 테스트
        for lat_offset in [0.0001, 0.0005, 0.001]:
            candidates = [
                NaverAptDTO(
                    complex_no="test",
                    complex_name="테스트",
                    latitude=37.5 + lat_offset,
                    longitude=127.0,
                )
            ]

            result = AsilNaverMatcher.match_by_coordinate(asil, candidates)
            if result:
                assert 0.0 <= result.confidence <= 1.0


# =============================================================================
# Test No Match Scenarios
# =============================================================================


@pytest.mark.integration
class TestNoMatchScenarios:
    """매칭 실패 시나리오 통합 테스트"""

    def test_no_match_empty_candidates(self):
        """빈 후보 목록 시 모든 매칭 실패"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.0", MAP_Y="37.5", naver_uid="")

        assert AsilNaverMatcher.match_by_direct_id(asil) is None
        assert AsilNaverMatcher.match_by_coordinate(asil, []) is None
        assert AsilNaverMatcher.match_by_fuzzy_name(asil, []) is None

    def test_no_match_far_coordinates(self):
        """모든 후보가 너무 멀 때 좌표 매칭 실패"""
        asil = create_asil_detail(BLDNM="테스트아파트", MAP_X="127.0", MAP_Y="37.5")

        # 200m+ 떨어진 후보들
        far_candidates = [
            NaverAptDTO(
                complex_no=f"far{i}",
                complex_name=f"먼아파트{i}",
                latitude=37.52,
                longitude=127.02,
            )
            for i in range(3)
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil, far_candidates)
        assert result is None

    def test_no_match_low_similarity(self):
        """모든 후보의 유사도가 낮을 때 퍼지 매칭 실패"""
        asil = create_asil_detail(BLDNM="역삼자이")

        low_similarity_candidates = [
            NaverAptDTO(complex_no=str(i), complex_name=f"완전다른이름{i}") for i in range(3)
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil, low_similarity_candidates)
        assert result is None

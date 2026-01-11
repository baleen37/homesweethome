"""AsilNaverMatcher 단위 테스트"""

from crawler.dto.asil_offer_detail import AsilOfferDetailDTO
from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.dto.naver_listing import NaverAptDTO
from crawler.matching.asil_naver_matcher import AsilNaverMatcher
from crawler.matching.dto import MatchMethod, MatchResultDTO


def create_asil_dto(
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


class TestHaversineDistance:
    """Haversine 거리 계산 테스트"""

    def test_distance_between_seoul_landmarks(self):
        """서울 랜드마크 간 거리 계산"""
        # 강남역 역삼역 사이 거리 (약 830m)
        gangnam_station = (37.497984, 127.027614)
        yeoksam_station = (37.500581, 127.036425)

        distance = AsilNaverMatcher.haversine(gangnam_station, yeoksam_station)

        # 약 830m - 오차 범위 20m 허용
        assert 810 <= distance <= 850

    def test_distance_same_coordinates(self):
        """동일 좌표 간 거리는 0이어야 함"""
        coord = (37.5, 127.0)
        distance = AsilNaverMatcher.haversine(coord, coord)
        assert distance == 0

    def test_distance_calculates_in_meters(self):
        """거리가 미터 단위로 계산되어야 함"""
        # 위도 1도는 약 111km
        coord1 = (37.5, 127.0)
        coord2 = (38.5, 127.0)  # 위도 1도 차이

        distance = AsilNaverMatcher.haversine(coord1, coord2)

        # 약 111km = 111,000m
        assert 110000 <= distance <= 112000

    def test_distance_longitude_difference(self):
        """경도 차이에 따른 거리 계산 (서울 위도)"""
        # 서울 위도(37.5도)에서 경도 1도는 약 88km
        coord1 = (37.5, 127.0)
        coord2 = (37.5, 128.0)  # 경도 1도 차이

        distance = AsilNaverMatcher.haversine(coord1, coord2)

        # 약 88km = 88,000m
        assert 87000 <= distance <= 89000


class TestNormalizeApartmentName:
    """아파트 이름 정규화 테스트"""

    def test_remove_spaces(self):
        """공백 제거"""
        assert AsilNaverMatcher.normalize_name("역삼 자이") == "역삼자이"
        assert AsilNaverMatcher.normalize_name("래미안  원베일리") == "래미안원베일리"

    def test_remove_special_characters(self):
        """특수 문자 제거"""
        assert AsilNaverMatcher.normalize_name("래미안(원베일리)") == "래미안원베일리"
        assert AsilNaverMatcher.normalize_name("힐스테이트~역삼") == "힐스테이트역삼"

    def test_common_brand_patterns(self):
        """공통 브랜드 패턴 처리"""
        # 자이
        assert "자이" in AsilNaverMatcher.normalize_name("역삼자이")
        # 트라이팰
        assert AsilNaverMatcher.normalize_name("트라이팰") == "트라이팰"
        # 힐스테이트
        assert AsilNaverMatcher.normalize_name("힐스테이트") == "힐스테이트"
        # 래미안
        assert AsilNaverMatcher.normalize_name("래미안") == "래미안"

    def test_case_insensitive(self):
        """대소문자 구분 없이 처리"""
        result1 = AsilNaverMatcher.normalize_name("역삼자이")
        result2 = AsilNaverMatcher.normalize_name("역삼자이")
        assert result1 == result2

    def test_empty_string(self):
        """빈 문자열 처리"""
        assert AsilNaverMatcher.normalize_name("") == ""

    def test_remove_parentheses_content(self):
        """괄호 내용 제거"""
        assert AsilNaverMatcher.normalize_name("아파트(재건축)") == "아파트재건축"


class TestNameSimilarityScore:
    """이름 유사도 점수 테스트"""

    def test_exact_match(self):
        """정확히 일치하면 1.0을 반환해야 함"""
        score = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이")
        assert score == 1.0

    def test_no_similarity(self):
        """전혀 다른 이름은 0에 가까운 점수를 반환해야 함"""
        score = AsilNaverMatcher.name_similarity("역삼자이", "래미안원베일리")
        assert score < 0.3

    def test_partial_match(self):
        """부분 일치는 중간 점수를 반환해야 함"""
        score = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이2차")
        assert 0.5 <= score <= 0.9

    def test_normalized_comparison(self):
        """정규화된 이름으로 비교해야 함"""
        # 공백 차이만 있는 경우
        score1 = AsilNaverMatcher.name_similarity("역삼 자이", "역삼자이")
        score2 = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이")
        # 유사해야 함
        assert abs(score1 - score2) < 0.1

    def test_fuzzy_brand_match(self):
        """브랜드명 포함 유사도"""
        # 같은 브랜드, 다른 지역
        score = AsilNaverMatcher.name_similarity("역삼자이", "강남자이")
        assert 0.5 <= score <= 0.8

    def test_score_range(self):
        """점수는 항상 0.0-1.0 범위여야 함"""
        score1 = AsilNaverMatcher.name_similarity("가", "나")
        score2 = AsilNaverMatcher.name_similarity("역삼자이", "역삼자이역삼자이")
        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0


class TestMatchByDirectId:
    """Direct naver_uid 매칭 테스트"""

    def test_match_with_naver_uid(self):
        """naver_uid가 있으면 최고 신뢰도로 매칭되어야 함"""
        asil_detail = create_asil_dto(
            BLDNM="역삼자이",
            naver_uid="2602100872",
        )

        result = AsilNaverMatcher.match_by_direct_id(asil_detail)

        assert isinstance(result, MatchResultDTO)
        assert result.asil_apt_code == "test123"
        assert result.naver_apt_code == "2602100872"
        assert result.confidence == 1.0
        assert result.method == MatchMethod.DIRECT_ID

    def test_no_match_without_naver_uid(self):
        """naver_uid가 없으면 매칭 실패해야 함"""
        asil_detail = create_asil_dto(
            BLDNM="역삼자이",
            naver_uid="",  # 빈 naver_uid
        )

        result = AsilNaverMatcher.match_by_direct_id(asil_detail)

        assert result is None

    def test_whitespace_naver_uid(self):
        """공백만 있는 naver_uid는 매칭 실패해야 함"""
        asil_detail = create_asil_dto(
            BLDNM="역삼자이",
            naver_uid="   ",  # 공백만
        )

        result = AsilNaverMatcher.match_by_direct_id(asil_detail)

        assert result is None


class TestMatchByCoordinate:
    """좌표 기반 매칭 테스트"""

    def test_exact_coordinate_match(self):
        """정확한 좌표 일치는 최고 신뢰도"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="127.036425",
            MAP_Y="37.500581",
        )

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼자이",
                latitude=37.500581,
                longitude=127.036425,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "naver123"
        assert result.confidence == 1.0
        assert result.distance_m == 0
        assert result.method == MatchMethod.COORDINATE

    def test_nearby_coordinate_match(self):
        """가까운 좌표는 높은 신뢰도로 매칭"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="127.036425",
            MAP_Y="37.500581",
        )

        # 약 50m 떨어진 위치
        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼자이",
                latitude=37.501000,  # 약 50m 차이
                longitude=127.036500,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "naver123"
        assert result.confidence >= 0.7  # 50m 거리는 0.76 정도의 신뢰도
        assert result.distance_m < 100

    def test_far_coordinate_no_match(self):
        """먼 좌표는 매칭 실패"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="127.036425",
            MAP_Y="37.500581",
        )

        # 약 3km 떨어진 위치
        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="다른아파트",
                latitude=37.530000,
                longitude=127.070000,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is None

    def test_selects_closest_candidate(self):
        """가장 가까운 후보를 선택해야 함"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="127.036425",
            MAP_Y="37.500581",
        )

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

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result.naver_apt_code == "close"

    def test_empty_candidates(self):
        """후보가 없으면 매칭 실패"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="127.036425",
            MAP_Y="37.500581",
        )

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, [])

        assert result is None

    def test_missing_coordinates(self):
        """좌표가 없으면 매칭 실패"""
        asil_apt = create_asil_dto(
            BLDNM="역삼자이",
            MAP_X="",  # 빈 좌표
            MAP_Y="",
        )

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼자이",
                latitude=37.500581,
                longitude=127.036425,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is None


class TestMatchByFuzzyName:
    """퍼지 이름 매칭 테스트"""

    def test_exact_name_match(self):
        """정확한 이름 일치는 최고 신뢰도"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼자이",
            )
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "naver123"
        assert result.confidence == 1.0
        assert result.method == MatchMethod.FUZZY_NAME

    def test_similar_name_match(self):
        """유사한 이름은 높은 신뢰도로 매칭"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼 자이",  # 공백 차이
            )
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result is not None
        assert result.confidence >= 0.8

    def test_selects_most_similar(self):
        """가장 유사한 이름을 선택해야 함"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(complex_no="low", complex_name="완전다른이름"),
            NaverAptDTO(complex_no="high", complex_name="역삼자이2차"),
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result.naver_apt_code == "high"

    def test_low_similarity_no_match(self):
        """낮은 유사도는 매칭 실패"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="완전다른아파트",
            )
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result is None

    def test_empty_candidates(self):
        """후보가 없으면 매칭 실패"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, [])

        assert result is None

    def test_brand_name_matching(self):
        """브랜드명 기반 매칭"""
        asil_apt = create_asil_dto(BLDNM="역삼자이")

        candidates = [
            NaverAptDTO(
                complex_no="naver123",
                complex_name="역삼 자이2차",  # 브랜드명 + 지역명 + 숫자
            )
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result is not None
        assert result.confidence >= 0.5


class TestMatchWithNaverArticleItem:
    """NaverArticleItemDTO (Cluster API) 매칭 테스트"""

    def test_exact_coordinate_match_with_article_item(self):
        """NaverArticleItemDTO로 정확한 좌표 매칭"""
        asil_apt = create_asil_dto(
            BLDNM="래미안강남",
            MAP_X="127.0473",
            MAP_Y="37.5172",
        )

        # Cluster API 기반 매물
        candidates = [
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
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "12345"  # atcl_no 사용
        assert result.naver_apt_name == "래미안강남"
        assert result.confidence == 1.0
        assert result.distance_m == 0
        assert result.method == MatchMethod.COORDINATE

    def test_nearby_coordinate_match_with_article_item(self):
        """NaverArticleItemDTO로 근처 좌표 매칭"""
        asil_apt = create_asil_dto(
            BLDNM="래미안강남",
            MAP_X="127.0473",
            MAP_Y="37.5172",
        )

        # 약 50m 떨어진 위치
        candidates = [
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
                lat=37.5176,  # 약 50m 차이
                lng=127.0474,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "12345"
        assert result.confidence >= 0.7
        assert result.distance_m < 100

    def test_fuzzy_name_match_with_article_item(self):
        """NaverArticleItemDTO로 퍼지 이름 매칭"""
        asil_apt = create_asil_dto(BLDNM="래미안강남")

        candidates = [
            NaverArticleItemDTO(
                atcl_no="12345",
                cortar_no="1168010300",
                atcl_nm="래미안 강남",  # 공백 차이
                atcl_stat_cd="R01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                prc=250000,
            )
        ]

        result = AsilNaverMatcher.match_by_fuzzy_name(asil_apt, candidates)

        assert result is not None
        assert result.naver_apt_code == "12345"
        assert result.confidence >= 0.8
        assert result.method == MatchMethod.FUZZY_NAME

    def test_mixed_dto_types_in_candidates(self):
        """NaverAptDTO와 NaverArticleItemDTO 혼합 후보 목록"""
        asil_apt = create_asil_dto(
            BLDNM="래미안강남",
            MAP_X="127.0473",
            MAP_Y="37.5172",
        )

        # 두 타입 혼합
        candidates = [
            NaverAptDTO(
                complex_no="111",
                complex_name="먼아파트",
                latitude=37.5000,
                longitude=127.0000,
            ),
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
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        # 가장 가까운 NaverArticleItemDTO가 선택되어야 함
        assert result is not None
        assert result.naver_apt_code == "12345"
        assert result.naver_apt_name == "래미안강남"

    def test_article_item_without_coordinates(self):
        """좌표가 없는 NaverArticleItemDTO는 건너뛰어야 함"""
        asil_apt = create_asil_dto(
            BLDNM="래미안강남",
            MAP_X="127.0473",
            MAP_Y="37.5172",
        )

        candidates = [
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
                lat=None,  # 좌표 없음
                lng=None,
            )
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        assert result is None

    def test_selects_closest_among_mixed_types(self):
        """혼합 타입 중 가장 가까운 후보 선택"""
        asil_apt = create_asil_dto(
            BLDNM="래미안강남",
            MAP_X="127.0473",
            MAP_Y="37.5172",
        )

        candidates = [
            NaverAptDTO(
                complex_no="far_apt",
                complex_name="먼아파트",
                latitude=37.5000,
                longitude=127.0000,
            ),
            NaverArticleItemDTO(
                atcl_no="close_article",
                cortar_no="1168010300",
                atcl_nm="가까운매물",
                atcl_stat_cd="R01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                prc=250000,
                lat=37.5173,  # 약 15m 차이
                lng=127.0474,
            ),
            NaverArticleItemDTO(
                atcl_no="medium_article",
                cortar_no="1168010300",
                atcl_nm="중간매물",
                atcl_stat_cd="R01",
                rlet_tp_cd="A01",
                rlet_tp_nm="아파트",
                trad_tp_cd="A1",
                trad_tp_nm="매매",
                prc=200000,
                lat=37.5150,  # 약 250m 차이
                lng=127.0450,
            ),
        ]

        result = AsilNaverMatcher.match_by_coordinate(asil_apt, candidates)

        # 가장 가까운 close_article이 선택되어야 함
        assert result is not None
        assert result.naver_apt_code == "close_article"
        assert result.distance_m < 50

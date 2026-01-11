"""ASIL-Naver 아파트 매칭 로직"""

import math
from typing import TYPE_CHECKING

from crawler.dto.asil_offer_detail import AsilOfferDetailDTO
from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.dto.naver_listing import NaverAptDTO
from crawler.matching.dto import MatchMethod, MatchResultDTO

if TYPE_CHECKING:
    from collections.abc import Sequence

# 두 DTO 타입 모두 지원하는 Union 타입
NaverAptType = NaverAptDTO | NaverArticleItemDTO


class AsilNaverMatcher:
    """ASIL과 Naver 아파트 정보를 매칭하는 클래스"""

    # 좌표 매칭: 최대 허용 거리 (미터)
    MAX_COORDINATE_DISTANCE_M = 100

    # 퍼지 이름 매칭: 최소 신뢰도 임계값
    MIN_FUZZY_CONFIDENCE = 0.5

    @staticmethod
    def haversine(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
        """
        두 좌표 사이의 Haversine 거리를 계산 (미터 단위)

        Args:
            coord1: (위도, 경도) 튜플
            coord2: (위도, 경도) 튜플

        Returns:
            거리 (미터)
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # 지구 반경 (미터)
        earth_radius_m = 6371000

        # 라디안으로 변환
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Haversine 공식
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return earth_radius_m * c

    @staticmethod
    def _extract_apt_info(naver_apt: NaverAptType) -> tuple[str, float | None, float | None]:
        """
        DTO 타입에 따라 적절한 필드 추출

        Args:
            naver_apt: NaverAptDTO 또는 NaverArticleItemDTO

        Returns:
            (단지명, 위도, 경도) 튜플
        """
        if isinstance(naver_apt, NaverArticleItemDTO):
            return (naver_apt.atcl_nm, naver_apt.lat, naver_apt.lng)
        else:
            return (naver_apt.complex_name, naver_apt.latitude, naver_apt.longitude)

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        아파트 이름을 정규화 (공백, 특수문자 제거)

        Args:
            name: 원본 이름

        Returns:
            정규화된 이름
        """
        # 공백 제거
        name = name.replace(" ", "")

        # 특수 문자 제거
        name = name.replace("(", "").replace(")", "")
        name = name.replace("~", "").replace("-", "")
        name = name.replace(".", "").replace(",", "")

        return name

    @staticmethod
    def name_similarity(s1: str, s2: str) -> float:
        """
        두 이름의 유사도를 계산 (Levenshtein 거리 기반)

        Args:
            s1: 첫 번째 문자열
            s2: 두 번째 문자열

        Returns:
            유사도 점수 (0.0-1.0)
        """
        # 정규화
        s1_norm = AsilNaverMatcher.normalize_name(s1)
        s2_norm = AsilNaverMatcher.normalize_name(s2)

        # Levenshtein 거리 계산
        m = len(s1_norm)
        n = len(s2_norm)

        # DP 테이블 초기화
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # 첫 행/열 초기화
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # DP 테이블 채우기
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1_norm[i - 1] == s2_norm[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],  # 삭제
                        dp[i][j - 1],  # 삽입
                        dp[i - 1][j - 1],  # 치환
                    )

        # 유사도 계산 (1 - 정규화된 거리)
        max_len = max(m, n)
        if max_len == 0:
            return 1.0 if m == n else 0.0

        distance = dp[m][n]
        similarity = 1.0 - (distance / max_len)

        return similarity

    @staticmethod
    def match_by_direct_id(
        asil_detail: AsilOfferDetailDTO,
    ) -> MatchResultDTO | None:
        """
        ASIL의 naver_uid로 직접 매칭

        Args:
            asil_detail: ASIL 매물 상세 정보

        Returns:
            매칭 결과 또는 None (매칭 실패 시)
        """
        naver_uid = asil_detail.naver_uid

        if not naver_uid or not naver_uid.strip():
            return None

        return MatchResultDTO(
            asil_apt_code=asil_detail.mm_uid,
            asil_apt_name=asil_detail.BLDNM,
            naver_apt_code=naver_uid,
            naver_apt_name=asil_detail.BLDNM,  # ASIL의 이름 사용
            confidence=1.0,
            method=MatchMethod.DIRECT_ID,
            distance_m=None,
        )

    @staticmethod
    def match_by_coordinate(
        asil_apt: AsilOfferDetailDTO,
        candidates: "Sequence[NaverAptType]",
    ) -> MatchResultDTO | None:
        """
        좌표 기반 매칭

        Args:
            asil_apt: ASIL 아파트 정보
            candidates: Naver 아파트 후보 목록 (NaverAptDTO 또는 NaverArticleItemDTO)

        Returns:
            매칭 결과 또는 None (매칭 실패 시)
        """
        if not candidates:
            return None

        # ASIL 좌표 파싱
        try:
            asil_lat = float(asil_apt.MAP_Y)
            asil_lon = float(asil_apt.MAP_X)
        except (ValueError, TypeError):
            return None

        asil_coord = (asil_lat, asil_lon)

        # 가장 가까운 후보 찾기
        best_candidate = None
        best_distance = float("inf")

        for candidate in candidates:
            # DTO 타입에 따라 좌표 추출
            _, cand_lat, cand_lon = AsilNaverMatcher._extract_apt_info(candidate)

            if cand_lat is None or cand_lon is None:
                continue

            cand_coord = (cand_lat, cand_lon)
            distance = AsilNaverMatcher.haversine(asil_coord, cand_coord)

            if distance < best_distance:
                best_distance = distance
                best_candidate = candidate

        # 최대 거리 체크
        if best_candidate is None or best_distance > AsilNaverMatcher.MAX_COORDINATE_DISTANCE_M:
            return None

        # 신뢰도 계산 (거리가 가까울수록 높음)
        # 0m = 1.0, 100m = 0.5 이상이 되도록 조정
        if best_distance == 0:
            confidence = 1.0
        else:
            confidence = max(
                0.5, 1.0 - (best_distance / (AsilNaverMatcher.MAX_COORDINATE_DISTANCE_M * 2))
            )

        # DTO 타입에 따라 필드 추출
        naver_name, _, _ = AsilNaverMatcher._extract_apt_info(best_candidate)
        if isinstance(best_candidate, NaverArticleItemDTO):
            naver_code = best_candidate.atcl_no
        else:
            naver_code = best_candidate.complex_no

        return MatchResultDTO(
            asil_apt_code=asil_apt.mm_uid,
            asil_apt_name=asil_apt.BLDNM,
            naver_apt_code=naver_code,
            naver_apt_name=naver_name,
            confidence=confidence,
            method=MatchMethod.COORDINATE,
            distance_m=best_distance,
        )

    @staticmethod
    def match_by_fuzzy_name(
        asil_apt: AsilOfferDetailDTO,
        candidates: "Sequence[NaverAptType]",
    ) -> MatchResultDTO | None:
        """
        퍼지 이름 매칭

        Args:
            asil_apt: ASIL 아파트 정보
            candidates: Naver 아파트 후보 목록 (NaverAptDTO 또는 NaverArticleItemDTO)

        Returns:
            매칭 결과 또는 None (매칭 실패 시)
        """
        if not candidates:
            return None

        asil_name = asil_apt.BLDNM

        # 가장 유사한 이름 찾기
        best_candidate = None
        best_similarity = -1.0

        for candidate in candidates:
            # DTO 타입에 따라 이름 추출
            naver_name, _, _ = AsilNaverMatcher._extract_apt_info(candidate)
            similarity = AsilNaverMatcher.name_similarity(asil_name, naver_name)

            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = candidate

        # 최소 신뢰도 체크
        if best_candidate is None or best_similarity < AsilNaverMatcher.MIN_FUZZY_CONFIDENCE:
            return None

        # DTO 타입에 따라 필드 추출
        naver_name, _, _ = AsilNaverMatcher._extract_apt_info(best_candidate)
        if isinstance(best_candidate, NaverArticleItemDTO):
            naver_code = best_candidate.atcl_no
        else:
            naver_code = best_candidate.complex_no

        return MatchResultDTO(
            asil_apt_code=asil_apt.mm_uid,
            asil_apt_name=asil_apt.BLDNM,
            naver_apt_code=naver_code,
            naver_apt_name=naver_name,
            confidence=best_similarity,
            method=MatchMethod.FUZZY_NAME,
            distance_m=None,
        )

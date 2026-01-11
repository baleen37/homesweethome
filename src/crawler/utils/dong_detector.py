"""대표동 감지 유틸리티

ASIL API는 특정 "대표동"을 조회하면 해당 지역 전체를 반환하는 패턴이 있습니다.
예: 문래동(1가) 조회 → 문래동 전체(1가~6가) 반환

이 모듈은 대표동을 자동 감지하고 중복 크롤링을 방지합니다.
"""

import re
from collections import defaultdict

from crawler.dto.asil_apt_list import AsilAptListDTO


class RepresentativeDongDetector:
    """대표동 여부를 자동 감지하는 클래스"""

    def __init__(self) -> None:
        """이미 처리된 동 그룹을 추적하기 위한 캐시"""
        self._seen_groups: set[str] = set()
        self._group_dongs: dict[str, set[str]] = defaultdict(set)

    def is_representative(self, apt_list: list[AsilAptListDTO]) -> bool:
        """여러 dong을 반환하는지 확인 (대표동 여부)

        Args:
            apt_list: API 응답 아파트 리스트

        Returns:
            대표동이면 True
        """
        if not apt_list:
            return False
        unique_dongs = len(set(apt.dong for apt in apt_list))
        return unique_dongs > 1

    def get_dong_codes(self, apt_list: list[AsilAptListDTO]) -> set[str]:
        """응답에 포함된 모든 dong 코드 반환

        Args:
            apt_list: API 응답 아파트 리스트

        Returns:
            dong 코드 집합
        """
        return set(apt.dong for apt in apt_list)

    def extract_base_dongname(self, dongname: str) -> str:
        """동 이름에서 숫자와 "가"/"동" 접미사 제거하여 기본 이름 추출

        Args:
            dongname: 동 이름 (예: "문래동1가", "문래동", "역삼1동")

        Returns:
            기본 동 이름 (예: "문래", "역삼")

        Examples:
            >>> extract_base_dongname("문래동1가")
            "문래"
            >>> extract_base_dongname("문래동")
            "문래"
            >>> extract_base_dongname("역삼1동")
            "역삼"
        """
        # "1가", "2동" 등의 숫자+접미사 제거
        base = re.sub(r"\d+가?$", "", dongname)
        # "동" 접미사 제거
        base = re.sub(r"동$", "", base)
        return base

    def get_dong_group(self, apt_list: list[AsilAptListDTO]) -> str:
        """아파트 리스트가 속한 동 그룹 반환

        Args:
            apt_list: API 응답 아파트 리스트

        Returns:
            기본 동 이름 (그룹 식별자)
        """
        if not apt_list:
            return ""
        # dongname은 모두 같은 그룹이라고 가정
        return self.extract_base_dongname(apt_list[0].dongname)

    def should_skip(self, apt_list: list[AsilAptListDTO]) -> bool:
        """이 동 크롤링을 스킵해야 하는지 확인

        이미 대표동에서 처리된 그룹이면 스킵.

        Args:
            apt_list: API 응답 아파트 리스트

        Returns:
            스킵해야 하면 True
        """
        if not apt_list:
            return True

        group = self.get_dong_group(apt_list)

        # 대표동인 경우: 그룹을 기록하고 스킵하지 않음
        if self.is_representative(apt_list):
            self._seen_groups.add(group)
            self._group_dongs[group].update(self.get_dong_codes(apt_list))
            return False

        # 일반동인 경우: 이미 그룹이 처리되었는지 확인
        return group in self._seen_groups

    def get_stats(self) -> dict[str, any]:
        """감지 통계 반환

        Returns:
            통계 딕셔너리
        """
        return {
            "seen_groups": len(self._seen_groups),
            "groups": dict(self._group_dongs),
        }

    def reset(self) -> None:
        """상태 초기화"""
        self._seen_groups.clear()
        self._group_dongs.clear()

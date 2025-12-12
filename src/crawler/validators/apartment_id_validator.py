"""아파트 ID 검증기

호갱노노 API에서 사용하는 아파트 ID의 유효성을 검증합니다.
"""

import re
from typing import Optional, Union

# Use built-in logging instead of structlog
import logging

logger = logging.getLogger(__name__)


class ApartmentIdValidator:
    """아파트 ID 유효성 검증기

    호갱노노 API의 아파트 ID 형식을 검증하고 유효하지 않은 ID를 필터링합니다.
    """

    # 유효한 아파트 ID 패턴 (일반적으로 영문 대문자와 숫자 조합)
    VALID_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    # 최소/최대 길이 제한
    MIN_ID_LENGTH = 1
    MAX_ID_LENGTH = 50

    # 유효하지 않은 문자 목록
    INVALID_CHARACTERS = [
        "/",
        " ",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "*",
        "(",
        ")",
        "+",
        "=",
        "[",
        "]",
        "{",
        "}",
        "|",
        "\\",
        ":",
        ";",
        '"',
        "'",
        "<",
        ">",
        ",",
        ".",
        "?",
        "!",
    ]

    @classmethod
    def is_valid_id(cls, apt_id: Optional[Union[str, int]]) -> bool:
        """아파트 ID가 유효한지 확인

        Args:
            apt_id: 검증할 아파트 ID

        Returns:
            bool: 유효하면 True, 아니면 False
        """
        # None 체크
        if apt_id is None:
            logger.debug("apartment_id_invalid", reason="None value")
            return False

        # 타입 변환 (숫자도 가능)
        if isinstance(apt_id, int):
            apt_id = str(apt_id)

        # 문자열 타입 체크
        if not isinstance(apt_id, str):
            logger.debug("apartment_id_invalid", reason=f"Invalid type: {type(apt_id)}")
            return False

        # 공백 문자열 체크
        if not apt_id.strip():
            logger.debug("apartment_id_invalid", reason="Empty or whitespace only")
            return False

        # 길이 체크
        if len(apt_id) < cls.MIN_ID_LENGTH or len(apt_id) > cls.MAX_ID_LENGTH:
            logger.debug(
                "apartment_id_invalid",
                reason=f"Invalid length: {len(apt_id)} (should be {cls.MIN_ID_LENGTH}-{cls.MAX_ID_LENGTH})",
            )
            return False

        # 유효하지 않은 문자 체크
        if any(char in apt_id for char in cls.INVALID_CHARACTERS):
            invalid_chars = [char for char in cls.INVALID_CHARACTERS if char in apt_id]
            logger.debug(
                "apartment_id_invalid", reason=f"Contains invalid characters: {invalid_chars}"
            )
            return False

        # 패턴 매칭 (영문, 숫자, 언더스코어, 하이픈만 허용)
        if not cls.VALID_ID_PATTERN.match(apt_id):
            logger.debug("apartment_id_invalid", reason="Does not match valid pattern")
            return False

        # 모든 검증 통과
        logger.debug("apartment_id_valid", id=apt_id)
        return True

    @classmethod
    def validate_and_normalize(cls, apt_id: Optional[Union[str, int]]) -> Optional[str]:
        """아파트 ID를 검증하고 정규화

        Args:
            apt_id: 검증할 아파트 ID

        Returns:
            Optional[str]: 정규화된 아파트 ID (유효하지 않으면 None)
        """
        if not cls.is_valid_id(apt_id):
            return None

        # 문자열로 변환하고 양 끝 공백 제거
        normalized = str(apt_id).strip()

        return normalized

    @classmethod
    def filter_valid_ids(cls, apt_ids: list) -> tuple[list, list]:
        """ID 목록에서 유효한 ID와 유효하지 않은 ID를 분리

        Args:
            apt_ids: 아파트 ID 목록

        Returns:
            tuple: (유효한 ID 목록, 유효하지 않은 ID 목록과 이유)
        """
        valid_ids = []
        invalid_ids = []

        for apt_id in apt_ids:
            normalized_id = cls.validate_and_normalize(apt_id)
            if normalized_id:
                valid_ids.append(normalized_id)
            else:
                reason = cls._get_invalid_reason(apt_id)
                invalid_ids.append((apt_id, reason))

        return valid_ids, invalid_ids

    @classmethod
    def _get_invalid_reason(cls, apt_id: Optional[Union[str, int]]) -> str:
        """ID가 유효하지 않은 이유 반환

        Args:
            apt_id: 검증할 아파트 ID

        Returns:
            str: 유효하지 않은 이유
        """
        if apt_id is None:
            return "None value"

        if isinstance(apt_id, int):
            apt_id = str(apt_id)

        if not isinstance(apt_id, str):
            return f"Invalid type: {type(apt_id).__name__}"

        if not apt_id.strip():
            return "Empty or whitespace only"

        if len(apt_id) < cls.MIN_ID_LENGTH or len(apt_id) > cls.MAX_ID_LENGTH:
            return f"Invalid length: {len(apt_id)}"

        if any(char in apt_id for char in cls.INVALID_CHARACTERS):
            invalid_chars = [char for char in cls.INVALID_CHARACTERS if char in apt_id]
            return f"Contains invalid characters: {invalid_chars}"

        if not cls.VALID_ID_PATTERN.match(apt_id):
            return "Contains only allowed: letters, numbers, underscore, hyphen"

        return "Unknown reason"

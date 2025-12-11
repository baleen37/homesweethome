from typing import Any

from crawler.writers.base_csv_writer import BaseCSVWriter


class TransactionCSVWriter(BaseCSVWriter):
    """거래내역 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 transactions.csv 파일을 생성합니다.
    점진적 저장(incremental write)을 지원합니다.
    """

    # 정의된 CSV 스키마
    FIELDNAMES = [
        "complex_id",
        "complex_name",
        "pyeong_type_number",
        "pyeong_name",
        "trade_type",
        "trade_type_name",
        "trade_date",
        "trade_year",
        "floor",
        "deal_price",
        "deposit",
        "monthly_rent",
        "trade_category",
        "is_delete",
        "is_renew",
        "gu_code",  # 추가: 구 코드
        "dong_code",  # 추가: 동 코드
        "gu_name",  # 추가: 구 이름
        "dong_name",  # 추가: 동 이름
    ]

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """거래내역 데이터를 CSV 스키마에 맞게 정규화합니다.

        필드 순서를 보장하고, 누락된 필드를 기본값으로 채웁니다.

        Args:
            row: 정규화할 거래내역 데이터

        Returns:
            정규화된 거래내역 데이터
        """
        # Base 정규화 적용
        normalized = self._normalize_common_fields(row)

        # 특수 필드 처리 - boolean 필드는 boolean 타입 유지
        for field in ["is_delete", "is_renew"]:
            value = row.get(field, "")
            if isinstance(value, bool):
                normalized[field] = value
            elif isinstance(value, str):
                normalized[field] = value.lower() == "true"
            elif isinstance(value, int) and value in (0, 1):
                normalized[field] = bool(value)
            else:
                normalized[field] = False

        # 숫자 필드 처리
        for field in ["floor", "deal_price", "deposit", "monthly_rent", "pyeong_type_number"]:
            try:
                normalized[field] = int(row.get(field, "")) if row.get(field, "") != "" else 0
            except (ValueError, TypeError):
                normalized[field] = 0

        # FIELDNAMES 순서로 필터링, boolean 필드는 타입 유지
        result = {}
        for field in self.FIELDNAMES:
            if field in ["is_delete", "is_renew"]:
                # Boolean 필드는 타입 유지
                result[field] = normalized.get(field, False)
            else:
                # 다른 필드는 문자열로 변환
                value = normalized.get(field, "")
                result[field] = str(value) if value is not None else ""

        return result

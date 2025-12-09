"""CSV writer for Hogangnono real estate data.

This module provides HogangnonoCSVWriter class for saving Hogangnono API responses
to CSV files.
"""

import json
from pathlib import Path
from typing import Any, List, Dict

from crawler.writers.csv_writer import CSVWriter


class HogangnonoCSVWriter:
    """호갱노노 데이터를 CSV로 저장

    호갱노노 API 응답 데이터를 받아 CSV 파일로 저장합니다.
    - complexes.csv: 단지 정보 저장
    - transactions.csv: 거래내역 저장
    """

    # 호갱노노 단지 정보 필드명 (원본 데이터 그대로 사용)
    COMPLEXES_FIELDNAMES = [
        "id",
        "name",
        "address",
        "lat",
        "lng",
        "build_year",
        "households",
        "floors",
    ]

    # 호갱노노 거래내역 필드명 (동적 필드를 포함한 기본 필드)
    TRANSACTIONS_FIELDNAMES = [
        "id",
        "name",
        "address",
        "lat",
        "lng",
        "build_year",
        "households",
        "floors",
        # 거래 관련 필드들은 데이터에 따라 동적으로 추가됨
    ]

    def __init__(self, output_dir: str = "output") -> None:
        """HogangnonoCSVWriter 초기화

        Args:
            output_dir: 출력 디렉토리 경로
        """
        self.output_dir = Path(output_dir)
        self.complexes_path = self.output_dir / "complexes.csv"
        self.transactions_path = self.output_dir / "transactions.csv"

        # CSV writer 인스턴스 생성
        self.complexes_writer = CSVWriter(self.complexes_path)
        self.transactions_writer = CSVWriter(self.transactions_path)

        # 파일 생성 여부 추적
        self._complexes_file_exists = self.complexes_path.exists()
        self._transactions_file_exists = self.transactions_path.exists()

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """단지 데이터를 complexes.csv로 저장

        Args:
            complexes_data: 호갱노노에서 가져온 단지 데이터 리스트
        """
        if not complexes_data:
            return

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 원본 데이터 그대로 저장
        mode = "a" if self._complexes_file_exists else "w"
        self.complexes_writer.write(complexes_data, mode=mode)

        if mode == "w":
            self._complexes_file_exists = True

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """거래내역 데이터를 transactions.csv로 저장

        Args:
            transactions_data: 호갱노노에서 가져온 거래내역 데이터 리스트
        """
        if not transactions_data:
            return

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 원본 데이터 그대로 저장
        mode = "a" if self._transactions_file_exists else "w"
        self.transactions_writer.write(transactions_data, mode=mode)

        if mode == "w":
            self._transactions_file_exists = True

    def save_from_json_file(self, json_file_path: str, data_type: str = "complex") -> None:
        """JSON 파일에서 호갱노노 데이터를 읽어 CSV로 저장

        Args:
            json_file_path: JSON 파일 경로
            data_type: 저장할 데이터 타입 ("complex" 또는 "transaction")
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 단일 데이터가 아닌 리스트인지 확인
            if isinstance(data, dict) and "data" in data:
                data = data["data"]

            if isinstance(data, dict):
                data = [data]

            if data_type == "complex":
                self.save_complexes(data)
            elif data_type == "transaction":
                self.save_transactions(data)

        except FileNotFoundError:
            raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"JSON 파싱 오류: {json_file_path}")
        except Exception as e:
            raise RuntimeError(f"데이터 저장 중 오류 발생: {str(e)}")

    def get_stats(self) -> Dict[str, int]:
        """저장된 파일 통계 정보 반환

        Returns:
            파일 통계 정보
        """
        stats = {
            "complexes_file_size": 0,
            "transactions_file_size": 0,
            "complexes_record_count": 0,
            "transactions_record_count": 0,
        }

        try:
            if self.complexes_path.exists():
                stats["complexes_file_size"] = self.complexes_path.stat().st_size

                # 레코드 수 계산 (헤더 제외)
                with open(self.complexes_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        stats["complexes_record_count"] = len(lines) - 1

        except Exception:
            pass

        try:
            if self.transactions_path.exists():
                stats["transactions_file_size"] = self.transactions_path.stat().st_size

                # 레코드 수 계산 (헤더 제외)
                with open(self.transactions_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        stats["transactions_record_count"] = len(lines) - 1

        except Exception:
            pass

        return stats

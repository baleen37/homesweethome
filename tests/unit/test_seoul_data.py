"""서울시 지역 데이터 테스트"""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def seoul_data_path() -> Path:
    """서울시 데이터 JSON 파일 경로"""
    return Path(__file__).parent.parent.parent / "src" / "crawler" / "data" / "seoul_districts.json"


@pytest.fixture
def seoul_data(seoul_data_path: Path) -> dict[str, Any]:
    """서울시 데이터 로드"""
    with open(seoul_data_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


class TestSeoulDataFile:
    """서울시 데이터 파일 테스트"""

    def test_file_exists(self, seoul_data_path: Path) -> None:
        """JSON 파일이 존재하는지 확인"""
        assert (
            seoul_data_path.exists()
        ), f"서울시 데이터 파일이 존재하지 않습니다: {seoul_data_path}"
        assert seoul_data_path.is_file(), f"경로가 파일이 아닙니다: {seoul_data_path}"


class TestSeoulDataSchema:
    """서울시 데이터 스키마 테스트"""

    def test_root_structure(self, seoul_data: dict[str, Any]) -> None:
        """최상위 구조 검증"""
        assert "districts" in seoul_data, "districts 키가 없습니다"
        assert isinstance(seoul_data["districts"], list), "districts는 리스트여야 합니다"

    def test_district_structure(self, seoul_data: dict[str, Any]) -> None:
        """구 데이터 구조 검증"""
        for district in seoul_data["districts"]:
            assert "district_name" in district, f"district_name 키가 없습니다: {district}"
            assert "district_code" in district, f"district_code 키가 없습니다: {district}"
            assert "dongs" in district, f"dongs 키가 없습니다: {district}"

            assert isinstance(district["district_name"], str), "district_name은 문자열이어야 합니다"
            assert isinstance(district["district_code"], str), "district_code는 문자열이어야 합니다"
            assert isinstance(district["dongs"], list), "dongs는 리스트여야 합니다"

    def test_dong_structure(self, seoul_data: dict[str, Any]) -> None:
        """동 데이터 구조 검증"""
        for district in seoul_data["districts"]:
            for dong in district["dongs"]:
                assert "dong_name" in dong, f"dong_name 키가 없습니다: {dong}"
                assert "cortarNo" in dong, f"cortarNo 키가 없습니다: {dong}"
                assert "bounds" in dong, f"bounds 키가 없습니다: {dong}"

                assert isinstance(dong["dong_name"], str), "dong_name은 문자열이어야 합니다"
                assert isinstance(dong["cortarNo"], str), "cortarNo는 문자열이어야 합니다"
                assert isinstance(dong["bounds"], dict), "bounds는 딕셔너리여야 합니다"

    def test_bounds_structure(self, seoul_data: dict[str, Any]) -> None:
        """bounds 데이터 구조 검증"""
        for district in seoul_data["districts"]:
            for dong in district["dongs"]:
                bounds = dong["bounds"]
                assert "leftLon" in bounds, f"leftLon 키가 없습니다: {bounds}"
                assert "rightLon" in bounds, f"rightLon 키가 없습니다: {bounds}"
                assert "topLat" in bounds, f"topLat 키가 없습니다: {bounds}"
                assert "bottomLat" in bounds, f"bottomLat 키가 없습니다: {bounds}"

                assert isinstance(bounds["leftLon"], (int, float)), "leftLon은 숫자여야 합니다"
                assert isinstance(bounds["rightLon"], (int, float)), "rightLon은 숫자여야 합니다"
                assert isinstance(bounds["topLat"], (int, float)), "topLat은 숫자여야 합니다"
                assert isinstance(bounds["bottomLat"], (int, float)), "bottomLat은 숫자여야 합니다"


class TestSeoulDataContent:
    """서울시 데이터 내용 테스트"""

    def test_district_count(self, seoul_data: dict[str, Any]) -> None:
        """서울시 25개 구가 모두 있는지 확인"""
        assert (
            len(seoul_data["districts"]) == 25
        ), f"서울시 구 개수는 25개여야 합니다. 실제: {len(seoul_data['districts'])}개"

    def test_district_names(self, seoul_data: dict[str, Any]) -> None:
        """서울시 구 이름 검증"""
        expected_districts = {
            "강남구",
            "강동구",
            "강북구",
            "강서구",
            "관악구",
            "광진구",
            "구로구",
            "금천구",
            "노원구",
            "도봉구",
            "동대문구",
            "동작구",
            "마포구",
            "서대문구",
            "서초구",
            "성동구",
            "성북구",
            "송파구",
            "양천구",
            "영등포구",
            "용산구",
            "은평구",
            "종로구",
            "중구",
            "중랑구",
        }
        actual_districts = {district["district_name"] for district in seoul_data["districts"]}
        assert (
            actual_districts == expected_districts
        ), f"구 이름이 일치하지 않습니다. 차이: {expected_districts ^ actual_districts}"

    def test_each_district_has_dongs(self, seoul_data: dict[str, Any]) -> None:
        """각 구에 최소 1개 이상의 동이 있는지 확인"""
        for district in seoul_data["districts"]:
            assert len(district["dongs"]) > 0, f"{district['district_name']}에 동 데이터가 없습니다"

    def test_district_codes(self, seoul_data: dict[str, Any]) -> None:
        """구 코드 형식 검증 (10자리 숫자)"""
        for district in seoul_data["districts"]:
            assert (
                len(district["district_code"]) == 10
            ), f"구 코드는 10자리여야 합니다: {district['district_code']}"
            assert district[
                "district_code"
            ].isdigit(), f"구 코드는 숫자여야 합니다: {district['district_code']}"
            # 구 코드는 대부분 000000으로 끝나지만, 일부는 다를 수 있음 (예: 강북구 1130500000)
            assert district["district_code"].endswith(
                "00000"
            ), f"구 코드는 최소 00000으로 끝나야 합니다: {district['district_code']}"

    def test_dong_codes(self, seoul_data: dict[str, Any]) -> None:
        """동 코드 형식 검증 (10자리 숫자)"""
        for district in seoul_data["districts"]:
            for dong in district["dongs"]:
                assert (
                    len(dong["cortarNo"]) == 10
                ), f"동 코드는 10자리여야 합니다: {dong['cortarNo']}"
                assert dong["cortarNo"].isdigit(), f"동 코드는 숫자여야 합니다: {dong['cortarNo']}"


class TestSeoulDataBounds:
    """서울시 데이터 bounds 검증 테스트"""

    def test_bounds_validity(self, seoul_data: dict[str, Any]) -> None:
        """bounds 값이 유효한지 확인 (leftLon < rightLon, bottomLat < topLat)"""
        for district in seoul_data["districts"]:
            for dong in district["dongs"]:
                bounds = dong["bounds"]
                assert bounds["leftLon"] < bounds["rightLon"], (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"leftLon({bounds['leftLon']})이 rightLon({bounds['rightLon']})보다 작아야 합니다"
                )
                assert bounds["bottomLat"] < bounds["topLat"], (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"bottomLat({bounds['bottomLat']})이 topLat({bounds['topLat']})보다 작아야 합니다"
                )

    def test_bounds_in_seoul_range(self, seoul_data: dict[str, Any]) -> None:
        """bounds가 서울시 범위 내에 있는지 확인"""
        # 서울시 대략적인 좌표 범위
        seoul_min_lat = 37.4
        seoul_max_lat = 37.7
        seoul_min_lon = 126.7
        seoul_max_lon = 127.2

        for district in seoul_data["districts"]:
            for dong in district["dongs"]:
                bounds = dong["bounds"]
                assert seoul_min_lat <= bounds["bottomLat"] <= seoul_max_lat, (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"bottomLat({bounds['bottomLat']})이 서울 범위를 벗어났습니다"
                )
                assert seoul_min_lat <= bounds["topLat"] <= seoul_max_lat, (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"topLat({bounds['topLat']})이 서울 범위를 벗어났습니다"
                )
                assert seoul_min_lon <= bounds["leftLon"] <= seoul_max_lon, (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"leftLon({bounds['leftLon']})이 서울 범위를 벗어났습니다"
                )
                assert seoul_min_lon <= bounds["rightLon"] <= seoul_max_lon, (
                    f"{district['district_name']} {dong['dong_name']}: "
                    f"rightLon({bounds['rightLon']})이 서울 범위를 벗어났습니다"
                )


class TestSeoulDataStatistics:
    """서울시 데이터 통계 테스트"""

    def test_total_dong_count(self, seoul_data: dict[str, Any]) -> None:
        """전체 동 개수 확인"""
        total_dongs = sum(len(district["dongs"]) for district in seoul_data["districts"])
        # 최소 400개 이상의 동이 있어야 함 (실제로는 467개)
        assert total_dongs >= 400, f"전체 동 개수가 너무 적습니다: {total_dongs}개"
        # 최대 500개 미만이어야 함 (데이터 중복 검증)
        assert total_dongs < 500, f"전체 동 개수가 너무 많습니다: {total_dongs}개"

    def test_no_duplicate_districts(self, seoul_data: dict[str, Any]) -> None:
        """중복된 구가 없는지 확인"""
        district_names = [district["district_name"] for district in seoul_data["districts"]]
        assert len(district_names) == len(set(district_names)), "중복된 구가 있습니다"

        district_codes = [district["district_code"] for district in seoul_data["districts"]]
        assert len(district_codes) == len(set(district_codes)), "중복된 구 코드가 있습니다"

    def test_no_duplicate_dongs_in_district(self, seoul_data: dict[str, Any]) -> None:
        """각 구 내에 중복된 동이 없는지 확인"""
        for district in seoul_data["districts"]:
            dong_names = [dong["dong_name"] for dong in district["dongs"]]
            assert len(dong_names) == len(
                set(dong_names)
            ), f"{district['district_name']}에 중복된 동 이름이 있습니다"

            dong_codes = [dong["cortarNo"] for dong in district["dongs"]]
            assert len(dong_codes) == len(
                set(dong_codes)
            ), f"{district['district_name']}에 중복된 동 코드가 있습니다"

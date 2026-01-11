# 카카오맵 좌표계 변환 분석 보고서

## 개요

카카오맵 대중교통 API 요청 파라미터의 좌표계를 분석하고, WGS84(위경도)를 WCONGNAMUL(카카오맵 좌표계)로 변환하는 Python 코드를 구현했습니다.

## 좌표계 분석 결과

### 1. WCONGNAMUL 좌표계 특성

- **기반**: EPSG:5181 (중부원점 TM 투영 좌표계, GRS80 타원체)
- **스케일**: EPSG:5181에 2.5배 스케일 적용
- **원점**: 위도 38°N, 경도 127°E (중부원점)
- **오프셋**:
  - X(경도) 방향: 200,000m (FALSE_EASTING)
  - Y(위도) 방향: 500,000m (FALSE_NORTHING)

### 2. API 요청 파라미터 형식

카카오맵 대중교통 API에서는 다음 파라미터를 사용합니다:

```
?sX={startX}&sY={startY}&eX={endX}&eY={endY}
```

- **sX, sY**: 출발지 WCONGNAMUL 좌표 (X, Y)
- **eX, eY**: 도착지 WCONGNAMUL 좌표 (X, Y)

### 3. 변환 정확도

- **서울/경기 지역**: 왕복 변환 오차 < 0.000002도 (약 0.22미터)
- **부산/제주 등**: 원점에서 먼 지역은 오차가 커질 수 있음 (TM 투영 특성)

## Python 구현

### 파일 구조

```
src/crawler/
└── coordinate_converter.py    # 좌표 변환 모듈

tests/unit/
└── test_coordinate_converter.py  # 유닛 테스트

examples/
└── coordinate_converter_usage.py  # 사용 예제
```

### 사용 예시

```python
from src.crawler.coordinate_converter import (
    wgs84_to_wcongnamul,
    wcongnamul_to_wgs84,
)

# WGS84 -> WCONGNAMUL
lat, lon = 37.5665, 126.9780  # 서울시청
x, y = wgs84_to_wcongnamul(lat, lon)
print(f"WCONGNAMUL: X={x}, Y={y}")

# WCONGNAMUL -> WGS84
lon, lat = wcongnamul_to_wgs84(x, y)
print(f"WGS84: lat={lat}, lon={lon}")
```

### 카카오맵 대중교통 API 적용 예시

```python
# 출발지: 서울역, 도착지: 강남역
start_lat, start_lon = 37.5547, 126.9707
end_lat, end_lon = 37.5172, 127.0473

# WCONGNAMUL로 변환
start_x, start_y = wgs84_to_wcongnamul(start_lat, start_lon)
end_x, end_y = wgs84_to_wcongnamul(end_lat, end_lon)

# API 요청 파라미터 생성
params = f"?sX={start_x}&sY={start_y}&eX={end_x}&eY={end_y}"
print(params)  # ?sX=493528&sY=1126439&eX=510454&eY=1116035
```

## 기술 상세

### Transverse Mercator 투영

구현된 변환 공식은 Transverse Mercator 투영법을 기반으로 합니다:

1. **타원체 파라미터**: WGS84 타원체 (반장축 6,378,137m, 편평률 0.0033528...)
2. **자오선 길이 계산**: 위도에 따른 자오선 호 길이 계산
3. **투영 변환**: 경도 차이를 이용한 X, Y 좌표 계산
4. **스케일 적용**: 2.5배 스케일로 WCONGNAMUL 변환

### 함수 API

#### `wgs84_to_wcongnamul(latitude, longitude) -> (x, y)`

WGS84 좌표를 WCONGNAMUL 좌표로 변환합니다.

**Parameters:**
- `latitude` (float): 위도 (WGS84, decimal degrees)
- `longitude` (float): 경도 (WGS84, decimal degrees)

**Returns:**
- `Tuple[float, float]`: (x, y) WCONGNAMUL 좌표

#### `wcongnamul_to_wgs84(x, y) -> (longitude, latitude)`

WCONGNAMUL 좌표를 WGS84 좌표로 변환합니다.

**Parameters:**
- `x` (float): WCONGNAMUL X 좌표
- `y` (float): WCONGNAMUL Y 좌표

**Returns:**
- `Tuple[float, float]`: (longitude, latitude) WGS84 좌표

## 테스트

```bash
# 전체 테스트 실행
uv run pytest tests/unit/test_coordinate_converter.py -v

# 단일 테스트 실행
uv run pytest tests/unit/test_coordinate_converter.py::TestCoordinateConverter::test_wgs84_to_wcongnamul_known_values -v

# 예제 실행
uv run python -m examples.coordinate_converter_usage
```

## 참고자료

1. [Go: WGS84를 WCONGNAMUL로 변환 함수](https://choiseokwon.tistory.com/407)
   - Transverse Mercator 투영 공식의 Go 언어 구현
   - 본 Python 코드는 이 공식을 기반으로 구현됨

2. [EPSG:5174 데이터 변환 - 카카오 개발자 포럼](https://devtalk.kakao.com/t/epsg-5174/112815)

3. [Kakao 지도 Web API 문서](https://apis.map.kakao.com/web/documentation/)

## 주의사항

1. **중부원점 기반**: 본 변환은 중부원점 TM 투영(EPSG:5181)을 기반으로 하므로 서울/경기 지역에서 가장 정확합니다.

2. **좌표 순서**:
   - WGS84 변환: `wgs84_to_wcongnamul(latitude, longitude)`
   - WCONGNAMUL 변환: `wcongnamul_to_wgs84(x, y) -> (longitude, latitude)`

3. **반올림**: WCONGNAMUL 변환 시 `round()` 함수를 사용하므로 왕복 변환 시 미세한 오차가 발생할 수 있습니다 (약 0.000001도 = 0.11미터).

4. **원점에서 먼 지역**: 부산, 제주 등 중부원점(위도 38°N, 경도 127°E)에서 먼 지역은 오차가 커질 수 있습니다. 이는 TM 투영법의 특성상 원점에서 가까울수록 정확하기 때문입니다.

## 라이선스

본 코드는 프로젝트의 라이선스를 따릅니다.

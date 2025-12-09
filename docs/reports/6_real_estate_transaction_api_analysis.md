# 6단계: 실거래 내역 API 분석 보고서

**분석 일자**: 2025-12-09
**분석 대상**: 호갱노노 부동산 실거래 내역 조회 API
**분석 방법**: 코드 분석 및 API 직접 테스트

## API 엔드포인트

| 엔드포인트 | 설명 | 상태 |
|------------|------|------|
| `https://hogangnono.com/api/v2/pois-bounding` | POI(관심지점) 목록 조회 (좌표 기반) | ✅ 활성 |
| `https://hogangnono.com/api/v2/ranks/rolling` | 인기 순위 조회 | ✅ 활성 |
| `https://hogangnono.com/api/v2/maps/region` | 지역 정보 조회 | ✅ 활성 |
| `https://hogangnono.com/api/v2/apts/recent-visits` | 최근 방문 아파트 | ✅ 활성 |
| `https://hogangnono.com/cluster/ajax/complexList` | 단지 목록 조회 | ❌ 404 |
| `https://hogangnono.com/cluster/ajax/complexDetail` | 단지 상세 정보 | ❌ 404 |
| `https://hogangnono.com/api/v2/apts` | 아파트 목록 (지역코드 기반) | ❌ 404 |
| `https://hogangnono.com/api/apt/detail` | 아파트 상세 정보 | ❌ 404 |

## 요청 파라미터 상세

### 필수 파라미터
| 파라미터 | 타입 | 설명 | 예시 |
|----------|------|------|------|
| startX | float | 최소 경도 (lng_min) | 127.048 |
| endX | float | 최대 경도 (lng_max) | 127.068 |
| startY | float | 최소 위도 (lat_min) | 37.495 |
| endY | float | 최대 위도 (lat_max) | 37.515 |

### 선택적 파라미터
| 파라미터 | 타입 | 설명 | 기본값 | 예시 |
|----------|------|------|--------|------|
| level | string | 줌 레벨 (1-18, 클수록 상세) | "17" | "17" |
| tradeType | int | 거래 유형 (0:매매, 1:전세, 2:월세) | 0 | 0 |
| aptType | int | 아파트 유형 (-1:전체, 0:아파트, 1:주상복합, 2:오피스텔) | -1 | 1 |
| priceType | int | 가격 유형 (0:전체, 1:매매, 2:전세) | 0 | 0 |
| rentType | int | 임대 유형 (0:전체, 1:월세, 2:단기임대) | 0 | 0 |
| areaFrom | float | 최소 전용면적 (㎡) | - | 30 |
| areaTo | float | 최대 전용면적 (㎡) | - | 100 |
| priceFrom | int | 최소 가격 (만원) | - | 50000 |
| priceTo | int | 최대 가격 (만원) | - | 150000 |
| map | string | 지도 종류 | "google" | "google" |
| screenWidth | int | 화면 너비 | 1200 | 1200 |
| screenHeight | int | 화면 높이 | 924 | 924 |
| apt | string | 아파트 필터 | "" | "" |

## 요청 예시

### 기본 요청
```bash
# 세션 초기화
curl -c cookies.txt -X GET "https://hogangnono.com"

# 특정 지역 POI 조회
curl -b cookies.txt \
  -X GET "https://hogangnono.com/api/v2/pois-bounding" \
  -G \
  -d "startX=127.048" \
  -d "endX=127.068" \
  -d "startY=37.495" \
  -d "endY=37.515" \
  -d "level=17"
```

### 필터링 옵션 적용
```bash
# 아파트만 필터링 (aptType=1)
curl -b cookies.txt \
  -X GET "https://hogangnono.com/api/v2/pois-bounding" \
  -G \
  -d "startX=127.048" \
  -d "endX=127.068" \
  -d "startY=37.495" \
  -d "endY=37.515" \
  -d "tradeType=0" \
  -d "aptType=1"

# 가격/면적 필터링
curl -b cookies.txt \
  -X GET "https://hogangnono.com/api/v2/pois-bounding" \
  -G \
  -d "startX=127.048" \
  -d "endX=127.068" \
  -d "startY=37.495" \
  -d "endY=37.515" \
  -d "areaFrom=30" \
  -d "areaTo=100" \
  -d "priceFrom=50000" \
  -d "priceTo=150000"
```

## 응답 데이터 구조

### POI 목록 응답
```json
{
  "data": [
    {
      "id": "cfa3",
      "category": 1,
      "name": "삼성",
      "description": "2호선",
      "content": null,
      "lat": 37.508822740225305,
      "lng": 127.06302321147604,
      "address": null,
      "likes": 0,
      "isExpired": 0,
      "dong": null,
      "dist": 614
    }
  ],
  "status": "success"
}
```

### 인기 순위 응답
```json
{
  "data": {
    "rolling": [
      {
        "sidoName": "서울특별시",
        "sigunguName": "강남구",
        "dongName": "역삼동",
        "rank": 1,
        "prevRank": 2,
        "visitor": 1250,
        "rankType": "daily",
        "hash": "gKl6c",
        "regionName": "서울 강남구 역삼동",
        "name": "역삼아파트",
        "statusTag": "hot"
      }
    ]
  }
}
```

## 주요 필드 설명

### POI 데이터 필드
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| id | string | POI 고유 ID | "cfa3" |
| category | int | 카테고리 코드 (1: 아파트, 10: 상점 등) | 1 |
| name | string | 명칭 | "삼성" |
| description | string | 설명 | "2호선" |
| lat | float | 위도 | 37.508822740225305 |
| lng | float | 경도 | 127.06302321147604 |
| address | string | 주소 | "서울특별시 강남구 삼성동..." |
| likes | int | 좋아요 수 | 0 |
| isExpired | int | 만료 여부 (0: 유효, 1: 만료) | 0 |
| dong | string | 동 이름 | "삼성동" |
| dist | int | 기준점으로부터의 거리 (미터) | 614 |

### 인기 순위 데이터 필드
| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| hash | string | 단지 고유 ID (단지 식별자) | "gKl6c" |
| name | string | 단지명 | "역삼아파트" |
| sidoName | string | 시/도명 | "서울특별시" |
| sigunguName | string | 시/군구명 | "강남구" |
| dongName | string | 동 이름 | "역삼동" |
| regionName | string | 전체 지역명 | "서울 강남구 역삼동" |
| rank | int | 현재 순위 | 1 |
| prevRank | int | 이전 순위 | 2 |
| visitor | int | 방문자 수 (인기도 지표) | 1250 |
| rankType | string | 순위 타입 (daily/weekly/monthly) | "daily" |
| statusTag | string | 상태 태그 (hot/new 등) | "hot" |

## 페이지네이션 및 데이터 제한

- **페이지네이션**: 지원하지 않음
- **최대 반환 수**: 약 600개 (요청 영역 크기에 따라 달라짐)
- **영역 조절**: `level` 파라미터로 조회 영역 크기 조절
  - level 1-8: 전국/광역시 단위
  - level 9-12: 구/군 단위
  - level 13-15: 동 단위
  - level 16-18: 단지 상세 단위

## 분석 결과 및 특이사항

### 1. 실거래 내역 직접 조회 불가
- 현재 API는 POI(Point of Interest) 정보만 제공
- 실제 거래 가격, 면적, 계약일 등의 정보 없음
- 아파트 매물이 아닌 지하철역, 상점 등 다양한 정보 포함
- `category=1` 필터링으로 아파트만 구분 필요

### 2. 지역코드 기반 조회 미지원
- `/api/v2/apts?regionCode=...` 엔드포인트 404 오류
- 오직 Bounding box 좌표 기반 조회만 지원
- 지역별 크롤링을 위해 좌표 변환 필요

### 3. 인증 필수
- 세션 쿠키(`connect.sid`) 필수
- 메인 페이지 접속으로 쿠키 발급 필요
- 쿠키 만료 시 재발급 필요

### 4. 단지 ID 획득 방법
- 인기 순위 API에서 `hash` 필드로 단지 ID 획득 가능
- 하지만 전체 단지 목록이 아닌 인기 단지만 제한적 제공

### 5. 실제 데이터 소스 추측
- 실거래 내역은 웹페이지 JavaScript로 동적 로드될 가능성
- 별도의 내부 API에서 가져오거나 HTML 렌더링 후 삽입될 수 있음
- 브라우저 자동화(Playwright) 필요

## 제안사항

### 1. 동적 크롤링 전략
```python
# Playwright를 사용한 단지 상세 페이지 크롤링
async def crawl_complex_detail(complex_id):
    page = await browser.new_page()
    await page.goto(f"https://hogangnono.com/complex/{complex_id}")

    # JavaScript 실행 후 거래 내역 로드 대기
    await page.wait_for_selector('.transaction-list')

    # 네트워크 요청 모니터링
    page.on('response', handle_response)

    # 거래 내역 추출
    transactions = await page.evaluate('window.transactions')
    return transactions
```

### 2. 네트워크 요청 분석
- 브라우저 개발자 도구로 실제 거래 내역 요청 경로 확인
- WebSocket 연결 여부 확인
- 추가적인 API 엔드포인트 발견

### 3. 데이터 수집 워크플로우
1. POI API로 아파트 단지 목록 획득 (category=1 필터)
2. 각 단지별 상세 페이지 접속
3. JavaScript로 로드되는 실거래 내역 캡처
4. CSV 형식으로 데이터 저장

### 4. 대안 데이터 소스
- 공공데이터포털 실거래가 API 활용
- 다른 부동산 플랫폼 비교 분석
- 여러 소스 데이터 결합

## 다음 단계 (7단계)
1. Playwright 기반 동적 크롤러 구현
2. 단지 상세 페이지의 거래 내역 추출 로직 개발
3. 좌표 기반 대량 데이터 수집 자동화
4. 데이터 정제 및 CSV 저장 기능 확장
5. 에러 처리 및 재시도 메커니즘 구현

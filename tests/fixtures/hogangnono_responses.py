"""호갱노노 API 응답 Mock 데이터"""

# POI bounding API 응답 Mock 데이터
MOCK_POIS_BOUNDING_RESPONSE = {
    "success": True,
    "data": [
        {
            "id": "complex_123456",
            "name": "테스트아파트",
            "lat": 37.5172,
            "lng": 127.0473,
            "type": "아파트",
            "region1": "서울특별시",
            "region2": "강남구",
            "region3": "역삼동",
            "address": "서울특별시 강남구 역삼동 123-45",
            "buildDate": "2005",
            "households": 300,
            "floors": 15,
            "elevatorCount": 3,
            "parkingCount": 250,
            "heatingType": "개별난방",
            "totalFloorArea": "15000",
            "totalSiteArea": "8000",
        },
        {
            "id": "complex_789012",
            "name": "샘플주상복합",
            "lat": 37.5200,
            "lng": 127.0500,
            "type": "주상복합",
            "region1": "서울특별시",
            "region2": "강남구",
            "region3": "대치동",
            "address": "서울특별시 강남구 대치동 678-90",
            "buildDate": "2010",
            "households": 450,
            "floors": 25,
            "elevatorCount": 5,
            "parkingCount": 400,
            "heatingType": "지역난방",
            "totalFloorArea": "25000",
            "totalSiteArea": "12000",
        },
    ],
}

# Ranks rolling API 응답 Mock 데이터
MOCK_RANKS_ROLLING_RESPONSE = {
    "success": True,
    "data": {
        "rolling": [
            {
                "hash": "rank_abc123",
                "name": "인기아파트",
                "sidoName": "서울특별시",
                "sigunguName": "강남구",
                "dongName": "대치동",
                "regionName": "서울특별시 강남구 대치동",
                "rank": 1,
                "prevRank": 2,
                "visitor": 5000,
                "rankType": "weekly",
                "statusTag": "hot",
            },
            {
                "hash": "rank_def456",
                "name": "새로운아파트",
                "sidoName": "서울특별시",
                "sigunguName": "서초구",
                "dongName": "서초동",
                "regionName": "서울특별시 서초구 서초동",
                "rank": 2,
                "prevRank": 5,
                "visitor": 3500,
                "rankType": "weekly",
                "statusTag": "rising",
            },
            {
                "hash": "rank_ghi789",
                "name": "고급아파트",
                "sidoName": "서울특별시",
                "sigunguName": "송파구",
                "dongName": "잠실동",
                "regionName": "서울특별시 송파구 잠실동",
                "rank": 3,
                "prevRank": 1,
                "visitor": 4200,
                "rankType": "weekly",
                "statusTag": None,
            },
        ]
    },
}

# Complex list API 응답 Mock 데이터
MOCK_COMPLEX_LIST_RESPONSE = {
    "success": True,
    "data": {
        "complexes": [
            {
                "complexNo": "C12345",
                "complexName": "강남역 힐스테이트",
                "address": "서울특별시 강남구 역삼동",
                "buildYear": "2018",
                "householdCount": 520,
                "dongCount": 4,
                "minFloor": 3,
                "maxFloor": 35,
                "totalDongCount": 4,
                "exclusiveAreaMin": 59.99,
                "exclusiveAreaMax": 134.98,
                "supplyAreaMin": 84.52,
                "supplyAreaMax": 169.84,
                "salePriceMin": 118000,
                "salePriceMax": 265000,
                "jeonsePriceMin": 70000,
                "jeonsePriceMax": 150000,
                "monthlyRentMin": 0,
                "monthlyRentMax": 0,
            },
            {
                "complexNo": "C67890",
                "complexName": "서초 포레스트",
                "address": "서울특별시 서초구 서초동",
                "buildYear": "2015",
                "householdCount": 350,
                "dongCount": 3,
                "minFloor": 2,
                "maxFloor": 28,
                "totalDongCount": 3,
                "exclusiveAreaMin": 49.94,
                "exclusiveAreaMax": 114.88,
                "supplyAreaMin": 66.24,
                "supplyAreaMax": 149.93,
                "salePriceMin": 95000,
                "salePriceMax": 230000,
                "jeonsePriceMin": 55000,
                "jeonsePriceMax": 130000,
                "monthlyRentMin": 0,
                "monthlyRentMax": 0,
            },
        ]
    },
}

# Complex detail API 응답 Mock 데이터
MOCK_COMPLEX_DETAIL_RESPONSE = {
    "success": True,
    "data": {
        "complexNo": "C12345",
        "complexName": "강남역 힐스테이트",
        "address": "서울특별시 강남구 역삼동 647-20",
        "buildYear": "2018",
        "householdCount": 520,
        "dongCount": 4,
        "floorInfo": {"undergroundFloor": 5, "lowestFloor": 3, "highestFloor": 35},
        "heatingType": "지역난방",
        "parking": {"total": 520, "household": 1.0},
        "elevator": {"count": 8, "servicePerElevator": 65},
        "areas": [
            {"exclusive": 59.99, "supply": 84.52, "pyeong": 18},
            {"exclusive": 84.94, "supply": 113.75, "pyeong": 26},
        ],
        "recentSales": [
            {
                "date": "2024.10.15",
                "area": 84.94,
                "floor": 15,
                "price": 185000,
                "tradeType": "매매",
            },
            {"date": "2024.10.20", "area": 59.99, "floor": 8, "price": 145000, "tradeType": "전세"},
        ],
    },
}

# Article list API 응답 Mock 데이터 (페이지네이션용)
MOCK_ARTICLE_LIST_RESPONSE = {
    "success": True,
    "data": {
        "articles": [
            {
                "articleNo": "A123456",
                "complexNo": "C12345",
                "complexName": "강남역 힐스테이트",
                "tradeType": "매매",
                "exclusiveArea": 84.94,
                "pyeong": 26,
                "floor": "15층",
                "direction": "남향",
                "price": 185000,
                "deposit": 0,
                "monthlyRent": 0,
                "manageCost": 45,
                "description": "강남역 도보 5분, 리모델링 완료",
                "regDate": "2024.10.15",
                "images": [
                    "https://image.hogangnono.com/1.jpg",
                    "https://image.hogangnono.com/2.jpg",
                ],
            },
            {
                "articleNo": "A789012",
                "complexNo": "C67890",
                "complexName": "서초 포레스트",
                "tradeType": "전세",
                "exclusiveArea": 59.99,
                "pyeong": 18,
                "floor": "8층",
                "direction": "남동향",
                "price": 0,
                "deposit": 145000,
                "monthlyRent": 0,
                "manageCost": 35,
                "description": "서초역 도보 3분, 전망 좋음",
                "regDate": "2024.10.20",
                "images": ["https://image.hogangnono.com/3.jpg"],
            },
        ],
        "pagination": {"page": 1, "totalCount": 50, "totalPage": 5, "countPerPage": 10},
    },
}

# 에러 응답 Mock 데이터
MOCK_ERROR_RESPONSE = {
    "success": False,
    "error": {"code": "INVALID_PARAMETER", "message": "유효하지 않은 파라미터입니다"},
}

# 인증 에러 응답 Mock 데이터
MOCK_AUTH_ERROR_RESPONSE = {
    "success": False,
    "error": {"code": "UNAUTHORIZED", "message": "인증이 필요합니다"},
}

# Rate limiting 에러 응답 Mock 데이터
MOCK_RATE_LIMIT_ERROR_RESPONSE = {
    "success": False,
    "error": {
        "code": "TOO_MANY_REQUESTS",
        "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요",
    },
}

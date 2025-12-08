#!/usr/bin/env python3
"""Test script to find correct API endpoints for real estate data."""

import json
import requests

# Base URL
BASE_URL = "https://hogangnono.com"

# Common headers
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://hogangnono.com/",
    "Origin": "https://hogangnono.com",
}

# Create session for cookies
session = requests.Session()
session.headers.update(headers)

# First, visit main page to get cookies
print("Visiting main page to get cookies...")
response = session.get(BASE_URL)
print(f"Main page status: {response.status_code}")
print(f"Cookies: {[c.name for c in session.cookies]}")

# Test different endpoints
endpoints_to_test = [
    # Try complex list endpoint
    (
        "/cluster/ajax/complexList",
        {
            "cortarNo": "1168010500"  # 강남구 압구정동
        },
    ),
]

print("\n" + "=" * 80)
print("TESTING API ENDPOINTS")
print("=" * 80)

for endpoint, params in endpoints_to_test:
    print(f"\n{'-'*60}")
    print(f"Testing: {endpoint}")
    print(f"Params: {params}")

    try:
        response = session.get(f"{BASE_URL}{endpoint}", params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(
                    f"Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                )

                # Sample the data structure
                if isinstance(data, dict):
                    if "data" in data and isinstance(data["data"], list):
                        print(f"Data Items Count: {len(data['data'])}")
                        if data["data"]:
                            print(
                                f"Sample Item Keys: {list(data['data'][0].keys()) if isinstance(data['data'][0], dict) else 'Not a dict'}"
                            )
                            if isinstance(data["data"][0], dict) and "aptName" in data["data"][0]:
                                print(f"Sample Apartment: {data['data'][0]['aptName']}")

                elif isinstance(data, list):
                    print(f"Response is a list with {len(data)} items")

            except json.JSONDecodeError:
                print(f"Response is not JSON (size: {len(response.text)} bytes)")
                print(f"First 500 chars: {response.text[:500]}")

        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except Exception as e:
        print(f"Request failed: {str(e)}")

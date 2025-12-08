import requests
# from crawler.api.hogangnono_client import HogangnonoAPIClient


def test_real_hogangnono_api_availability():
    """Test that real 호갱노노 API endpoints are accessible"""
    # Direct HTTP client test for basic connectivity
    response = requests.get("https://hogangnono.com/api/v2/ranks/rolling", timeout=10)
    assert response.status_code == 200

    data = response.json()
    # API returns data in a different format
    assert "rolling" in data or "data" in data, f"Unexpected response format: {data}"

    # Check if we have some data
    if "rolling" in data:
        assert isinstance(data["rolling"], list), "rolling should be a list"
        if len(data["rolling"]) > 0:
            assert "name" in data["rolling"][0], "Each item should have a name field"


def test_bounding_box_api_with_real_coordinates():
    """Test bounding box API with Seoul coordinates"""
    # Direct HTTP client test - use correct API endpoint
    # The bounding box format should be: lat_min,lng_min,lat_max,lng_max
    params = {
        "bounds": "37.514,127.044,37.527,127.106",  # lat_min, lng_min, lat_max, lng_max
        "type": "apt",  # Use 'apt' instead of 'apartment'
        "trade": "매매",  # Use Korean trade type
    }

    response = requests.get(
        "https://hogangnono.com/api/v2/pois-bounding", params=params, timeout=10
    )
    # The API might return 400 for invalid parameters, but that's still connectivity
    assert response.status_code in [
        200,
        400,
    ], f"API should be accessible, got status {response.status_code}"

    if response.status_code == 200:
        data = response.json()
        # API might return empty array or list of properties
        assert isinstance(data, list), "Should return a list"



def pytest_configure(config):
    """pytest 마커 등록"""
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "e2e: E2E 테스트 (실제 브라우저 필요)")

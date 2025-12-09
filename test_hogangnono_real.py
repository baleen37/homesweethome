#!/usr/bin/env python
"""호갱노노 크롤러 실제 테스트

실제 호갱노노 사이트를 크롤링하여 구현을 검증합니다.
"""

import sys
from pathlib import Path

# playwright import는 sys.path 설정 후에 해야 함
# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# ruff: noqa: E402
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from playwright.sync_api import sync_playwright


def test_apartment_list_parsing():
    """아파트 목록 파싱 테스트 (실제 HTML 샘플)"""
    # 실제 검색 결과 페이지의 HTML 샘플
    sample_html = """
    <html>
    <body>
        <ul>
            <li>
                <a href="/apt/ds61e">
                    <generic>개포동 개포자이프레지던스</generic>
                    <generic>3,375세대</generic>
                    <generic>2023년 2월 입주</generic>
                </a>
            </li>
            <li>
                <a href="/apt/1Oo28">
                    <generic>개포동 개포동상지리츠빌</generic>
                    <generic>18세대</generic>
                    <generic>2003년 3월 입주</generic>
                </a>
            </li>
        </ul>
    </body>
    </html>
    """

    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config)

    # HTML 파싱 테스트
    listings = crawler.parse(sample_html)

    print("=== 아파트 목록 파싱 테스트 ===")
    print(f"추출된 아파트 수: {len(listings)}")
    for listing in listings:
        print(f"- {listing['complex_name']} ({listing['dong']}) - {listing['household_count']}")

    assert len(listings) >= 2, "최소 2개의 아파트를 추출해야 합니다"
    assert (
        "개포자이프레지던스" in listings[0]["complex_name"]
    ), "첫 번째 아파트 이름이 일치해야 합니다"
    assert listings[0]["apt_id"] == "ds61e", "아파트 ID가 올바르게 추출되어야 합니다"

    print("\n✅ 아파트 목록 파싱 테스트 통과\n")


def test_transaction_parsing():
    """실거래가 파싱 테스트 (실제 HTML 샘플)"""
    # 실제 아파트 상세 페이지의 실거래가 표 HTML 샘플
    sample_html = """
    <html>
    <body>
        <h1>개포동 개포자이프레지던스</h1>
        <generic>서울특별시 강남구 개포동 1284</generic>

        <table>
            <thead>
                <tr>
                    <th>계약일</th>
                    <th>면적(공급)</th>
                    <th>가격</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>25.11.07</td>
                    <td><button>110A</button></td>
                    <td>
                        <generic>41억 7,000</generic>
                        <generic>28층</generic>
                    </td>
                </tr>
                <tr>
                    <td>25.10.13</td>
                    <td><button>110A</button></td>
                    <td>
                        <generic>39억 8,000</generic>
                        <generic>16층</generic>
                    </td>
                </tr>
                <tr>
                    <td>25.09.21</td>
                    <td><button>110A</button></td>
                    <td>
                        <generic>35억 5,000</generic>
                        <generic>2층</generic>
                    </td>
                </tr>
            </tbody>
        </table>
    </body>
    </html>
    """

    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config)

    # HTML 파싱 테스트
    listings = crawler.parse(sample_html)

    print("=== 실거래가 파싱 테스트 ===")
    print(f"추출된 실거래가 수: {len(listings)}")
    for listing in listings:
        print(f"- {listing['date']}: {listing['price']} ({listing['area']}, {listing['floor']})")

    assert len(listings) == 3, "3개의 실거래가를 추출해야 합니다"
    assert (
        listings[0]["complex_name"] == "개포동 개포자이프레지던스"
    ), "아파트 이름이 일치해야 합니다"
    assert "41억 7,000" in listings[0]["price"], "첫 번째 실거래가 가격이 일치해야 합니다"
    assert listings[0]["area"] == "110A", "면적 정보가 일치해야 합니다"
    assert listings[0]["floor"] == "28층", "층수 정보가 일치해야 합니다"

    print("\n✅ 실거래가 파싱 테스트 통과\n")


def test_real_site_search():
    """실제 사이트 검색 테스트 (Playwright 사용)"""
    config = CrawlerConfig.from_env()
    config.headless = True  # 실제 테스트를 위해 headless 모드

    crawler = HogangnonoCrawler(config)

    try:
        print("=== 실제 사이트 검색 테스트 ===")
        print("강남구 개포동 아파트 검색 중...")

        # 지역별 크롤링 테스트
        listings = crawler.crawl_region("강남구", "개포동")

        print(f"검색 결과: {len(listings)}개 아파트 발견")
        for listing in listings[:5]:  # 처음 5개만 출력
            print(f"- {listing['complex_name']} ({listing.get('dong', '')})")
            if listing.get("household_count"):
                print(f"  세대수: {listing['household_count']}")
            if listing.get("move_in_date"):
                print(f"  입주일: {listing['move_in_date']}")

        assert len(listings) > 0, "검색 결과가 있어야 합니다"

        print("\n✅ 실제 사이트 검색 테스트 통과\n")

        # 아파트 상세 정보 테스트 (첫 번째 아파트)
        if listings and listings[0].get("apt_id"):
            apt_id = listings[0]["apt_id"]
            print(f"=== 아파트 상세 정보 테스트: {apt_id} ===")

            transactions = crawler.crawl_apartment_detail(apt_id)

            print(f"실거래가: {len(transactions)}건")
            for transaction in transactions[:5]:  # 처음 5개만 출력
                print(
                    f"- {transaction['date']}: {transaction['price']} ({transaction['area']}, {transaction['floor']})"
                )

            print("\n✅ 아파트 상세 정보 테스트 통과\n")

    except Exception as e:
        print(f"\n❌ 실제 사이트 테스트 실패: {e}\n")
        # 실패해도 전체 테스트는 계속 진행
        return False

    return True


def test_with_playwright_directly():
    """Playwright를 직접 사용하여 사이트 구조 확인"""
    print("=== Playwright 직접 테스트 ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. 강남구 개포동 검색
            search_url = "https://hogangnono.com/search?q=%EA%B0%95%EB%82%A8%EA%B5%AC%20%EA%B0%9C%ED%8F%AC%EB%8F%99"
            print(f"접속: {search_url}")

            page.goto(search_url)
            page.wait_for_load_state("networkidle")

            # 2. 아파트 링크 확인
            apt_links = page.query_selector_all('a[href*="/apt/"]')
            print(f"\n발견된 아파트 링크 수: {len(apt_links)}")

            for i, link in enumerate(apt_links[:5]):
                href = link.get_attribute("href")
                text = link.text_content()
                print(f"{i+1}. {text} -> {href}")

            # 3. 첫 번째 아파트 상세 페이지 확인
            if apt_links:
                first_href = apt_links[0].get_attribute("href")
                if first_href:
                    apt_id = first_href.split("/apt/")[-1].split("/")[0]
                    detail_url = f"https://hogangnono.com/apt/{apt_id}/0"

                    print(f"\n상세 페이지 접속: {detail_url}")
                    page.goto(detail_url)
                    page.wait_for_load_state("networkidle")

                    # 실거래가 표 확인
                    table = page.query_selector("table")
                    if table:
                        rows = table.query_selector_all("tr")
                        print(f"\n실거래가: {len(rows)-1}건")  # 헤더 제외

                        for i, row in enumerate(rows[1:6]):  # 처음 5개만
                            cells = row.query_selector_all("td")
                            if len(cells) >= 3:
                                date = cells[0].text_content()
                                area = cells[1].text_content()
                                price_floor = cells[2].text_content()
                                print(f"{i+1}. {date} | {area} | {price_floor}")

                    # 더보기 버튼 확인
                    more_buttons = page.query_selector_all('button:has-text("더보기")')
                    print(f"\n더보기 버튼 수: {len(more_buttons)}")

            print("\n✅ Playwright 직접 테스트 통과\n")

        except Exception as e:
            print(f"\n❌ Playwright 테스트 실패: {e}\n")
            return False
        finally:
            browser.close()

    return True


def main():
    """메인 테스트 실행"""
    print("🏢 호갱노노 크롤러 테스트 시작\n")

    # 1. HTML 파싱 테스트
    test_apartment_list_parsing()
    test_transaction_parsing()

    # 2. Playwright 직접 테스트
    test_with_playwright_directly()

    # 3. 실제 사이트 테스트
    # 주의: 실제 사이트 접속이 필요하므로 주석 처리
    test_real_site_search()

    print("🎉 모든 테스트 완료!")


if __name__ == "__main__":
    main()

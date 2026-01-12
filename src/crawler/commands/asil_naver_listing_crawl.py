"""ASIL 아파트 목록 → Naver 매칭 → 매물 크롤링 CLI"""

import time
from collections.abc import Sequence
from pathlib import Path

from crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler
from crawler.commands.cli_common import (
    add_all_argument,
    add_output_argument,
    create_dong_code_parser,
    resolve_dong_codes,
)
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.export.csv_export import (
    export_matched_apts_to_csv,
    export_naver_articles_with_apt_seq,
)
from crawler.matching.asil_naver_matcher import AsilNaverMatcher
from crawler.matching.dto import MatchMethod
from crawler.naver_cluster_api import NaverClusterAPIClient
from crawler.naver_listing_crawler import NaverListingCrawler


class RateLimit:
    """Rate Limiting 상수 (네이버 Abuse 방지)"""

    BETWEEN_APTS = 3.0  # 각 아파트 처리 후 3초 대기 (Abuse 방지)


def deduplicate_listings(
    listings: Sequence[NaverArticleItemDTO],
) -> list[NaverArticleItemDTO]:
    """매물 ID 기준 중복 제거

    Args:
        listings: 매물 DTO 리스트

    Returns:
        중복 제거된 매물 리스트
    """
    seen = set()
    unique_listings = []

    for listing in listings:
        atcl_no = listing.atcl_no
        if atcl_no not in seen:
            seen.add(atcl_no)
            unique_listings.append(listing)

    return unique_listings


def crawl_asil_to_naver_listings(
    dong_codes: list[str],
    output_path: Path,
    radius_m: int = 500,
    max_apts: int | None = None,
) -> int:
    """
    ASIL 아파트 목록 → Naver 매칭 → 매물 크롤링

    Args:
        dong_codes: 법정동 코드 리스트
        output_path: 출력 CSV 경로 (확장자 제거한 기본 경로)
        radius_m: 매물 검색 반경 (기본 500m)
        max_apts: 최대 처리할 아파트 수 (None이면 모든 아파트 처리)

    Returns:
        크롤링한 매물 수
    """
    all_listings: list[NaverArticleItemDTO] = []
    matched_apts_list: list[AsilAptListDTO] = []
    total_apts = 0
    matched_apts = 0
    skipped_no_coord = 0
    skipped_no_match = 0
    errors = 0

    for dong_code in dong_codes:
        print(f"동 코드 {dong_code} 조회 중...")

        # 1. ASIL 목록 크롤링
        apt_crawler = AsilAptListCrawler(dong_code=dong_code)
        apt_list = apt_crawler.crawl()

        if not apt_list:
            print("  - 데이터 없음")
            continue

        print(f"  - {len(apt_list)}개 아파트 찾음")

        # 2. 각 아파트별 Naver 매칭 및 매물 크롤링
        for apt in apt_list:
            # max_apts 체크
            if max_apts is not None and matched_apts >= max_apts:
                print(f"  - 최대 {max_apts}개 아파트 처리 완료, 중단")
                break

            total_apts += 1
            apt_name = getattr(apt, "name", "")
            apt_seq = getattr(apt, "seq", "")
            lat = getattr(apt, "lat", 0)
            lng = getattr(apt, "lng", 0)

            print(f"    - [{apt_name}] 매칭 중...")

            # 좌표가 없으면 스킵 (문자열 0 또는 숫자 0 체크)
            try:
                lat_f = float(lat) if lat else 0
                lng_f = float(lng) if lng else 0
            except (ValueError, TypeError):
                print("      - 좌표 변환 실패, 스킵")
                skipped_no_coord += 1
                continue

            if lat_f == 0 or lng_f == 0:
                print("      - 좌표 없음, 스킵")
                skipped_no_coord += 1
                continue

            # Naver Cluster API로 매칭 (법정동 코드 필터링 포함)
            cluster_client = NaverClusterAPIClient(
                lat=lat_f,
                lon=lng_f,
                bottom=lat_f - 0.005,  # 약 550m
                left=lng_f - 0.005,  # 약 450m (서울 위도 기준)
                top=lat_f + 0.005,
                right=lng_f + 0.005,
                cortar_no=apt.dong,  # 법정동 코드 필터링
                zoom=15,
            )

            try:
                # Naver Cluster API 호출
                url = cluster_client.build_url(page=1)
                response_json = cluster_client.fetch(url)
                cluster_response = cluster_client.parse_response(response_json)
                articles = cluster_response.articles

                if not articles:
                    print("      - Naver 매칭 실패 (매물 없음), 스킵")
                    skipped_no_match += 1
                    continue

                # 2단계 매칭: 좌표 기반 + 이름 퍼지 서치
                match_result = AsilNaverMatcher.match_by_coordinate(apt, articles)

                # 좌표 매칭 실패 시 이름 퍼지 매칭 시도
                if match_result is None:
                    match_result = AsilNaverMatcher.match_by_fuzzy_name(apt, articles)

                if match_result is None:
                    print(
                        f"      - Naver 매칭 실패 (좌표/이름 매칭 실패), "
                        f"후보 수: {len(articles)}, 스킵"
                    )
                    skipped_no_match += 1
                    continue

                # 원래 좌표 매칭 결과 저장 (이름 매칭 우선 시 좌표 계산용)
                original_match_result = match_result

                # 좌표 기반 매칭 시 이름 유사도 추가 검증
                if match_result.method == MatchMethod.COORDINATE:
                    # 매칭된 아파트 이름 유사도 계산
                    name_match = AsilNaverMatcher.match_by_fuzzy_name(apt, articles)
                    if name_match and name_match.confidence >= 0.8:
                        # 이름이 매우 유사하면 이름 매칭 결과 사용
                        if name_match.naver_apt_code != match_result.naver_apt_code:
                            print(
                                f"      - 이름 매칭 우선: {name_match.naver_apt_name} "
                                f"(유사도: {name_match.confidence:.2f})"
                            )
                            match_result = name_match

                # 원래 좌표 매칭 결과로 매물 찾기 (좌표가 필요하므로)
                matched_article = next(
                    (a for a in articles if a.atcl_no == original_match_result.naver_apt_code),
                    None,
                )

                if matched_article is None:
                    print("      - 매칭된 매물을 찾을 수 없음, 스킵")
                    skipped_no_match += 1
                    continue

                matched_lat = matched_article.lat
                matched_lng = matched_article.lng

                # 좌표가 None이면 스킵
                if matched_lat is None or matched_lng is None:
                    print("      - 좌표 없음, 스킵")
                    skipped_no_match += 1
                    continue

                # 거리 정보 포맷팅 (이름 매칭 시 distance_m이 None일 수 있음)
                distance_str = (
                    f"{original_match_result.distance_m:.1f}m"
                    if original_match_result.distance_m is not None
                    else "N/A"
                )
                print(
                    f"      - Naver 매칭 성공: {match_result.naver_apt_name} "
                    f"(거리: {distance_str}, "
                    f"신뢰도: {match_result.confidence:.2f}, "
                    f"좌표: {matched_lat}, {matched_lng})"
                )
                matched_apts += 1

                # ASIL 실거래가 조회
                try:
                    trade_crawler = AsilTradePriceCrawler(
                        apt_code=apt_seq,
                        sido_code="11",
                        area_m2=84,
                    )
                    trade_prices = trade_crawler.crawl()
                    if trade_prices:
                        trade_price = trade_prices[0]
                        # 실거래가 요약 정보를 apt에 추가
                        apt.date_m = trade_price.date_m
                        apt.date_j = trade_price.date_j
                        apt.max_m = trade_price.max_m
                        apt.max_j = trade_price.max_j
                        apt.price_total = trade_price.price_total
                        print(
                            f"      - 실거래가: 최근매매({trade_price.date_m}), "
                            f"최근전세({trade_price.date_j})"
                        )
                except Exception as e:
                    print(f"      - 실거래가 조회 실패: {e}")

                # 매칭된 아파트 저장
                matched_apts_list.append(apt)

                # 3. ASIL 아파트 좌표로 Naver 매물 크롤링 (매칭된 매물 좌표가 아님)
                listing_crawler = NaverListingCrawler(
                    lat=lat_f,  # ASIL 아파트의 원래 좌표 사용
                    lon=lng_f,
                    radius_m=radius_m,
                )

                listings = listing_crawler.crawl_listings(max_pages=1)

                if listings:
                    print(f"      - {len(listings)}개 매물 찾음")
                    # apt_seq 설정
                    for listing in listings:
                        listing.apt_seq = apt_seq
                    all_listings.extend(listings)
                else:
                    print("      - 매물 없음")

            except ValueError as e:
                # JSON 파싱 실패 (abuse 감지 후 Playwright 우회 실패 등)
                print(f"      - Naver API 응답 파싱 실패: {e}")
                skipped_no_match += 1
                continue
            except Exception as e:
                print(f"      - 에러 발생: {e}")
                errors += 1
                continue

            # Rate limiting: 각 아파트 처리 후 대기
            time.sleep(RateLimit.BETWEEN_APTS)

    # 중복 제거
    before_count = len(all_listings)
    all_listings = deduplicate_listings(all_listings)
    after_count = len(all_listings)
    removed = before_count - after_count

    # CSV 내보내기 (두 개의 시트)
    # 1. 아파트 목록 시트
    apts_output_path = output_path.with_name(f"{output_path.stem}_apts.csv")
    export_matched_apts_to_csv(matched_apts_list, apts_output_path)

    # 2. 매물 시트
    articles_output_path = output_path.with_name(f"{output_path.stem}_articles.csv")
    export_naver_articles_with_apt_seq(all_listings, articles_output_path)

    print("\n=== 크롤링 완료 ===")
    print(f"전체 아파트: {total_apts}개")
    print(f"매칭 성공: {matched_apts}개")
    print(f"스킵 (좌표 없음): {skipped_no_coord}개")
    print(f"스킵 (매칭 실패): {skipped_no_match}개")
    print(f"에러: {errors}개")
    print(f"중복 제거: {removed}개 ({before_count} → {after_count})")
    print(f"완료: {len(matched_apts_list)}개 아파트 → {apts_output_path}")
    print(f"완료: {after_count}개 매물 → {articles_output_path}")

    return after_count


def main() -> None:
    """CLI 메인 함수"""
    parser = create_dong_code_parser(
        description="ASIL 아파트 목록 → Naver 매칭 → 매물 크롤링\n\n"
        "ASIL에서 법정동별 아파트 목록을 추출하고, 각 아파트를 Naver Cluster API로 매칭한 후,\n"
        "매칭된 아파트 주변의 네이버 매물을 크롤링합니다."
    )

    add_all_argument(parser)
    add_output_argument(
        parser,
        default="output/asil_naver_listings.csv",
        help="출력 CSV 경로 (기본값: output/asil_naver_listings.csv)",
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=500,
        help="매물 검색 반경 (미터, 기본값: 500)",
    )

    args = parser.parse_args()

    # 동 코드 결정
    dong_codes = resolve_dong_codes(args)

    # 출력 경로
    output_path = Path(args.output)

    # 크롤링 실행
    crawl_asil_to_naver_listings(
        dong_codes=dong_codes,
        output_path=output_path,
        radius_m=args.radius,
    )


if __name__ == "__main__":
    main()

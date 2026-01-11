"""CSV 내보내기 유틸리티"""

import csv
from pathlib import Path

from src.crawler.dto.asil_apt_list import AsilAptListDTO
from src.crawler.dto.asil_trade_price import AsilTradePriceDTO
from src.crawler.dto.naver_article import NaverArticleItemDTO


def export_apt_list_to_csv(
    data: list[AsilAptListDTO],
    output_path: Path,
) -> None:
    """
    아파트 기본정보를 CSV로 내보냅니다.

    CSV 필드: seq, name, dong, dongname, build_year, household, lat, lng

    Args:
        data: 아파트 기본정보 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seq",
        "name",
        "dong",
        "dongname",
        "build_year",
        "household",
        "lat",
        "lng",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for apt in data:
            row = {
                "seq": apt.seq,
                "name": apt.name,
                "dong": apt.dong,
                "dongname": apt.dongname,
                "build_year": apt.build_year or "",
                "household": apt.household or "",
                "lat": apt.lat or "",
                "lng": apt.lng or "",
            }
            writer.writerow(row)


def export_trade_price_to_csv(
    data: list[tuple[str, list[AsilTradePriceDTO]]],
    output_path: Path,
) -> None:
    """
    실거래가 정보를 CSV로 내보냅니다.

    CSV 필드: apt_seq, yyyymm, day, money, rent, floor, type

    Args:
        data: (apt_seq, 실거래가 리스트) 튜플 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "apt_seq",
        "yyyymm",
        "day",
        "money",
        "rent",
        "floor",
        "type",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for apt_seq, trade_prices in data:
            for trade_price in trade_prices:
                if not trade_price.val:
                    continue

                for month in trade_price.val:
                    if not month.val:
                        continue

                    for day in month.val:
                        if not day.val:
                            continue

                        for detail in day.val:
                            row = {
                                "apt_seq": apt_seq,
                                "yyyymm": month.yyyymm or "",
                                "day": day.day or "",
                                "money": detail.money or "",
                                "rent": detail.rent or "",
                                "floor": detail.floor or "",
                                "type": detail.type or "",
                            }
                            writer.writerow(row)


def export_naver_articles_to_csv(
    data: list[NaverArticleItemDTO],
    output_path: Path,
) -> None:
    """
    네이버 부동산 매물 정보를 CSV로 내보냅니다.

    CSV 필드: atcl_no, cortar_no, atcl_nm, rlet_tp_nm, trad_tp_nm, prc, rent_prc,
              flr_info, spc1, spc2, direction, atcl_cfm_ymd, lat, lng, atcl_fetr_desc, bild_nm

    Args:
        data: 네이버 매물 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "atcl_no",
        "cortar_no",
        "atcl_nm",
        "rlet_tp_nm",
        "trad_tp_nm",
        "prc",
        "rent_prc",
        "flr_info",
        "spc1",
        "spc2",
        "direction",
        "atcl_cfm_ymd",
        "lat",
        "lng",
        "atcl_fetr_desc",
        "bild_nm",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for article in data:
            row = {
                "atcl_no": article.atcl_no,
                "cortar_no": article.cortar_no,
                "atcl_nm": article.atcl_nm,
                "rlet_tp_nm": article.rlet_tp_nm,
                "trad_tp_nm": article.trad_tp_nm,
                "prc": article.prc or "",
                "rent_prc": article.rent_prc or "",
                "flr_info": article.flr_info,
                "spc1": article.spc1,
                "spc2": article.spc2,
                "direction": article.direction or "",
                "atcl_cfm_ymd": article.atcl_cfm_ymd or "",
                "lat": article.lat or "",
                "lng": article.lng or "",
                "atcl_fetr_desc": article.atcl_fetr_desc,
                "bild_nm": article.bild_nm,
            }
            writer.writerow(row)


def export_naver_articles_with_apt_seq(
    data: list[NaverArticleItemDTO],
    output_path: Path,
) -> None:
    """
    네이버 부동산 매물 정보를 CSV로 내보냅니다 (apt_seq 포함).

    CSV 필드: apt_seq, atcl_no, cortar_no, atcl_nm, rlet_tp_nm, trad_tp_nm, prc, rent_prc,
              flr_info, spc1, spc2, direction, atcl_cfm_ymd, lat, lng, atcl_fetr_desc, bild_nm

    Args:
        data: 네이버 매물 리스트 (apt_seq 필드 포함)
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "apt_seq",
        "atcl_no",
        "cortar_no",
        "atcl_nm",
        "rlet_tp_nm",
        "trad_tp_nm",
        "prc",
        "rent_prc",
        "flr_info",
        "spc1",
        "spc2",
        "direction",
        "atcl_cfm_ymd",
        "lat",
        "lng",
        "atcl_fetr_desc",
        "bild_nm",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for article in data:
            row = {
                "apt_seq": article.apt_seq or "",
                "atcl_no": article.atcl_no,
                "cortar_no": article.cortar_no,
                "atcl_nm": article.atcl_nm,
                "rlet_tp_nm": article.rlet_tp_nm,
                "trad_tp_nm": article.trad_tp_nm,
                "prc": article.prc or "",
                "rent_prc": article.rent_prc or "",
                "flr_info": article.flr_info,
                "spc1": article.spc1,
                "spc2": article.spc2,
                "direction": article.direction or "",
                "atcl_cfm_ymd": article.atcl_cfm_ymd or "",
                "lat": article.lat or "",
                "lng": article.lng or "",
                "atcl_fetr_desc": article.atcl_fetr_desc,
                "bild_nm": article.bild_nm,
            }
            writer.writerow(row)


def export_matched_apts_to_csv(
    data: list[AsilAptListDTO],
    output_path: Path,
) -> None:
    """
    ASIL-Naver 매칭 아파트 목록을 CSV로 내보냅니다.

    CSV 필드: seq, name, dong, dongname, build_year, household, lat, lng,
    date_m, date_j, max_m, max_j, price_total

    Args:
        data: ASIL 아파트 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seq",
        "name",
        "dong",
        "dongname",
        "build_year",
        "household",
        "lat",
        "lng",
        "date_m",
        "date_j",
        "max_m",
        "max_j",
        "price_total",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for apt in data:
            row = {
                "seq": apt.seq,
                "name": apt.name,
                "dong": apt.dong,
                "dongname": apt.dongname,
                "build_year": apt.build_year or "",
                "household": apt.household or "",
                "lat": apt.lat or "",
                "lng": apt.lng or "",
                "date_m": apt.date_m or "",
                "date_j": apt.date_j or "",
                "max_m": apt.max_m or "",
                "max_j": apt.max_j or "",
                "price_total": apt.price_total or "",
            }
            writer.writerow(row)

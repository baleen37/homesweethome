#!/usr/bin/env python
"""Script to crawl data using working Hogangnono APIs."""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import structlog

from crawler.config import CrawlerConfig
from crawler.crawlers.working_hogangnono import WorkingHogangnonoCrawler
from crawler.writers.csv_writer import CSVWriter


logger = structlog.get_logger()


def crawl_popular_apartments(crawler: WorkingHogangnonoCrawler, output_dir: Path):
    """Crawl popular apartment rankings."""
    logger.info("Crawling popular apartments...")

    # Fetch data
    data = crawler.fetch_popular_apartments()

    # Parse to CSV format
    csv_data = crawler.parse_to_csv_format(data, "apartments")

    # Save
    output_path = output_dir / "popular_apartments.csv"
    writer = CSVWriter(output_path)
    writer.write(csv_data)

    logger.info(f"Saved {len(csv_data)} popular apartments to {output_path}")
    return csv_data


def crawl_pois_in_area(
    crawler: WorkingHogangnonoCrawler, area_name: str, bbox: Dict[str, float], output_dir: Path
) -> List[Dict]:
    """Crawl POIs in a specific area."""
    logger.info(f"Crawling POIs in {area_name}...", bbox=bbox)

    # Fetch data
    data = crawler.fetch_pois_in_area(bbox)

    # Parse to CSV format
    csv_data = crawler.parse_to_csv_format(data, "pois")

    # Add area name to each POI
    for poi in csv_data:
        poi["영역"] = area_name

    # Save
    output_path = output_dir / f"pois_{area_name.lower()}.csv"
    writer = CSVWriter(output_path)
    writer.write(csv_data)

    logger.info(f"Saved {len(csv_data)} POIs from {area_name} to {output_path}")
    return csv_data


def get_predefined_areas() -> Dict[str, Dict[str, float]]:
    """Get predefined areas for crawling."""
    return {
        "gangnam": {
            "startX": 127.02,
            "endX": 127.07,
            "startY": 37.50,
            "endY": 37.53,
            "description": "강남구 역삼동, 청담동 일대",
        },
        "pangyo": {
            "startX": 127.10,
            "endX": 127.12,
            "startY": 37.39,
            "endY": 37.40,
            "description": "경기도 성남시 분당구 판교역 일대",
        },
        "songpa": {
            "startX": 127.10,
            "endX": 127.15,
            "startY": 37.48,
            "endY": 37.52,
            "description": "송파구 잠실, 가락동 일대",
        },
        "seocho": {
            "startX": 127.00,
            "endX": 127.04,
            "startY": 37.47,
            "endY": 37.50,
            "description": "서초구 서초동, 교대 일대",
        },
        "yeouido": {
            "startX": 126.91,
            "endX": 126.93,
            "startY": 37.52,
            "endY": 37.54,
            "description": "영등포구 여의도 일대",
        },
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Crawl data from working Hogangnono APIs")

    parser.add_argument(
        "--output", "-o", default="output", help="Output directory (default: output)"
    )

    parser.add_argument(
        "--areas",
        nargs="+",
        choices=["all"] + list(get_predefined_areas().keys()),
        default=["gangnam"],
        help="Areas to crawl (default: gangnam)",
    )

    parser.add_argument(
        "--popular-apartments", action="store_true", help="Crawl popular apartment rankings"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10)  # DEBUG level
        )

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    # Initialize crawler
    config = CrawlerConfig.from_env()
    crawler = WorkingHogangnonoCrawler(config)

    # Results summary
    results = {"popular_apartments": 0, "pois": {}}

    # Crawl popular apartments
    if args.popular_apartments:
        try:
            apartments = crawl_popular_apartments(crawler, output_dir)
            results["popular_apartments"] = len(apartments)
        except Exception as e:
            logger.error("Failed to crawl popular apartments", error=str(e))

    # Crawl POIs in specified areas
    areas = get_predefined_areas()
    if "all" in args.areas:
        areas_to_crawl = areas.keys()
    else:
        areas_to_crawl = args.areas

    all_pois = []

    for area_name in areas_to_crawl:
        if area_name not in areas:
            logger.warning(f"Unknown area: {area_name}")
            continue

        try:
            pois = crawl_pois_in_area(crawler, area_name, areas[area_name], output_dir)
            all_pois.extend(pois)
            results["pois"][area_name] = len(pois)
        except Exception as e:
            logger.error(f"Failed to crawl POIs in {area_name}", error=str(e))
            results["pois"][area_name] = 0

    # Save all POIs combined
    if all_pois:
        combined_path = output_dir / "all_pois_combined.csv"
        writer = CSVWriter(combined_path)
        writer.write(all_pois)
        logger.info(f"Saved combined POI data to {combined_path}")
        results["total_pois"] = len(all_pois)

    # Save summary
    summary_path = output_dir / "crawl_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 50)
    print("Crawling Summary:")
    print(f"- Popular apartments: {results['popular_apartments']}")
    print(f"- Total POIs: {results.get('total_pois', 0)}")

    if results["pois"]:
        print("\nPOIs by area:")
        for area, count in results["pois"].items():
            area_info = areas.get(area, {})
            desc = area_info.get("description", "")
            print(f"  - {area}: {count} POIs {f'({desc})' if desc else ''}")

    print(f"\nOutput directory: {output_dir.absolute()}")
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()

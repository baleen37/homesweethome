"""Enhanced CSV strategy for Hogangnono using dataclasses."""

import csv
from typing import List, Dict, Any
from pathlib import Path

from src.crawler.models import ApartmentComplex, PoiData


class EnhancedHogangnonoComplexStrategy:
    """Enhanced strategy for writing apartment complex data to CSV using dataclasses."""

    def __init__(self):
        """Initialize the strategy."""
        self.headers = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "address",
            "dong_name",  # This is the critical field that was missing!
            "lat",
            "lng",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
            "min_area",
            "max_area",
            "pyeong_types",
            "deal_count",
            "lease_count",
            "rent_count",
            "fetched_at",
        ]

    def get_csv_headers(self) -> List[str]:
        """Get the CSV headers."""
        return self.headers

    def write_apartments_to_csv(self, complexes: List[ApartmentComplex], file_path: str) -> None:
        """Write a list of ApartmentComplex objects to CSV file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, mode="w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.headers)
            writer.writeheader()

            for complex in complexes:
                row = self._complex_to_dict(complex)
                writer.writerow(row)

    def _complex_to_dict(self, complex: ApartmentComplex) -> Dict[str, Any]:
        """Convert ApartmentComplex to dictionary matching CSV headers."""
        return {
            "complex_id": complex.complex_id,
            "complex_name": complex.complex_name,
            "real_estate_type": complex.real_estate_type,
            "address": complex.address,
            "dong_name": complex.dong_name,  # Now properly included!
            "lat": complex.lat,
            "lng": complex.lng,
            "completion_year_month": complex.completion_year_month,
            "total_dong_count": complex.total_dong_count,
            "total_household_count": complex.total_household_count,
            "min_area": complex.min_area,
            "max_area": complex.max_area,
            "pyeong_types": complex.pyeong_types,
            "deal_count": complex.deal_count,
            "lease_count": complex.lease_count,
            "rent_count": complex.rent_count,
            "fetched_at": complex.fetched_at,
        }

    @staticmethod
    def create_from_poi_data_list(poi_list: List[Dict[str, Any]]) -> List[ApartmentComplex]:
        """Create a list of ApartmentComplex from POI data list."""
        complexes = []

        for poi_data in poi_list:
            # First create PoiData from the raw dict
            poi = PoiData.from_api_response(poi_data)

            # Then convert to ApartmentComplex
            complex = ApartmentComplex.from_poi_data(poi)
            complexes.append(complex)

        return complexes

    def process_and_save_poi_data(
        self, poi_data_list: List[Dict[str, Any]], file_path: str
    ) -> None:
        """Process POI data list and save to CSV."""
        # Convert POI data to ApartmentComplex objects
        complexes = self.create_from_poi_data_list(poi_data_list)

        # Write to CSV
        self.write_apartments_to_csv(complexes, file_path)

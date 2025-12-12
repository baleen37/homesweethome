"""CSV writer that handles dataclass objects directly

This module provides CSV writers that can handle dataclass objects
and convert them to CSV format with proper validation.
"""

from pathlib import Path
from typing import Dict, List, Optional
import structlog

from crawler.models.api_responses import ComplexInfo, POIInfo
from crawler.models.csv_models import ComplexCSVRow, TransactionCSVRow

logger = structlog.get_logger().bind(component="DataclassCSVWriter")


class DataclassComplexCSVWriter:
    """CSV writer that handles ComplexInfo dataclass objects

    This writer converts ComplexInfo objects to CSV format with proper
    validation and type safety.
    """

    def __init__(self, output_path: Path) -> None:
        """Initialize the writer

        Args:
            output_path: Path to the output CSV file
        """
        self.output_path = output_path
        self.logger = structlog.get_logger().bind(component="DataclassComplexCSVWriter")

    def write_complex_info(self, complex_infos: List[ComplexInfo]) -> None:
        """Write ComplexInfo objects to CSV

        Args:
            complex_infos: List of ComplexInfo objects to write
        """
        if not complex_infos:
            self.logger.info("no_data_to_write")
            return

        # Convert ComplexInfo objects to CSV rows
        csv_rows = []
        for complex_info in complex_infos:
            try:
                csv_row = ComplexCSVRow.from_complex_info(complex_info)
                csv_rows.append(csv_row.to_dict())
            except Exception as e:
                self.logger.error(
                    "complex_to_csv_failed", complex_id=complex_info.id, error=str(e), exc_info=True
                )

        # Write using base CSV writer
        from crawler.writers.hogangnono_complexes_writer import HogangnonoComplexesCSVWriter

        base_writer = HogangnonoComplexesCSVWriter(self.output_path)
        base_writer.write(csv_rows)

        self.logger.info(
            "complex_info_written", count=len(csv_rows), output_path=str(self.output_path)
        )

    def write_poi_info(
        self, poi_infos: List[POIInfo], validation_results: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """Write POIInfo objects to CSV with validation results

        Args:
            poi_infos: List of POIInfo objects to write
            validation_results: Optional list of validation results for each POI
        """
        if not poi_infos:
            self.logger.info("no_data_to_write")
            return

        # Convert POIInfo objects to CSV rows
        csv_rows = []
        for i, poi_info in enumerate(poi_infos):
            try:
                # Get validation result if provided
                validation_result = ""
                validation_reason = ""
                if validation_results and i < len(validation_results):
                    validation_result = validation_results[i].get("result", "")
                    validation_reason = validation_results[i].get("reason", "")

                csv_row = ComplexCSVRow.from_poi_info(
                    poi_info,
                    validation_result=validation_result,
                    validation_reason=validation_reason,
                )
                csv_rows.append(csv_row.to_dict())
            except Exception as e:
                self.logger.error(
                    "poi_to_csv_failed", poi_id=poi_info.id, error=str(e), exc_info=True
                )

        # Write using base CSV writer
        from crawler.writers.hogangnono_complexes_writer import HogangnonoComplexesCSVWriter

        base_writer = HogangnonoComplexesCSVWriter(self.output_path)
        base_writer.write(csv_rows)

        self.logger.info("poi_info_written", count=len(csv_rows), output_path=str(self.output_path))


class DataclassTransactionCSVWriter:
    """CSV writer that handles transaction data from ComplexInfo objects

    This writer extracts transaction information from ComplexInfo objects
    and writes it to CSV format.
    """

    def __init__(self, output_path: Path) -> None:
        """Initialize the writer

        Args:
            output_path: Path to the output CSV file
        """
        self.output_path = output_path
        self.logger = structlog.get_logger().bind(component="DataclassTransactionCSVWriter")

    def write_from_complex_infos(self, complex_infos: List[ComplexInfo]) -> None:
        """Extract and write transaction data from ComplexInfo objects

        Args:
            complex_infos: List of ComplexInfo objects containing transaction data
        """
        if not complex_infos:
            self.logger.info("no_data_to_write")
            return

        # Convert ComplexInfo objects to transaction CSV rows
        csv_rows = []
        for complex_info in complex_infos:
            try:
                transaction_rows = TransactionCSVRow.from_complex_info(complex_info)
                for row in transaction_rows:
                    csv_rows.append(row.to_dict())
            except Exception as e:
                self.logger.error(
                    "complex_to_transaction_csv_failed",
                    complex_id=complex_info.id,
                    error=str(e),
                    exc_info=True,
                )

        # Write using base CSV writer
        from crawler.writers.hogangnono_transactions_writer import HogangnonoTransactionsCSVWriter

        base_writer = HogangnonoTransactionsCSVWriter(self.output_path)
        base_writer.write(csv_rows)

        self.logger.info(
            "transaction_info_written", count=len(csv_rows), output_path=str(self.output_path)
        )


class DataclassCSVWriterFactory:
    """Factory for creating appropriate dataclass CSV writers"""

    @staticmethod
    def create_complex_writer(output_path: Path) -> DataclassComplexCSVWriter:
        """Create a complex info CSV writer

        Args:
            output_path: Path to the output CSV file

        Returns:
            DataclassComplexCSVWriter instance
        """
        return DataclassComplexCSVWriter(output_path)

    @staticmethod
    def create_transaction_writer(output_path: Path) -> DataclassTransactionCSVWriter:
        """Create a transaction CSV writer

        Args:
            output_path: Path to the output CSV file

        Returns:
            DataclassTransactionCSVWriter instance
        """
        return DataclassTransactionCSVWriter(output_path)

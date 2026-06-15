import csv
import logging

logger = logging.getLogger()


def parse_csv_rows(csv_path: str) -> list[dict[str, str]]:
    """Parse a CSV file path into a list of rows keyed by column name, preserving structure."""
    try:
        with open(csv_path, newline="", encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file))
    except Exception as e:
        logger.error(f"Failed to parse CSV rows: {e}")
        raise e

"""Utility functions for working with datasets."""

from typing import TYPE_CHECKING, List, Optional

from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest

if TYPE_CHECKING:
    from db_models.dataset_models import DatabaseDatasetVersionRow


def dataset_row_matches_filter(
    db_row: "DatabaseDatasetVersionRow",
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]],
) -> bool:
    """Check if a dataset row matches all filter conditions (AND logic).

    Args:
        db_row: The database row to check
        dataset_row_filter: Optional list of column name and value filters.
            If None or empty, returns True (all rows match).

    Returns:
        True if the row matches all filter conditions, False otherwise.
        If no filter is provided, returns True.

    Note:
        Row must match ALL filter conditions to be included (AND logic).
        Both row values and filter values are converted to strings for comparison
        since row data can be any JSON type (int, bool, etc.) but filter values
        are always strings per the schema.
    """
    if not dataset_row_filter:
        return True  # No filter means all rows match

    # Row must match ALL filter conditions to be included
    for filter_condition in dataset_row_filter:
        row_value = db_row.data.get(filter_condition.column_name)
        # Convert both to strings for comparison since row data can be any JSON type
        # (int, bool, etc.) but filter values are always strings per the schema
        if str(row_value) != str(filter_condition.column_value):
            return False
    return True

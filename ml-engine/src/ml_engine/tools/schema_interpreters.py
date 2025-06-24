from arthur_client.api_bindings import AvailableDataset, Dataset
from arthur_common.models.schema_definitions import ScopeSchemaTag
from tools.converters import client_to_common_dataset_schema


def primary_timestamp_col_name(dataset: Dataset | AvailableDataset) -> str:
    """Retrieves name of primary timestamp tagged column, raises error if there is none."""
    missing_col_msg = (
        f"Could not find primary timestamp column in dataset schema. Inference timestamp column should "
        f"have the {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag."
    )
    if not dataset.dataset_schema:
        raise ValueError(missing_col_msg)

    dataset_schema = client_to_common_dataset_schema(dataset.dataset_schema)
    for col in dataset_schema.columns:
        if (
            col.definition
            and col.definition.tag_hints
            and ScopeSchemaTag.PRIMARY_TIMESTAMP in col.definition.tag_hints
        ):
            return col.source_name
    raise ValueError(missing_col_msg)

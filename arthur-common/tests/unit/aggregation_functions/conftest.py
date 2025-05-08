import os
from uuid import uuid4

import duckdb
import pandas as pd
import pytest
from arthur_common.models.metrics import DatasetReference
from arthur_common.tools.duckdb_data_loader import DuckDBOperator
from arthur_common.tools.schema_inferer import SchemaInferer
from duckdb import DuckDBPyConnection


def _get_dataset(name: str) -> pd.DataFrame | list[dict]:
    current_dir = os.path.dirname(__file__)
    if name == "balloons":
        csv_path = os.path.join(current_dir, "../../test_data/balloons/flights.csv")
    elif name == "networking":
        csv_path = os.path.join(
            current_dir,
            "../../test_data/networking/network_packets_dataset.csv",
        )
    elif name == "electricity":
        csv_path = os.path.join(
            current_dir,
            "../../test_data/electricity/energy_dataset.csv",
        )
    elif name == "vehicles":
        csv_path = os.path.join(
            current_dir,
            "../../test_data/vehicles/vehicle_classification_data.csv",
        )
    else:
        raise ValueError(f"Dataset {name} doesn't exist.")
    data = pd.read_csv(csv_path)

    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.max_columns", None)

    schema = SchemaInferer(data).infer_schema()
    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        table_name="inferences",
        schema=schema,
    )
    DuckDBOperator.apply_alias_mask(table_name="inferences", conn=conn, schema=schema)
    return conn


@pytest.fixture
def get_balloons_dataset_conn() -> tuple[DuckDBPyConnection, DatasetReference]:
    conn = _get_dataset("balloons")
    dataset_reference = DatasetReference(
        dataset_name="balloons",
        dataset_table_name="inferences",
        dataset_id=uuid4(),
    )
    return conn, dataset_reference


@pytest.fixture
def get_networking_dataset_conn() -> tuple[DuckDBPyConnection, DatasetReference]:
    conn = _get_dataset("networking")
    dataset_reference = DatasetReference(
        dataset_name="networking",
        dataset_table_name="inferences",
        dataset_id=uuid4(),
    )
    return conn, dataset_reference


@pytest.fixture
def get_vehicle_dataset_conn() -> tuple[DuckDBPyConnection, DatasetReference]:
    conn = _get_dataset("vehicles")
    dataset_reference = DatasetReference(
        dataset_name="vehicles",
        dataset_table_name="inferences",
        dataset_id=uuid4(),
    )
    return conn, dataset_reference


@pytest.fixture
def get_electricity_dataset_conn() -> tuple[DuckDBPyConnection, DatasetReference]:
    conn = _get_dataset("electricity")
    dataset_reference = DatasetReference(
        dataset_name="electricity",
        dataset_table_name="inferences",
        dataset_id=uuid4(),
    )
    return conn, dataset_reference


@pytest.fixture
def get_shield_dataset_conn() -> tuple[DuckDBPyConnection, DatasetReference]:
    """Create a test database with Shield inference data.

    Returns:
        tuple: (DuckDB connection, DatasetReference)
    """
    conn = duckdb.connect(":memory:")
    dataset_ref = DatasetReference(
        dataset_name="shield_dataset",
        dataset_table_name="shield_test_data",
        dataset_id="test-dataset",
    )

    # Create test data with known token counts
    conn.sql(
        f"""
        CREATE TABLE {dataset_ref.dataset_table_name} (
            created_at BIGINT,
            inference_prompt STRUCT(tokens BIGINT),
            inference_response STRUCT(tokens BIGINT)
        )
        """,
    )

    # Insert test data with 5-minute intervals
    # Total prompt tokens: 100, response tokens: 150
    test_data = [
        # First 5-minute interval
        (
            1704067200000,  # 2024-01-01 00:00:00
            {"tokens": 40},
            {"tokens": 60},
        ),
        # Second 5-minute interval
        (
            1704067500000,  # 2024-01-01 00:05:00
            {"tokens": 30},
            {"tokens": 50},
        ),
        # Third 5-minute interval
        (
            1704067800000,  # 2024-01-01 00:10:00
            {"tokens": 30},
            {"tokens": 40},
        ),
    ]

    # Insert the test data
    for created_at, prompt, response in test_data:
        conn.sql(
            f"""
            INSERT INTO {dataset_ref.dataset_table_name}
            VALUES (
                {created_at},
                ROW({prompt['tokens']}),
                ROW({response['tokens']})
            )
            """,
        )

    return conn, dataset_ref


@pytest.fixture
def get_shield_dataset_conn_no_tokens() -> tuple[DuckDBPyConnection, DatasetReference]:
    """Create a test database with Shield inference data that has NULL token values.

    Returns:
        tuple: (DuckDB connection, DatasetReference)
    """
    conn = duckdb.connect(":memory:")
    dataset_ref = DatasetReference(
        dataset_name="shield_dataset",
        dataset_table_name="shield_test_data",
        dataset_id="test-dataset",
    )

    # Create test data including NULL values
    conn.sql(
        f"""
        CREATE TABLE {dataset_ref.dataset_table_name} (
            created_at BIGINT,
            inference_prompt STRUCT(tokens BIGINT),
            inference_response STRUCT(tokens BIGINT)
        )
        """,
    )

    # Insert test data with NULL token values
    test_data = [
        # Record with no token values present
        (
            1704067200000,  # 2024-01-01 00:00:00
            {"tokens": None},
            {"tokens": None},
        ),
        # Record with NULL prompt tokens
        (
            1704067500000,  # 2024-01-01 00:05:00
            {"tokens": None},
            {"tokens": 50},
        ),
        # Record with NULL response tokens
        (
            1704067800000,  # 2024-01-01 00:10:00
            {"tokens": 30},
            {"tokens": None},
        ),
    ]

    # Insert the test data
    for created_at, prompt, response in test_data:
        prompt_tokens = "NULL" if prompt["tokens"] is None else prompt["tokens"]
        response_tokens = "NULL" if response["tokens"] is None else response["tokens"]

        conn.sql(
            f"""
            INSERT INTO {dataset_ref.dataset_table_name}
            VALUES (
                {created_at},
                ROW({prompt_tokens}),
                ROW({response_tokens})
            )
            """,
        )

    return conn, dataset_ref

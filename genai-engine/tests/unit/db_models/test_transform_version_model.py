import uuid
from datetime import datetime

import pytest

from db_models.transform_models import DatabaseTraceTransformVersion


@pytest.mark.unit_tests
def test_transform_version_instantiation() -> None:
    """Test that DatabaseTraceTransformVersion can be instantiated with required fields."""
    transform_id = uuid.uuid4()
    task_id = str(uuid.uuid4())
    config = {"variables": [{"variable_name": "x", "span_name": "s", "attribute_path": "a"}]}

    version = DatabaseTraceTransformVersion(
        transform_id=transform_id,
        task_id=task_id,
        version_number=1,
        config_snapshot=config,
        author="test-user",
        created_at=datetime(2026, 3, 23, 12, 0, 0),
    )

    assert version.transform_id == transform_id
    assert version.task_id == task_id
    assert version.version_number == 1
    assert version.config_snapshot == config
    assert version.author == "test-user"
    assert version.created_at == datetime(2026, 3, 23, 12, 0, 0)


@pytest.mark.unit_tests
def test_transform_version_author_optional() -> None:
    """Test that author field is optional (nullable)."""
    version = DatabaseTraceTransformVersion(
        transform_id=uuid.uuid4(),
        task_id=str(uuid.uuid4()),
        version_number=1,
        config_snapshot={"variables": []},
        author=None,
    )

    assert version.author is None


@pytest.mark.unit_tests
def test_transform_version_tablename() -> None:
    """Test that the table name is correct."""
    assert DatabaseTraceTransformVersion.__tablename__ == "transform_versions"


@pytest.mark.unit_tests
def test_transform_version_unique_constraint_defined() -> None:
    """Test that the unique constraint on (transform_id, version_number) is present."""
    constraints = DatabaseTraceTransformVersion.__table_args__
    constraint_names = [c.name for c in constraints if hasattr(c, "name")]
    assert "uq_transform_version_number" in constraint_names


@pytest.mark.unit_tests
def test_transform_version_config_snapshot_stores_complex_json() -> None:
    """Test that config_snapshot can hold complex nested JSON."""
    complex_config = {
        "variables": [
            {
                "variable_name": "prompt",
                "span_name": "llm-call",
                "attribute_path": "attributes.input",
                "fallback": None,
            },
            {
                "variable_name": "response",
                "span_name": "llm-call",
                "attribute_path": "attributes.output",
                "fallback": "",
            },
        ],
        "metadata": {"created_by": "system", "tags": ["v2", "production"]},
    }

    version = DatabaseTraceTransformVersion(
        transform_id=uuid.uuid4(),
        task_id=str(uuid.uuid4()),
        version_number=3,
        config_snapshot=complex_config,
    )

    assert version.config_snapshot == complex_config
    assert len(version.config_snapshot["variables"]) == 2
    assert version.config_snapshot["metadata"]["tags"] == ["v2", "production"]

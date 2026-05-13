import uuid
from datetime import datetime

import pytest

from db_models.transform_models import DatabaseTraceTransformVersion


@pytest.mark.unit_tests
def test_transform_version_instantiation() -> None:
    """Test that DatabaseTraceTransformVersion can be instantiated with required fields."""
    transform_id = uuid.uuid4()
    config = {
        "variables": [{"variable_name": "x", "span_name": "s", "attribute_path": "a"}],
    }

    version = DatabaseTraceTransformVersion(
        transform_id=transform_id,
        version_number=1,
        definition=config,
        created_at=datetime(2026, 3, 23, 12, 0, 0),
    )

    assert version.transform_id == transform_id
    assert version.version_number == 1
    assert version.definition == config
    assert version.created_at == datetime(2026, 3, 23, 12, 0, 0)


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
def test_transform_version_definition_stores_complex_json() -> None:
    """Test that definition can hold complex nested JSON."""
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
        version_number=3,
        definition=complex_config,
    )

    assert version.definition == complex_config
    assert len(version.definition["variables"]) == 2
    assert version.definition["metadata"]["tags"] == ["v2", "production"]

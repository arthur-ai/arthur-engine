from datetime import datetime, timezone

import pytest
from arthur_client.api_bindings import DataResultFilter, DataResultFilterOp
from arthur_common.models.enums import ToolClassEnum
from pydantic import ValidationError
from tools.agentic_filters import (
    _map_comparison_operator_to_suffix,
    build_validated_filter_params,
    validate_filters,
)


@pytest.mark.parametrize(
    "op,expected_suffix",
    [
        (DataResultFilterOp.EQUALS, "_eq"),
        (DataResultFilterOp.GREATER_THAN, "_gt"),
        (DataResultFilterOp.GREATER_THAN_OR_EQUAL, "_gte"),
        (DataResultFilterOp.LESS_THAN, "_lt"),
        (DataResultFilterOp.LESS_THAN_OR_EQUAL, "_lte"),
        (DataResultFilterOp.IN, None),  # No suffix, should return None
    ],
)
def test_comparison_operator_mapping(op, expected_suffix):
    """Test that comparison operators map to correct suffixes."""
    assert _map_comparison_operator_to_suffix(op) == expected_suffix


@pytest.mark.parametrize(
    "field_name,op,value,expected_key,expected_value",
    [
        # Relevance filters with comparison operators
        (
            "query_relevance",
            DataResultFilterOp.GREATER_THAN,
            0.5,
            "query_relevance_gt",
            0.5,
        ),
        (
            "query_relevance",
            DataResultFilterOp.LESS_THAN,
            0.8,
            "query_relevance_lt",
            0.8,
        ),
        ("query_relevance", DataResultFilterOp.EQUALS, 0.7, "query_relevance_eq", 0.7),
        (
            "response_relevance",
            DataResultFilterOp.GREATER_THAN_OR_EQUAL,
            0.3,
            "response_relevance_gte",
            0.3,
        ),
        (
            "response_relevance",
            DataResultFilterOp.LESS_THAN_OR_EQUAL,
            0.9,
            "response_relevance_lte",
            0.9,
        ),
        # Duration filters
        (
            "trace_duration",
            DataResultFilterOp.GREATER_THAN,
            1000,
            "trace_duration_gt",
            1000,
        ),
        (
            "trace_duration",
            DataResultFilterOp.LESS_THAN_OR_EQUAL,
            5000,
            "trace_duration_lte",
            5000,
        ),
        # Direct mapping fields
        (
            "tool_name",
            DataResultFilterOp.EQUALS,
            "search_tool",
            "tool_name",
            "search_tool",
        ),
        (
            "span_types",
            DataResultFilterOp.IN,
            ["LLM", "CHAIN"],
            "span_types",
            ["LLM", "CHAIN"],
        ),
        ("span_types", DataResultFilterOp.EQUALS, "LLM", "span_types", ["LLM"]),
        # Trace IDs - single string gets converted to list
        ("trace_ids", DataResultFilterOp.EQUALS, "trace123", "trace_ids", ["trace123"]),
        (
            "trace_ids",
            DataResultFilterOp.IN,
            ["trace1", "trace2"],
            "trace_ids",
            ["trace1", "trace2"],
        ),
        # Tool classification - integer gets converted to enum
        (
            "tool_selection",
            DataResultFilterOp.EQUALS,
            1,
            "tool_selection",
            ToolClassEnum(1),
        ),
        ("tool_usage", DataResultFilterOp.EQUALS, 2, "tool_usage", ToolClassEnum(2)),
    ],
)
def test_filter_parameter_conversion(
    field_name,
    op,
    value,
    expected_key,
    expected_value,
):
    """Test that filters are converted to correct query parameters."""
    filters = [DataResultFilter(field_name=field_name, op=op, value=value)]

    result = build_validated_filter_params(
        task_ids=["task1"],
        filters=filters,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    assert expected_key in result
    assert result[expected_key] == expected_value


@pytest.mark.parametrize(
    "field_name,op,value",
    [
        # Unsupported operators for relevance fields
        ("query_relevance", DataResultFilterOp.IN, [0.5, 0.6]),
        ("response_relevance", DataResultFilterOp.IN, [0.3, 0.8]),
        ("trace_duration", DataResultFilterOp.IN, [1000, 2000]),
        # Unsupported operators for tool fields
        ("tool_name", DataResultFilterOp.GREATER_THAN, "search"),
        ("span_types", DataResultFilterOp.GREATER_THAN, "LLM"),
        ("trace_ids", DataResultFilterOp.GREATER_THAN, "trace1"),
    ],
)
def test_unsupported_operators_ignored(field_name, op, value):
    """Test that unsupported operators are ignored and don't appear in result."""
    filters = [DataResultFilter(field_name=field_name, op=op, value=value)]

    result = build_validated_filter_params(
        task_ids=["task1"],
        filters=filters,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    # Should not contain any filters for fields with unsupported operators
    relevant_keys = [key for key in result.keys() if key.startswith(field_name)]
    assert len(relevant_keys) == 0


@pytest.mark.parametrize(
    "invalid_value,field_name",
    [
        (-0.1, "query_relevance"),  # Below minimum
        (1.5, "query_relevance"),  # Above maximum
        (-0.5, "response_relevance"),  # Below minimum
        (2.0, "response_relevance"),  # Above maximum
    ],
)
def test_invalid_relevance_values_raise_validation_error(invalid_value, field_name):
    """Test that invalid relevance values raise ValidationError."""
    filters = [
        DataResultFilter(
            field_name=field_name,
            op=DataResultFilterOp.GREATER_THAN,
            value=invalid_value,
        ),
    ]

    with pytest.raises(ValidationError) as exc_info:
        build_validated_filter_params(
            task_ids=["task1"],
            filters=filters,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )

    error_str = str(exc_info.value)
    assert field_name in error_str


@pytest.mark.parametrize(
    "filters_data,expected_error_msg",
    [
        # Conflicting operators for same field
        (
            [
                ("query_relevance", DataResultFilterOp.EQUALS, 0.5),
                ("query_relevance", DataResultFilterOp.GREATER_THAN, 0.3),
            ],
            "cannot be combined",
        ),
        (
            [
                ("response_relevance", DataResultFilterOp.GREATER_THAN, 0.3),
                ("response_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.4),
            ],
            "Cannot combine",
        ),
        (
            [
                ("trace_duration", DataResultFilterOp.LESS_THAN, 2000),
                ("trace_duration", DataResultFilterOp.LESS_THAN_OR_EQUAL, 1500),
            ],
            "Cannot combine",
        ),
    ],
)
def test_conflicting_operators_raise_validation_error(filters_data, expected_error_msg):
    """Test that conflicting operators raise ValidationError."""
    filters = [
        DataResultFilter(field_name=field, op=op, value=value)
        for field, op, value in filters_data
    ]

    with pytest.raises(ValidationError) as exc_info:
        build_validated_filter_params(
            task_ids=["task1"],
            filters=filters,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )

    assert expected_error_msg.lower() in str(exc_info.value).lower()


def test_empty_task_ids_raises_validation_error():
    """Test that empty task_ids raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        build_validated_filter_params(
            task_ids=[],  # Empty
            filters=[],
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )

    assert "too_short" in str(exc_info.value)


@pytest.mark.parametrize(
    "is_agentic,filter_field,should_pass_through",
    [
        (True, "query_relevance", True),  # Agentic filters pass through
        (True, "invalid_field", True),  # Even invalid ones for agentic
        (False, "conversation_id", True),  # Valid non-agentic filter
        (False, "invalid_field", False),  # Invalid non-agentic filter filtered out
    ],
)
def test_validate_filters_agentic_vs_non_agentic(
    is_agentic,
    filter_field,
    should_pass_through,
):
    """Test that validate_filters behaves differently for agentic vs non-agentic."""
    filters = [
        DataResultFilter(
            field_name=filter_field,
            op=DataResultFilterOp.EQUALS,
            value="test_value",
        ),
    ]

    result = validate_filters(filters, is_agentic=is_agentic)

    if should_pass_through:
        assert result == filters
    else:
        assert result == []


def test_complex_filter_combination_parameter_conversion():
    """Test parameter conversion with many different filter types."""
    filters = [
        DataResultFilter(
            field_name="query_relevance",
            op=DataResultFilterOp.GREATER_THAN,
            value=0.3,
        ),
        DataResultFilter(
            field_name="response_relevance",
            op=DataResultFilterOp.LESS_THAN,
            value=0.9,
        ),
        DataResultFilter(
            field_name="trace_duration",
            op=DataResultFilterOp.GREATER_THAN_OR_EQUAL,
            value=500,
        ),
        DataResultFilter(
            field_name="tool_name",
            op=DataResultFilterOp.EQUALS,
            value="search",
        ),
        DataResultFilter(
            field_name="span_types",
            op=DataResultFilterOp.IN,
            value=["LLM", "CHAIN"],
        ),
        DataResultFilter(
            field_name="trace_ids",
            op=DataResultFilterOp.EQUALS,
            value="trace123",
        ),
        DataResultFilter(
            field_name="tool_selection",
            op=DataResultFilterOp.EQUALS,
            value=1,
        ),
    ]

    result = build_validated_filter_params(
        task_ids=["task1"],
        filters=filters,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    # Verify all expected parameters are present with correct values
    expected_params = {
        "query_relevance_gt": 0.3,
        "response_relevance_lt": 0.9,
        "trace_duration_gte": 500,
        "tool_name": "search",
        "span_types": ["LLM", "CHAIN"],
        "trace_ids": ["trace123"],  # String converted to list
        "tool_selection": ToolClassEnum(1),  # Integer converted to enum
    }

    for key, expected_value in expected_params.items():
        assert key in result
        assert result[key] == expected_value


@pytest.mark.parametrize(
    "boundary_value,field_name,op",
    [
        (0.0, "query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL),
        (1.0, "query_relevance", DataResultFilterOp.LESS_THAN_OR_EQUAL),
        (0.0, "response_relevance", DataResultFilterOp.EQUALS),
        (1.0, "response_relevance", DataResultFilterOp.EQUALS),
    ],
)
def test_boundary_values_accepted(boundary_value, field_name, op):
    """Test that boundary values (0.0 and 1.0) are accepted for relevance fields."""
    filters = [DataResultFilter(field_name=field_name, op=op, value=boundary_value)]

    # Should not raise ValidationError
    result = build_validated_filter_params(
        task_ids=["task1"],
        filters=filters,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
    )

    # Should contain the filter
    expected_key = f"{field_name}{_map_comparison_operator_to_suffix(op)}"
    assert expected_key in result
    assert result[expected_key] == boundary_value

import pytest
from arthur_common.aggregations.functions.shield_aggregations import (
    ShieldInferenceTokenCountAggregation,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


@pytest.mark.parametrize(
    "model_name,expected_prompt_tokens,expected_response_tokens,expected_prompt_cost,expected_response_cost",
    [
        (
            "gpt-4o",
            100,  # prompt tokens
            150,  # response tokens
            0.00025,  # prompt cost
            0.0015,  # response cost
        ),
        (
            "gpt-3.5-turbo",
            100,
            150,
            0.00015,
            0.0003,
        ),
    ],
)
def test_shield_token_count(
    get_shield_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    model_name: str,
    expected_prompt_tokens: int,
    expected_response_tokens: int,
    expected_prompt_cost: float,
    expected_response_cost: float,
):
    """Test the Shield token count aggregation function.

    Args:
        get_shield_dataset_conn: Fixture providing connection and dataset reference
        model_name: Name of the model to test costs for
        expected_prompt_tokens: Expected number of tokens in prompts
        expected_response_tokens: Expected number of tokens in responses
        expected_prompt_cost: Expected cost for prompt tokens
        expected_response_cost: Expected cost for response tokens
    """
    conn, dataset_ref = get_shield_dataset_conn
    token_count_aggregator = ShieldInferenceTokenCountAggregation()

    metrics = token_count_aggregator.aggregate(
        conn,
        dataset_ref,
        shield_response_column="shield_response",
    )

    # Check for a single token count metric, and two token count series within those metrics
    token_count_metrics = [m for m in metrics if m.name == "token_count"]
    assert len(token_count_metrics) == 1
    assert len(token_count_metrics[0].numeric_series) == 2

    # Find prompt and response series
    token_count_series = {
        series.dimensions[0].value: series.values
        for series in token_count_metrics[0].numeric_series
        if series.dimensions[0].name == "location"
    }

    # Check token counts
    total_prompt_tokens = sum(v.value for v in token_count_series["prompt"])
    total_response_tokens = sum(v.value for v in token_count_series["response"])
    assert total_prompt_tokens == expected_prompt_tokens
    assert total_response_tokens == expected_response_tokens

    # Check that the token cost metric exists
    token_cost_metrics = [m for m in metrics if m.name == f"token_cost.{model_name}"]
    assert len(token_cost_metrics) == 1

    # Find prompt and response cost series
    prompt_cost_series = next(
        s
        for s in token_cost_metrics[0].numeric_series
        if s.dimensions[0].name == "location" and s.dimensions[0].value == "prompt"
    )
    response_cost_series = next(
        s
        for s in token_cost_metrics[0].numeric_series
        if s.dimensions[0].name == "location" and s.dimensions[0].value == "response"
    )

    # Check costs
    total_prompt_cost = sum(v.value for v in prompt_cost_series.values)
    total_response_cost = sum(v.value for v in response_cost_series.values)
    assert round(total_prompt_cost, 5) == expected_prompt_cost
    assert round(total_response_cost, 5) == expected_response_cost


@pytest.mark.parametrize(
    "model_name,expected_prompt_tokens,expected_response_tokens,expected_prompt_cost,expected_response_cost",
    [
        (
            "gpt-4o",
            30,  # prompt tokens
            50,  # response tokens
            0.00007,  # prompt cost
            0.0005,  # response cost
        ),
        (
            "gpt-3.5-turbo",
            30,
            50,
            0.00005,
            0.0001,
        ),
    ],
)
def test_shield_empty_token_count(
    get_shield_dataset_conn_no_tokens: tuple[DuckDBPyConnection, DatasetReference],
    model_name: str,
    expected_prompt_tokens: int,
    expected_response_tokens: int,
    expected_prompt_cost: float,
    expected_response_cost: float,
):
    """Test the Shield token count aggregation function.

    Args:
        get_shield_dataset_conn: Fixture providing connection and dataset reference
        model_name: Name of the model to test costs for
        expected_prompt_tokens: Expected number of tokens in prompts
        expected_response_tokens: Expected number of tokens in responses
        expected_prompt_cost: Expected cost for prompt tokens
        expected_response_cost: Expected cost for response tokens
    """
    conn, dataset_ref = get_shield_dataset_conn_no_tokens
    token_count_aggregator = ShieldInferenceTokenCountAggregation()

    metrics = token_count_aggregator.aggregate(
        conn,
        dataset_ref,
        shield_response_column="shield_response",
    )

    # Check for a single token count metric, and two token count series within those metrics
    token_count_metrics = [m for m in metrics if m.name == "token_count"]
    assert len(token_count_metrics) == 1
    assert len(token_count_metrics[0].numeric_series) == 2

    # Find prompt and response series
    token_count_series = {
        series.dimensions[0].value: series.values
        for series in token_count_metrics[0].numeric_series
        if series.dimensions[0].name == "location"
    }

    # Check token counts
    total_prompt_tokens = sum(v.value for v in token_count_series["prompt"])
    total_response_tokens = sum(v.value for v in token_count_series["response"])
    assert total_prompt_tokens == expected_prompt_tokens
    assert total_response_tokens == expected_response_tokens

    # Check that the token cost metric exists
    token_cost_metrics = [m for m in metrics if m.name == f"token_cost.{model_name}"]
    assert len(token_cost_metrics) == 1

    # Find prompt and response cost series
    prompt_cost_series = next(
        s
        for s in token_cost_metrics[0].numeric_series
        if s.dimensions[0].name == "location" and s.dimensions[0].value == "prompt"
    )
    response_cost_series = next(
        s
        for s in token_cost_metrics[0].numeric_series
        if s.dimensions[0].name == "location" and s.dimensions[0].value == "response"
    )

    # Check costs
    total_prompt_cost = sum(v.value for v in prompt_cost_series.values)
    total_response_cost = sum(v.value for v in response_cost_series.values)
    assert round(total_prompt_cost, 5) == expected_prompt_cost
    assert round(total_response_cost, 5) == expected_response_cost

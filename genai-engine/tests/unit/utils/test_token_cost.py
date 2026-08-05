import logging
from unittest.mock import patch

import pytest
from litellm import cost_per_token

from utils.token_count import (
    TokenCountCost,
    _model_name_candidates,
    compute_cost_from_tokens,
)
from utils.trace import extract_token_cost_from_span

RECOGNIZED_MODEL = "claude-sonnet-4-6"
UNKNOWN_MODEL = "totally-made-up-model-xyz"


def _llm_span(
    model,
    prompt_tokens,
    completion_tokens,
    cache_read=None,
    cache_write=None,
):
    token_count = {"prompt": prompt_tokens, "completion": completion_tokens}
    prompt_details = {}
    if cache_read is not None:
        prompt_details["cache_read"] = cache_read
    if cache_write is not None:
        prompt_details["cache_write"] = cache_write
    if prompt_details:
        token_count["prompt_details"] = prompt_details
    return {"attributes": {"llm": {"model_name": model, "token_count": token_count}}}


@pytest.mark.unit_tests
class TestComputeCostFromTokens:
    def test_recognized_model_matches_litellm(self):
        expected_prompt, expected_completion = cost_per_token(
            model=RECOGNIZED_MODEL,
            prompt_tokens=1000,
            completion_tokens=100,
        )
        cost = compute_cost_from_tokens(
            RECOGNIZED_MODEL,
            input_tokens=1000,
            output_tokens=100,
        )
        assert cost == pytest.approx(
            float(expected_prompt) + float(expected_completion)
        )

    def test_cache_read_priced_below_full_input(self):
        without_cache = compute_cost_from_tokens(
            RECOGNIZED_MODEL,
            input_tokens=1000,
        )
        with_cache = compute_cost_from_tokens(
            RECOGNIZED_MODEL,
            input_tokens=1000,
            cache_read_input_tokens=800,
        )
        assert with_cache < without_cache

    def test_no_tokens_returns_none(self):
        assert compute_cost_from_tokens(RECOGNIZED_MODEL) is None

    def test_unknown_model_returns_none_and_logs(self, caplog):
        with caplog.at_level(logging.WARNING, logger="utils.token_count"):
            cost = compute_cost_from_tokens(
                UNKNOWN_MODEL,
                input_tokens=1000,
                output_tokens=100,
            )
        assert cost is None
        assert any(
            "unrecognized model" in record.message and UNKNOWN_MODEL in record.message
            for record in caplog.records
        )

    def test_prefixed_model_name_is_normalized(self):
        cost = compute_cost_from_tokens(
            "bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            input_tokens=1000,
            output_tokens=100,
        )
        assert cost is not None
        assert cost > 0


@pytest.mark.unit_tests
class TestModelNameCandidates:
    def test_route_and_region_prefixes_stripped(self):
        candidates = _model_name_candidates(
            "bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        assert candidates[0] == "bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0"
        assert "anthropic.claude-3-5-sonnet-20240620-v1:0" in candidates

    def test_bare_name_yields_single_candidate(self):
        assert _model_name_candidates(RECOGNIZED_MODEL) == [RECOGNIZED_MODEL]


@pytest.mark.unit_tests
class TestExtractTokenCostFromSpan:
    def test_recognized_model_prices_as_before(self):
        result = extract_token_cost_from_span(
            _llm_span(RECOGNIZED_MODEL, 1000, 100),
            "LLM",
        )
        expected_prompt, _ = cost_per_token(
            model=RECOGNIZED_MODEL,
            prompt_tokens=1000,
            completion_tokens=0,
        )
        _, expected_completion = cost_per_token(
            model=RECOGNIZED_MODEL,
            prompt_tokens=0,
            completion_tokens=100,
        )
        assert result.prompt_token_cost == pytest.approx(float(expected_prompt))
        assert result.completion_token_cost == pytest.approx(float(expected_completion))
        assert result.total_token_cost == pytest.approx(
            float(expected_prompt) + float(expected_completion),
        )
        assert result.cost_unknown is False

    def test_cache_read_lowers_cost(self):
        without_cache = extract_token_cost_from_span(
            _llm_span(RECOGNIZED_MODEL, 1000, 100),
            "LLM",
        )
        with_cache = extract_token_cost_from_span(
            _llm_span(RECOGNIZED_MODEL, 1000, 100, cache_read=800),
            "LLM",
        )
        assert with_cache.total_token_cost < without_cache.total_token_cost

    def test_cache_tokens_passed_through(self):
        span = _llm_span(RECOGNIZED_MODEL, 1000, 100, cache_read=800, cache_write=50)
        with patch(
            "utils.trace.compute_cost_from_tokens",
            return_value=0.0,
        ) as mock_cost:
            extract_token_cost_from_span(span, "LLM")

        prompt_call = mock_cost.call_args_list[0]
        assert prompt_call.kwargs["input_tokens"] == 1000
        assert prompt_call.kwargs["cache_read_input_tokens"] == 800
        assert prompt_call.kwargs["cache_creation_input_tokens"] == 50

    def test_unknown_model_flags_cost_unknown(self, caplog):
        with caplog.at_level(logging.WARNING, logger="utils.token_count"):
            result = extract_token_cost_from_span(
                _llm_span(UNKNOWN_MODEL, 1000, 100),
                "LLM",
            )
        assert result.prompt_token_cost is None
        assert result.total_token_cost is None
        assert result.cost_unknown is True
        assert any("unrecognized model" in record.message for record in caplog.records)

    def test_default_cost_unknown_is_false(self):
        assert TokenCountCost().cost_unknown is False

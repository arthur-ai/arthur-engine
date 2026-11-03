import pytest
from arthur_common.models.llm_model_providers import ModelProvider

from utils.thinking_capabilities import always_on_thinking_error, thinking_always_on


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name,expected",
    [
        (ModelProvider.ANTHROPIC, "claude-sonnet-5-5", True),
        (ModelProvider.ANTHROPIC, "claude-opus-5-5", True),
        (ModelProvider.ANTHROPIC, "claude-fable-5-1", True),
        (ModelProvider.ANTHROPIC, "anthropic/claude-sonnet-5-5", True),
        # Dated ids missing from the cost map still resolve through litellm's rules.
        (ModelProvider.ANTHROPIC, "claude-sonnet-5-5-20261001", True),
        (ModelProvider.BEDROCK, "us.anthropic.claude-sonnet-5-5", True),
        (ModelProvider.VERTEX_AI, "claude-opus-5-5@default", True),
        (ModelProvider.ANTHROPIC, "claude-haiku-4-5", False),
        (ModelProvider.ANTHROPIC, "claude-sonnet-4-6", False),
        (ModelProvider.OPENAI, "gpt-5-mini", False),
        (ModelProvider.ANTHROPIC, "not-a-model", False),
    ],
)
def test_thinking_always_on(provider, model_name, expected):
    assert thinking_always_on(provider, model_name) is expected


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "reasoning_effort,thinking",
    [("none", None), (None, {"type": "disabled"})],
)
def test_turning_thinking_off_is_an_error_only_where_it_cannot_work(
    reasoning_effort,
    thinking,
):
    error = always_on_thinking_error(
        ModelProvider.ANTHROPIC,
        "claude-sonnet-5-5",
        reasoning_effort,
        thinking,
    )
    assert error is not None and "reasoning_effort 'low'" in error
    assert (
        always_on_thinking_error(
            ModelProvider.ANTHROPIC,
            "claude-haiku-4-5",
            reasoning_effort,
            thinking,
        )
        is None
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "reasoning_effort,thinking",
    [("low", None), (None, {"type": "adaptive"}), (None, None)],
)
def test_settings_that_take_effect_are_allowed(reasoning_effort, thinking):
    assert (
        always_on_thinking_error(
            ModelProvider.ANTHROPIC,
            "claude-sonnet-5-5",
            reasoning_effort,
            thinking,
        )
        is None
    )

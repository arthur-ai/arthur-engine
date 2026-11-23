import pytest
from arthur_common.models.llm_model_providers import ModelProvider

from utils.reasoning_capabilities import (
    UNKNOWN_REASONING_OPTIONS,
    reasoning_settings_error,
    resolve_reasoning_options,
    thinking_always_on,
)

ANTHROPIC = ModelProvider.ANTHROPIC
OPENAI = ModelProvider.OPENAI


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name,expected",
    [
        (ANTHROPIC, "claude-sonnet-5-5", True),
        (ANTHROPIC, "claude-opus-5-5", True),
        (ANTHROPIC, "claude-fable-5-1", True),
        (ANTHROPIC, "anthropic/claude-sonnet-5-5", True),
        # Dated ids missing from the cost map still resolve through litellm's rules.
        (ANTHROPIC, "claude-sonnet-5-5-20261001", True),
        (ModelProvider.BEDROCK, "us.anthropic.claude-sonnet-5-5", True),
        (ModelProvider.VERTEX_AI, "claude-opus-5-5@default", True),
        (ANTHROPIC, "claude-haiku-4-5", False),
        (ANTHROPIC, "claude-sonnet-4-6", False),
        (OPENAI, "gpt-5-mini", False),
        (ANTHROPIC, "not-a-model", False),
    ],
)
def test_thinking_always_on(provider, model_name, expected):
    assert thinking_always_on(provider, model_name) is expected


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name,efforts,thinking_types",
    [
        (OPENAI, "gpt-5-mini", ["minimal", "low", "medium", "high"], []),
        (OPENAI, "gpt-5.1", ["none", "low", "medium", "high"], []),
        (OPENAI, "gpt-4o-mini", [], []),
        # Mapped, but litellm states no levels: any value goes.
        (OPENAI, "o4-mini", None, []),
        (ANTHROPIC, "claude-haiku-4-5", None, ["enabled", "adaptive", "disabled"]),
        (
            ANTHROPIC,
            "claude-sonnet-5-5",
            ["minimal", "low", "medium", "high"],
            ["enabled", "adaptive"],
        ),
        (
            ModelProvider.BEDROCK,
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            None,
            ["enabled", "adaptive", "disabled"],
        ),
        (ModelProvider.BEDROCK, "amazon.nova-pro-v1:0", [], []),
        # Gemini only takes a thinking budget; "disabled" only hides thoughts there.
        (ModelProvider.GEMINI, "gemini-2.5-flash", None, ["enabled"]),
    ],
)
def test_resolve_reasoning_options(provider, model_name, efforts, thinking_types):
    options = resolve_reasoning_options(provider, model_name)
    assert options.reasoning_efforts == efforts
    assert options.thinking_types == thinking_types
    assert options.thinking_supported is bool(thinking_types)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name",
    [
        (ModelProvider.AZURE, "my-prod-deployment"),
        (ModelProvider.VLLM, "llama-3-70b"),
        (OPENAI, "ft:my-fine-tune"),
    ],
)
def test_unknown_models_pass_through(provider, model_name):
    assert resolve_reasoning_options(provider, model_name) == UNKNOWN_REASONING_OPTIONS
    assert (
        reasoning_settings_error(
            provider,
            model_name,
            "none",
            {"type": "disabled"},
        )
        is None
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name,reasoning_effort,thinking,expected",
    [
        # litellm raises UnsupportedParamsError on each of these at run time.
        (OPENAI, "gpt-5-mini", "none", None, "Allowed values: 'minimal', 'low'"),
        (OPENAI, "gpt-5.1", "minimal", None, "Allowed values: 'none', 'low'"),
        (OPENAI, "gpt-4o-mini", "low", None, "does not take reasoning_effort"),
        (OPENAI, "gpt-5-mini", None, {"type": "disabled"}, "does not take thinking"),
        # "default" is never a value litellm states for a model.
        (OPENAI, "gpt-5-mini", "default", None, "is not supported for gpt-5-mini"),
        # Always-thinking Claude: both ways of turning thinking off are dropped.
        (ANTHROPIC, "claude-sonnet-5-5", "none", None, "be turned off"),
        (ANTHROPIC, "claude-sonnet-5-5", None, {"type": "disabled"}, "be turned off"),
        (
            ModelProvider.GEMINI,
            "gemini-2.5-flash",
            None,
            {"type": "disabled"},
            "Allowed types: 'enabled'",
        ),
    ],
)
def test_reasoning_settings_rejected(
    provider,
    model_name,
    reasoning_effort,
    thinking,
    expected,
):
    error = reasoning_settings_error(provider, model_name, reasoning_effort, thinking)
    assert error is not None and expected in error


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name,reasoning_effort,thinking",
    [
        (OPENAI, "gpt-5-mini", "minimal", None),
        (OPENAI, "gpt-5.1", "none", None),
        (OPENAI, "o4-mini", "high", None),
        (ANTHROPIC, "claude-haiku-4-5", None, {"type": "disabled"}),
        (ANTHROPIC, "claude-sonnet-5-5", "low", None),
        (ANTHROPIC, "claude-sonnet-5-5", None, {"type": "adaptive"}),
        (OPENAI, "gpt-4o-mini", None, None),
    ],
)
def test_reasoning_settings_allowed(provider, model_name, reasoning_effort, thinking):
    assert (
        reasoning_settings_error(provider, model_name, reasoning_effort, thinking)
        is None
    )

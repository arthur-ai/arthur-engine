"""Which Claude models always think (UP-5351).

litellm marks the Sonnet 5.5, Opus 5.5, Fable 5 and Mythos 5 families
thinking_always_on and drops thinking={"type": "disabled"} and reasoning_effort
"none" before sending a request to them, so neither turns thinking off there.
"""

from typing import Any, Optional

from arthur_common.models.llm_model_providers import ModelProvider
from litellm.llms.anthropic.common_utils import AnthropicModelInfo


def bare_model_name(provider: ModelProvider, model_name: str) -> str:
    prefix = f"{provider.value}/"
    return model_name[len(prefix) :] if model_name.startswith(prefix) else model_name


def thinking_always_on(provider: ModelProvider, model_name: str) -> bool:
    """Whether litellm treats the model as always thinking.

    Uses litellm's own check, which also covers dated ids missing from the cost
    map; get_model_info's thinking_always_on flag only covers mapped ids.
    """
    try:
        return AnthropicModelInfo._is_always_on_thinking_model(
            bare_model_name(provider, model_name),
            provider.value,
        )
    except Exception:
        # Raised for any model litellm can't resolve, which then isn't flagged.
        return False


def _turns_thinking_off(reasoning_effort: Any, thinking: Any) -> bool:
    effort = getattr(reasoning_effort, "value", reasoning_effort)
    return effort == "none" or (
        isinstance(thinking, dict) and thinking.get("type") == "disabled"
    )


def always_on_thinking_error(
    provider: ModelProvider,
    model_name: str,
    reasoning_effort: Any,
    thinking: Any,
) -> Optional[str]:
    """Why an eval's reasoning settings can't take effect on this model, if they can't."""
    if not _turns_thinking_off(reasoning_effort, thinking):
        return None
    if not thinking_always_on(provider, model_name):
        return None
    return (
        f"Thinking can't be turned off for {model_name}: the model always thinks, so "
        "thinking type 'disabled' and reasoning_effort 'none' are dropped before the "
        "request is sent. Use reasoning_effort 'low' to keep thinking to a minimum."
    )

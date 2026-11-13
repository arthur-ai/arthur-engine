"""Which reasoning settings litellm accepts for a model (UP-5351).

One source of truth for the eval save check, the provider eval defaults and the
eval editor's options. Everything comes from litellm:

- get_supported_openai_params: whether the model takes reasoning_effort and
  thinking at all. gpt-4o-mini takes neither, and litellm raises on both.
- resolve_supported_reasoning_efforts: which reasoning_effort values it takes.
  gpt-5-mini refuses "none" and gpt-5.1 refuses "minimal", and litellm raises
  UnsupportedParamsError on each.
- the always-on-thinking check: litellm flags the Claude Sonnet 5.5, Opus 5.5,
  Fable 5 and Mythos 5 families thinking_always_on, and drops thinking
  {"type": "disabled"} and reasoning_effort "none" before sending to them, so
  neither turns thinking off there.

thinking {"type": "disabled"} is only offered where it turns thinking off, which
is Claude: on Gemini litellm maps it to whether thoughts are returned, not to
whether the model thinks.

A model missing from litellm's cost map (an Azure deployment name, a vLLM
model) is unknown: nothing is said about it, an eval's own setting is sent as
configured, and the provider eval defaults are not applied.
"""

from dataclasses import dataclass
from typing import Any, Final, Optional

import litellm
from arthur_common.models.llm_model_providers import ModelProvider, ReasoningEffortEnum
from litellm.llms.anthropic.common_utils import AnthropicModelInfo
from litellm.router_utils.reasoning_effort_capability import (
    resolve_supported_reasoning_efforts,
)

REASONING_EFFORT_PARAM: Final = "reasoning_effort"
THINKING_PARAM: Final = "thinking"
THINKING_TYPES: Final = ("enabled", "adaptive", "disabled")

_EFFORT_VALUES: Final = {effort.value for effort in ReasoningEffortEnum}


@dataclass(frozen=True)
class ReasoningOptions:
    """None in a field means litellm can't say, and any value is sent as is."""

    reasoning_efforts: Optional[list[str]]
    thinking_supported: Optional[bool]
    thinking_types: Optional[list[str]]
    thinking_always_on: bool


UNKNOWN_REASONING_OPTIONS: Final = ReasoningOptions(
    reasoning_efforts=None,
    thinking_supported=None,
    thinking_types=None,
    thinking_always_on=False,
)


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


def _is_claude(provider: ModelProvider, model_name: str, model_info: Any) -> bool:
    return (
        provider == ModelProvider.ANTHROPIC
        or "anthropic" in str(model_info.get("litellm_provider") or "")
        or "claude" in model_name.lower()
    )


def resolve_reasoning_options(
    provider: ModelProvider,
    model_name: str,
) -> ReasoningOptions:
    provider = ModelProvider(provider)
    model = bare_model_name(provider, model_name)
    try:
        model_info = litellm.get_model_info(
            model=model,
            custom_llm_provider=provider.value,
        )
        supported = litellm.get_supported_openai_params(
            model=model,
            custom_llm_provider=provider.value,
        )
    except Exception:
        # Raised for any model missing from litellm's cost map.
        return UNKNOWN_REASONING_OPTIONS
    if supported is None:
        return UNKNOWN_REASONING_OPTIONS
    params = set(supported)

    always_on = thinking_always_on(provider, model)

    efforts: Optional[list[str]] = []
    if REASONING_EFFORT_PARAM in params:
        levels = resolve_supported_reasoning_efforts(
            model_info,
            deployment_is_mapped=True,
        )
        efforts = (
            None
            if levels is None
            else [
                level
                for level in levels
                # "none" is dropped before sending on always-thinking models.
                if level in _EFFORT_VALUES and not (always_on and level == "none")
            ]
        )

    thinking_supported = THINKING_PARAM in params
    if not thinking_supported:
        thinking_types: list[str] = []
    elif _is_claude(provider, model, model_info):
        thinking_types = [
            thinking_type
            for thinking_type in THINKING_TYPES
            if not (always_on and thinking_type == "disabled")
        ]
    else:
        # Elsewhere litellm maps only an enabled budget to a real thinking setting.
        thinking_types = ["enabled"]

    return ReasoningOptions(
        reasoning_efforts=efforts,
        thinking_supported=thinking_supported,
        thinking_types=thinking_types,
        thinking_always_on=always_on,
    )


def _effort_value(reasoning_effort: Any) -> Optional[str]:
    value = getattr(reasoning_effort, "value", reasoning_effort)
    return value if isinstance(value, str) else None


def _thinking_type(thinking: Any) -> Optional[str]:
    if not isinstance(thinking, dict):
        return None
    thinking_type = thinking.get("type")
    return thinking_type if isinstance(thinking_type, str) else None


def effort_allowed(options: ReasoningOptions, reasoning_effort: Any) -> bool:
    effort = _effort_value(reasoning_effort)
    return (
        effort is None
        or options.reasoning_efforts is None
        or effort in options.reasoning_efforts
    )


def thinking_allowed(options: ReasoningOptions, thinking: Any) -> bool:
    if thinking is None or options.thinking_supported is None:
        return True
    if not options.thinking_supported:
        return False
    thinking_type = _thinking_type(thinking)
    return (
        thinking_type is None
        or options.thinking_types is None
        or thinking_type in options.thinking_types
    )


def _listed(values: list[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def reasoning_settings_error(
    provider: ModelProvider,
    model_name: str,
    reasoning_effort: Any,
    thinking: Any,
) -> Optional[str]:
    """Why an eval's reasoning settings won't work on this model, if they won't."""
    if _effort_value(reasoning_effort) is None and thinking is None:
        return None
    options = resolve_reasoning_options(provider, model_name)
    effort = _effort_value(reasoning_effort)
    thinking_type = _thinking_type(thinking)

    if options.thinking_always_on and (effort == "none" or thinking_type == "disabled"):
        return (
            f"Thinking can't be turned off for {model_name}: the model always thinks, "
            "so thinking type 'disabled' and reasoning_effort 'none' are dropped before "
            "the request is sent. Use reasoning_effort 'low' to keep thinking to a "
            "minimum."
        )
    if not effort_allowed(options, reasoning_effort):
        allowed = options.reasoning_efforts or []
        return f"reasoning_effort '{effort}' is not supported for {model_name}. " + (
            f"Allowed values: {_listed(allowed)}."
            if allowed
            else "The model does not take reasoning_effort."
        )
    if not thinking_allowed(options, thinking):
        allowed = options.thinking_types or []
        return (
            f"thinking type '{thinking_type}' is not supported for {model_name}. "
            if thinking_type and allowed
            else f"thinking is not supported for {model_name}. "
        ) + (
            f"Allowed types: {_listed(allowed)}."
            if allowed
            else "The model does not take thinking."
        )
    return None

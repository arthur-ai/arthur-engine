"""Provider-level reasoning defaults for LLM eval calls (UP-5351).

Thinking tokens are most of an LLM judge's output, so a provider's admin can set
a default reasoning_effort and thinking that every eval on that provider gets
unless the eval sets its own. The eval's settings win as a pair: an eval that
sets either one gets neither default, so a default never mixes with an eval's
own choice into a combination nobody picked.

A provider hosts models that take different settings (gpt-4o-mini takes no
reasoning_effort, gpt-5-mini refuses "none", gpt-5.1 refuses "minimal"), and
litellm raises on a setting the model doesn't take. A default is a provider-wide
choice, so it is applied only to models litellm says accept it, and an eval on
any other model runs as if no default were set. When litellm doesn't know the
model it can't say, and the default is sent as configured.
"""

import logging
from typing import Any, Optional

import litellm
from arthur_common.models.llm_model_providers import ModelProvider
from litellm.router_utils.reasoning_effort_capability import (
    resolve_supported_reasoning_efforts,
)

from schemas.response_schemas import ModelProviderEvalDefaults

logger = logging.getLogger(__name__)

REASONING_EFFORT_PARAM = "reasoning_effort"
THINKING_PARAM = "thinking"


def _bare_model_name(provider: ModelProvider, model_name: str) -> str:
    prefix = f"{provider.value}/"
    return model_name[len(prefix) :] if model_name.startswith(prefix) else model_name


def _supported_params(provider: ModelProvider, model_name: str) -> Optional[set[str]]:
    """The params litellm maps for the model, or None when it can't say."""
    try:
        params = litellm.get_supported_openai_params(
            model=model_name,
            custom_llm_provider=provider.value,
        )
    except Exception:
        # litellm raises a range of errors for models it doesn't know.
        return None
    return set(params) if params is not None else None


def _supported_reasoning_efforts(
    provider: ModelProvider,
    model_name: str,
) -> Optional[tuple[str, ...]]:
    """The reasoning_effort values the model accepts, or None when litellm can't say."""
    try:
        model_info = litellm.get_model_info(
            model=model_name,
            custom_llm_provider=provider.value,
        )
    except Exception:
        # Raised for any model missing from litellm's cost map.
        return None
    return resolve_supported_reasoning_efforts(model_info, deployment_is_mapped=True)


def apply_provider_eval_defaults(
    config: dict[str, Any],
    defaults: ModelProviderEvalDefaults,
    model_name: str,
) -> None:
    """Fill reasoning_effort and thinking from the provider's defaults, in place.

    `config` is the eval's LLM config with unset fields left out.
    """
    if defaults.reasoning_effort is None and defaults.thinking is None:
        return
    if (
        config.get(REASONING_EFFORT_PARAM) is not None
        or config.get(THINKING_PARAM) is not None
    ):
        return

    provider = defaults.provider
    model = _bare_model_name(provider, model_name)
    supported = _supported_params(provider, model)

    if defaults.reasoning_effort is not None and (
        supported is None or REASONING_EFFORT_PARAM in supported
    ):
        levels = _supported_reasoning_efforts(provider, model)
        if levels is None or defaults.reasoning_effort.value in levels:
            config[REASONING_EFFORT_PARAM] = defaults.reasoning_effort
        else:
            logger.debug(
                "Skipping provider default reasoning_effort=%s for %s/%s, which accepts %s",
                defaults.reasoning_effort.value,
                provider.value,
                model,
                levels,
            )

    if defaults.thinking is not None and (
        supported is None or THINKING_PARAM in supported
    ):
        config[THINKING_PARAM] = dict(defaults.thinking)

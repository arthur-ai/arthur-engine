"""Provider-level reasoning defaults for LLM eval calls (UP-5351).

Thinking tokens are most of an LLM judge's output, so a provider's admin can set
a default reasoning_effort and thinking that every eval on that provider gets
unless the eval sets its own. The eval's settings win as a pair: an eval that
sets either one gets neither default, so a default never mixes with an eval's
own choice into a combination nobody picked.

A provider hosts models that take different settings (gpt-4o-mini takes no
reasoning_effort, gpt-5-mini refuses "none", gpt-5.1 refuses "minimal", Claude
Sonnet 5.5 can't turn thinking off). A default is a provider-wide choice, so it
is applied only to models that accept it, by the same rule the eval save check
uses (utils.reasoning_capabilities), and an eval on any other model runs as if
no default were set. When litellm doesn't know the model it can't say, and the
default is sent as configured.
"""

import logging
from typing import Any

from schemas.response_schemas import ModelProviderEvalDefaults
from utils.reasoning_capabilities import (
    REASONING_EFFORT_PARAM,
    THINKING_PARAM,
    effort_allowed,
    resolve_reasoning_options,
    thinking_allowed,
)

logger = logging.getLogger(__name__)


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

    options = resolve_reasoning_options(defaults.provider, model_name)

    if defaults.reasoning_effort is not None:
        if effort_allowed(options, defaults.reasoning_effort):
            config[REASONING_EFFORT_PARAM] = defaults.reasoning_effort
        else:
            logger.debug(
                "Skipping provider default reasoning_effort=%s for %s/%s, which accepts %s",
                defaults.reasoning_effort.value,
                defaults.provider.value,
                model_name,
                options.reasoning_efforts,
            )

    if defaults.thinking is not None:
        thinking = dict(defaults.thinking)
        if thinking_allowed(options, thinking):
            config[THINKING_PARAM] = thinking
        else:
            logger.debug(
                "Skipping provider default thinking=%s for %s/%s, which accepts %s",
                thinking,
                defaults.provider.value,
                model_name,
                options.thinking_types,
            )

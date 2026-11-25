import hashlib
import re
from typing import Any

from arthur_common.models.llm_model_providers import ModelProvider
from litellm import get_supported_openai_params
from litellm.integrations.anthropic_cache_control_hook import (
    supports_openai_prompt_cache_breakpoint,
)
from litellm.utils import supports_prompt_caching

# Start of the first Jinja expression, statement or comment
_JINJA_TAG_START = re.compile(r"\{[{%#]")

_EPHEMERAL_CACHE_CONTROL = {"type": "ephemeral"}
_OPENAI_EXPLICIT_CACHE_MODE = {"mode": "explicit"}


def static_template_prefix(template: str) -> str:
    """Return the literal text before the template's first Jinja tag.

    Trailing whitespace is dropped because a `{{-` tag, or Jinja's trailing-newline
    handling, can remove it from the rendered text.
    """
    match = _JINJA_TAG_START.search(template)
    prefix = template if match is None else template[: match.start()]
    return prefix.rstrip()


def eval_prompt_cache_key(task_id: str, eval_name: str, version: int) -> str:
    digest = hashlib.sha256(f"{task_id}:{eval_name}:{version}".encode()).hexdigest()
    return f"arthur-eval-{digest[:32]}"


def _uses_anthropic_cache_control(provider: ModelProvider, model_name: str) -> bool:
    if provider == ModelProvider.ANTHROPIC:
        return True
    # Bedrock and Vertex AI serve Claude alongside other model families, and only
    # some Claude versions there accept cache breakpoints
    if provider in (ModelProvider.BEDROCK, ModelProvider.VERTEX_AI):
        return "claude" in model_name.lower() and supports_prompt_caching(
            model=model_name,
            custom_llm_provider=provider,
        )
    return False


def _mark_static_instructions_cacheable(
    messages: list[dict[str, Any]],
    instructions: str,
    marker: dict[str, Any],
) -> None:
    """Split the rendered instructions message into a static block carrying a cache
    breakpoint and a block with the per-call remainder. The concatenated text is
    unchanged, and the breakpoint never covers rendered variable content."""
    static_prefix = static_template_prefix(instructions)
    if not static_prefix or not messages:
        return

    message = messages[-1]
    content = message.get("content")
    if (
        message.get("role") != "user"
        or not isinstance(content, str)
        or not content.startswith(static_prefix)
    ):
        return

    remainder = content[len(static_prefix) :]
    # providers reject whitespace-only text blocks
    if not remainder.strip():
        return

    message["content"] = [
        {"type": "text", "text": static_prefix, **marker},
        {"type": "text", "text": remainder},
    ]


def apply_eval_prompt_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    instructions: str,
    cache_key: str,
    add_cache_breakpoint: bool = True,
) -> None:
    """Make an LLM-judge eval request cacheable for the provider, in place.

    Claude models, and OpenAI (not Azure) models that take explicit breakpoints
    (GPT-5.6 and later), get a cache breakpoint after the static part of the instructions. A cache
    write costs more than uncached input on both, so callers pass
    `add_cache_breakpoint=False` for evals that run too rarely to read it back.
    OpenAI and Azure OpenAI get a stable `prompt_cache_key` so calls for the same
    eval route to the same cache. Older OpenAI models cache identical prefixes
    automatically with no write fee and also get 24-hour retention where supported.
    """
    messages = completion_params.get("messages", [])
    if _uses_anthropic_cache_control(provider, model_name):
        if add_cache_breakpoint:
            _mark_static_instructions_cacheable(
                messages,
                instructions,
                {"cache_control": dict(_EPHEMERAL_CACHE_CONTROL)},
            )
        return

    if provider not in (ModelProvider.OPENAI, ModelProvider.AZURE):
        return
    supported = (
        get_supported_openai_params(
            model=model_name,
            custom_llm_provider=provider,
        )
        or []
    )
    if "prompt_cache_key" in supported:
        completion_params["prompt_cache_key"] = cache_key

    # Explicit cache mode and retention are only sent to OpenAI itself: litellm only
    # applies its breakpoint dialect there, and Azure acceptance is unverified
    if provider != ModelProvider.OPENAI:
        return
    if supports_openai_prompt_cache_breakpoint(model_name):
        # These models otherwise cache implicitly at the last message, which would
        # pay the write premium on the per-trace text of every call
        completion_params["prompt_cache_options"] = dict(_OPENAI_EXPLICIT_CACHE_MODE)
        if add_cache_breakpoint:
            _mark_static_instructions_cacheable(
                messages,
                instructions,
                {"prompt_cache_breakpoint": dict(_OPENAI_EXPLICIT_CACHE_MODE)},
            )
    elif "prompt_cache_retention" in supported:
        # litellm drops a top-level prompt_cache_retention before the request is sent
        completion_params.setdefault("extra_body", {})["prompt_cache_retention"] = "24h"

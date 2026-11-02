import hashlib
import re
from typing import Any

from arthur_common.models.llm_model_providers import ModelProvider
from litellm import get_supported_openai_params
from litellm.utils import supports_prompt_caching

# Start of the first Jinja expression, statement or comment
_JINJA_TAG_START = re.compile(r"\{[{%#]")

_EPHEMERAL_CACHE_CONTROL = {"type": "ephemeral"}


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


def _accepts_prompt_cache_key(provider: ModelProvider, model_name: str) -> bool:
    if provider not in (ModelProvider.OPENAI, ModelProvider.AZURE):
        return False
    supported = get_supported_openai_params(
        model=model_name,
        custom_llm_provider=provider,
    )
    return "prompt_cache_key" in (supported or [])


def _mark_static_instructions_cacheable(
    messages: list[dict[str, Any]],
    instructions: str,
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
        {
            "type": "text",
            "text": static_prefix,
            "cache_control": dict(_EPHEMERAL_CACHE_CONTROL),
        },
        {"type": "text", "text": remainder},
    ]


def apply_eval_prompt_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    instructions: str,
    cache_key: str,
) -> None:
    """Make an LLM-judge eval request cacheable for the provider, in place.

    Claude models get an explicit cache breakpoint after the static part of the
    instructions. OpenAI caches identical prefixes automatically and gets a stable
    `prompt_cache_key` so calls for the same eval route to the same cache.
    """
    if _uses_anthropic_cache_control(provider, model_name):
        _mark_static_instructions_cacheable(
            completion_params.get("messages", []),
            instructions,
        )
    elif _accepts_prompt_cache_key(provider, model_name):
        completion_params["prompt_cache_key"] = cache_key

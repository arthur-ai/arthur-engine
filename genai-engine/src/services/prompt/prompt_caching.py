import hashlib
import re
from typing import Any, Callable, Sequence

from arthur_common.models.llm_model_providers import ModelProvider
from litellm import get_supported_openai_params
from litellm.integrations.anthropic_cache_control_hook import (
    supports_openai_prompt_cache_breakpoint,
)
from litellm.utils import supports_prompt_caching

# Start of the first Jinja expression, statement or comment
_JINJA_TAG_START = re.compile(r"\{[{%#]")
# A whole Jinja expression, statement or comment
_JINJA_TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)

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


def static_template_suffix(template: str) -> str | None:
    """Return the literal text after the template's last Jinja tag, or None when the
    template has no tags.

    Surrounding whitespace is dropped because `-}}` tags, and Jinja's trailing-newline
    handling, can remove it from the rendered text.
    """
    last_tag = None
    for last_tag in _JINJA_TAG.finditer(template):
        pass
    if last_tag is None:
        return None
    return template[last_tag.end() :].strip()


def eval_prompt_cache_key(task_id: str, eval_name: str, version: int) -> str:
    digest = hashlib.sha256(f"{task_id}:{eval_name}:{version}".encode()).hexdigest()
    return f"arthur-eval-{digest[:32]}"


def system_prompt_cache_key(family: str) -> str:
    digest = hashlib.sha256(family.encode()).hexdigest()
    return f"arthur-system-{digest[:32]}"


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


def _mark_message_cacheable(message: dict[str, Any], marker: dict[str, Any]) -> bool:
    """Put a cache breakpoint on the message's last text block."""
    content = message.get("content")
    if isinstance(content, str):
        # providers reject whitespace-only text blocks
        if not content.strip():
            return False
        message["content"] = [{"type": "text", "text": content, **marker}]
        return True
    if isinstance(content, list):
        for block in reversed(content):
            if isinstance(block, dict) and block.get("type") == "text":
                if not str(block.get("text") or "").strip():
                    return False
                block.update(marker)
                return True
    return False


def _mark_shared_prefix_cacheable(
    messages: list[dict[str, Any]],
    templates: Sequence[str | None],
    marker: dict[str, Any],
) -> None:
    """Put one breakpoint at the end of what prompts built on the same variables
    share: everything up to and including the last rendered variable. The literal
    text after it, which differs between sibling prompts, is split into a block after
    the breakpoint. A prompt with no variables gets the breakpoint on its last system
    message."""
    last_variable = max(
        (
            i
            for i, template in enumerate(templates[: len(messages)])
            if template and static_template_suffix(template) is not None
        ),
        default=None,
    )
    if last_variable is None:
        system = [i for i, m in enumerate(messages) if m.get("role") == "system"]
        if system:
            _mark_message_cacheable(messages[system[-1]], marker)
        return

    message = messages[last_variable]
    content = message.get("content")
    suffix = static_template_suffix(templates[last_variable] or "")
    if not suffix:
        _mark_message_cacheable(message, marker)
        return
    if not isinstance(content, str) or not content.rstrip().endswith(suffix):
        return
    split_at = len(content.rstrip()) - len(suffix)
    head, tail = content[:split_at], content[split_at:]
    # providers reject whitespace-only text blocks
    if not head.strip():
        return
    message["content"] = [
        {"type": "text", "text": head, **marker},
        {"type": "text", "text": tail},
    ]


def _mark_conversation_cacheable(
    messages: list[dict[str, Any]],
    marker: dict[str, Any],
) -> None:
    """Breakpoints on the last system message and on the last message, so the next
    request in a tool loop reads everything this one sent."""
    system = [i for i, m in enumerate(messages) if m.get("role") == "system"]
    if system:
        _mark_message_cacheable(messages[system[-1]], marker)
    if messages and (not system or system[-1] != len(messages) - 1):
        _mark_message_cacheable(messages[-1], dict(marker))


def _apply_provider_prompt_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    cache_key: str,
    place_breakpoints: Callable[[dict[str, Any]], None] | None,
) -> None:
    """Make a request cacheable for the provider, in place.

    Claude models, and OpenAI (not Azure) models that take explicit breakpoints
    (GPT-5.6 and later), get the breakpoints `place_breakpoints` puts on the messages,
    in the provider's marker. A cache write costs more than uncached input on both, so
    callers pass `None` for requests that run too rarely to read it back.
    OpenAI and Azure OpenAI get a stable `prompt_cache_key` so requests sharing a
    prefix route to the same cache. Older OpenAI models cache identical prefixes
    automatically with no write fee and also get 24-hour retention where supported.
    """
    if _uses_anthropic_cache_control(provider, model_name):
        if place_breakpoints is not None:
            place_breakpoints({"cache_control": dict(_EPHEMERAL_CACHE_CONTROL)})
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
        # pay the write premium on per-call text that is never read back
        completion_params["prompt_cache_options"] = dict(_OPENAI_EXPLICIT_CACHE_MODE)
        if place_breakpoints is not None:
            place_breakpoints(
                {"prompt_cache_breakpoint": dict(_OPENAI_EXPLICIT_CACHE_MODE)},
            )
    elif "prompt_cache_retention" in supported:
        # litellm drops a top-level prompt_cache_retention before the request is sent
        completion_params.setdefault("extra_body", {})["prompt_cache_retention"] = "24h"


def apply_eval_prompt_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    instructions: str,
    cache_key: str,
    add_cache_breakpoint: bool = True,
) -> None:
    """Make an LLM-judge eval request cacheable for the provider, in place, with the
    breakpoint after the static part of the instructions. Callers pass
    `add_cache_breakpoint=False` for evals that run too rarely to read it back."""
    messages = completion_params.get("messages", [])
    _apply_provider_prompt_caching(
        completion_params,
        provider=provider,
        model_name=model_name,
        cache_key=cache_key,
        place_breakpoints=(
            (
                lambda marker: _mark_static_instructions_cacheable(
                    messages,
                    instructions,
                    marker,
                )
            )
            if add_cache_breakpoint
            else None
        ),
    )


def apply_shared_prefix_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    templates: Sequence[str | None],
    cache_key: str,
) -> None:
    """Make a saved-prompt request cacheable for the provider, in place, for prompts
    that run back to back on the same variables and differ only after them.

    `templates` holds each message's content before variables were rendered. The
    breakpoint goes after the last rendered variable, so the system message and the
    rendered variables are written once and read by the sibling prompts.
    """
    messages = completion_params.get("messages", [])
    _apply_provider_prompt_caching(
        completion_params,
        provider=provider,
        model_name=model_name,
        cache_key=cache_key,
        place_breakpoints=lambda marker: _mark_shared_prefix_cacheable(
            messages,
            templates,
            marker,
        ),
    )


def apply_conversation_caching(
    completion_params: dict[str, Any],
    *,
    provider: ModelProvider,
    model_name: str,
    cache_key: str,
) -> None:
    """Make one request of a multi-turn tool loop cacheable for the provider, in
    place. Each request's breakpoint on its last message is read back by the next,
    which re-sends the same messages with more appended."""
    messages = completion_params.get("messages", [])
    _apply_provider_prompt_caching(
        completion_params,
        provider=provider,
        model_name=model_name,
        cache_key=cache_key,
        place_breakpoints=lambda marker: _mark_conversation_cacheable(
            messages,
            marker,
        ),
    )

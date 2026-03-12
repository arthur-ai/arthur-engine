from typing import Annotated
from urllib.parse import unquote

from fastapi import Path


def decode_path_param(value: str) -> str:
    """Decode a double-encoded path parameter.

    Frontend clients double-encode user-provided names before placing them in
    URL path segments.  Uvicorn's ASGI layer decodes the request path once
    before FastAPI routes the request, which strips the outer encoding layer.
    This function removes the remaining inner layer so the handler receives
    the original value.

    Safe to call on values that are NOT double-encoded -- unquote is a no-op
    when the string contains no percent-encoded sequences.
    """
    return unquote(value)


def decoded_eval_name(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval (URL-encoded).",
        title="LLM Eval Name",
    ),
) -> str:
    return decode_path_param(eval_name)


def decoded_prompt_name(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt (URL-encoded).",
        title="Prompt Name",
    ),
) -> str:
    return decode_path_param(prompt_name)


def decoded_tag(
    tag: str = Path(
        ...,
        description="The tag name (URL-encoded).",
        title="Tag",
    ),
) -> str:
    return decode_path_param(tag)

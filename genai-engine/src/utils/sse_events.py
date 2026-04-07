"""
Helpers for building Server-Sent Event (SSE) strings.

Event types are defined in ``schemas.enums.SSEEventType``.
"""

import json
from typing import Any

from schemas.enums import SSEEventType


def format_sse(event: SSEEventType, data: str) -> str:
    """Build a properly formatted SSE string: ``event: <type>\\ndata: <payload>\\n\\n``."""
    return (
        f"event: {event.value}\ndata: {data.replace(chr(10), chr(10) + 'data: ')}\n\n"
    )


def format_sse_json(event: SSEEventType, data: Any) -> str:
    """Build an SSE string with a JSON-serialised data payload."""
    return format_sse(event, json.dumps(data))


def format_sse_error(message: str, *, wrap: bool = True) -> str:
    """Build an SSE error event.

    When *wrap* is True (default) the message is JSON-encoded as
    ``{"error": "<message>"}``.  Set *wrap* to False to emit the raw
    string as the data payload (used by ``chat_completion_service``).
    """
    if wrap:
        return format_sse_json(SSEEventType.ERROR, {"error": message})
    return format_sse(SSEEventType.ERROR, message)

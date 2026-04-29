"""Request-body size limit — raw ASGI middleware.

Enforces a hard ceiling (config.MAX_REQUEST_BODY_BYTES, 1 MB by default) so
oversized payloads can't OOM the container. Two paths:

- Fast path: trust the Content-Length header and reject before reading.
- Slow path (chunked / no header): accumulate http.request events; if total
  crosses the ceiling, short-circuit with HTTP 413; otherwise replay the
  exact same events to the inner app so downstream Pydantic validators see
  an unmodified body.

Implemented as raw ASGI rather than starlette.BaseHTTPMiddleware because
BaseHTTPMiddleware's stream proxy doesn't replay bodies cleanly to
downstream consumers.
"""

import json
from typing import Awaitable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

import config as svc_config


def _too_large_response(send: Send) -> Awaitable[None]:
    body = json.dumps(
        {
            "error": {
                "code": "payload_too_large",
                "message": f"Request body exceeds {svc_config.MAX_REQUEST_BODY_BYTES} bytes",
                "details": None,
            },
        },
    ).encode("utf-8")

    async def _send_response() -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            },
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    return _send_response()


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: Content-Length header set.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > svc_config.MAX_REQUEST_BODY_BYTES:
                        await _too_large_response(send)
                        return
                except ValueError:
                    pass
                break

        # Slow path: read all events into a buffer, enforce limit, replay.
        events: list[Message] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                events.append(message)
                break
            if message["type"] == "http.request":
                body = message.get("body", b"") or b""
                total += len(body)
                if total > svc_config.MAX_REQUEST_BODY_BYTES:
                    await _too_large_response(send)
                    return
                events.append(message)
                if not message.get("more_body", False):
                    break
            else:
                events.append(message)

        async def replay() -> Message:
            if events:
                return events.pop(0)
            # Should never be hit — downstream handler shouldn't request more
            # than we replayed — but be safe.
            return {"type": "http.disconnect"}

        await self.app(scope, replay, send)

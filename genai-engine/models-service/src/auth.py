"""Bearer-token authentication middleware.

Every endpoint except `/v1/health` requires
`Authorization: Bearer $MODEL_REGISTRY_SECRET`. The token comparison uses
hmac.compare_digest to avoid timing-leak side channels. /v1/health is
exempted so docker healthchecks and stack `wait_for_port` helpers don't
need the secret.
"""

import hmac
from typing import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

import config as svc_config

EXEMPT_PATHS = {"/v1/health"}


def _unauthorized(
    message: str = "Missing or invalid Authorization header",
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "unauthorized",
                "message": message,
                "details": None,
            },
        },
    )


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        secret = svc_config.MODEL_REGISTRY_SECRET
        if not secret:
            return _unauthorized("Service misconfigured: MODEL_REGISTRY_SECRET unset")

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _unauthorized()
        token = header[len("Bearer ") :].strip()
        if not hmac.compare_digest(token, secret):
            return _unauthorized()

        return await call_next(request)

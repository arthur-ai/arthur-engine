"""FastAPI app for the models service.

Wires up:
- Operational endpoints: /v1/health (liveness), /v1/ready (model warmup
  status), /v1/models (loaded model metadata).
- Inference endpoints: /v1/inference/{prompt_injection, toxicity, pii,
  claim_filter}. Each delegates to its inference module.
- BearerAuthMiddleware (auth.py) gates everything except /v1/health.
- BodySizeLimitMiddleware (middleware.py) enforces a 1 MB body ceiling.
- FastAPIInstrumentor extracts W3C traceparent so the existing
  tracer.start_as_current_span(...) calls in the scorer code nest under the
  caller's parent span.
- Lifespan kicks off model warmup in a background thread so /v1/health is
  reachable immediately while weights are still loading.
"""

import logging
import threading
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

import config as svc_config
from auth import BearerAuthMiddleware
from inference import claim_filter as claim_filter_mod
from inference import pii as pii_mod
from inference import prompt_injection as prompt_injection_mod
from inference import toxicity as toxicity_mod
from inference.device import get_device  # noqa: F401 — kept for /v1/models
from middleware import BodySizeLimitMiddleware
from model_registry import downloader, loader
from model_registry.registry import ALL_MODELS
from schemas import (
    ClaimFilterRequest,
    ClaimFilterResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    PIIRequest,
    PIIResponse,
    PromptInjectionRequest,
    PromptInjectionResponse,
    ReadyResponse,
    ToxicityRequest,
    ToxicityResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """On startup: pull weights into MODEL_STORAGE_PATH (no-op if a host
    volume already has them), then warm all models on a background thread
    so /v1/health stays reachable while loading proceeds. /v1/ready surfaces
    the per-model status.
    """
    if svc_config.SKIP_MODEL_LOADING:
        logger.info("Skipping download + warmup — MODELS_SERVICE_SKIP_LOADING=true")
    else:

        def _warmup() -> None:
            try:
                downloader.download_all(workers=4)
            except Exception:
                logger.exception(
                    "Weight download failed; warmup will continue and fail per-model"
                )
            loader.warm_all()

        logger.info("Spawning background download+warmup thread")
        threading.Thread(target=_warmup, daemon=True).start()
    yield


app = FastAPI(
    title="Arthur Models Service",
    description="Sideloaded torch/transformers inference for genai-engine scorer checks",
    version="0.1.0",
    lifespan=lifespan,
)

# Order matters: body-size check FIRST (so we don't even auth oversized requests),
# then auth.
app.add_middleware(BearerAuthMiddleware)
app.add_middleware(BodySizeLimitMiddleware)

FastAPIInstrumentor.instrument_app(app)


# ---------------------------------------------------------------------------
# Error handlers — produce the standard error envelope from §3.7
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def _validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_failed",
                "message": "Request body failed validation",
                "details": {"errors": exc.errors()},
            },
        },
    )


@app.exception_handler(HTTPException)
async def _http_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "internal_error" if exc.status_code >= 500 else "client_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "details": None,
            },
        },
    )


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
                "details": None,
            },
        },
    )


# ---------------------------------------------------------------------------
# Operational endpoints
# ---------------------------------------------------------------------------


@app.get("/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/v1/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    # status_snapshot returns dict[str, Literal[...]]; widened here to satisfy
    # ReadyResponse's `dict[str, str]` (dicts are invariant in their value).
    statuses: dict[str, str] = dict(loader.status_snapshot())
    return ReadyResponse(ready=loader.all_loaded(), models=statuses)


@app.get("/v1/models", response_model=ModelsResponse)
async def models() -> ModelsResponse:
    statuses = loader.status_snapshot()
    loaded_at = loader.loaded_at_snapshot()
    device = get_device()
    out: list[ModelInfo] = []
    for entry in ALL_MODELS:
        out.append(
            ModelInfo(
                name=entry.name,
                hf_repo=entry.hf_repo,
                revision=entry.revision,
                device=device if statuses.get(entry.name) == "loaded" else "unknown",
                loaded_at=loaded_at.get(entry.name),
            ),
        )
    return ModelsResponse(models=out)


# ---------------------------------------------------------------------------
# Inference endpoints — §3.2–3.5
# ---------------------------------------------------------------------------


@app.post("/v1/inference/prompt_injection", response_model=PromptInjectionResponse)
async def prompt_injection(req: PromptInjectionRequest) -> PromptInjectionResponse:
    return prompt_injection_mod.classify(req)


@app.post("/v1/inference/toxicity", response_model=ToxicityResponse)
async def toxicity(req: ToxicityRequest) -> ToxicityResponse:
    return toxicity_mod.classify(req)


@app.post("/v1/inference/pii", response_model=PIIResponse)
async def pii(req: PIIRequest) -> PIIResponse:
    return pii_mod.classify(req)


@app.post("/v1/inference/claim_filter", response_model=ClaimFilterResponse)
async def claim_filter(req: ClaimFilterRequest) -> ClaimFilterResponse:
    return claim_filter_mod.classify(req)


# ---------------------------------------------------------------------------
# `uv run serve` entrypoint
# ---------------------------------------------------------------------------


def start() -> None:
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host=svc_config.HOST,
        port=svc_config.PORT,
        log_level="info",
    )


if __name__ == "__main__":
    start()

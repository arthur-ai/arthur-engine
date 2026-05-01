from fastapi import APIRouter, Response
from starlette import status

from schemas.enums import OverallWarmupStatus
from schemas.response_schemas import HealthResponse, ModelStatusResponse
from services.model_warmup_service import get_model_warmup_service
from utils import constants, utils
from utils.utils import public_endpoint

health_router = APIRouter()


@health_router.get(
    "/health",
    include_in_schema=False,
    responses={200: {"model": HealthResponse}},
)
@public_endpoint
def health() -> HealthResponse:
    """Liveness probe; always 200 once the API process is running."""
    return HealthResponse(message="ok", build_version=utils.get_genai_engine_version())


@health_router.get(
    "/readyz",
    include_in_schema=False,
    responses={
        200: {"model": ModelStatusResponse},
        503: {"model": ModelStatusResponse},
    },
)
@public_endpoint
def readyz(response: Response) -> ModelStatusResponse:
    """Readiness probe; 503 while any model is still warming, 200 once ready.

    Intended for callers (and orchestrators) to poll cheaply before sending
    real validate traffic — much friendlier than pummeling /validate_* and
    seeing per-rule MODEL_NOT_AVAILABLE responses.
    """
    snapshot = get_model_warmup_service().get_overall_status()
    if snapshot.overall_status in {
        OverallWarmupStatus.WARMING,
        OverallWarmupStatus.FAILED,
    }:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response.headers[constants.RETRY_AFTER_HEADER] = str(
            snapshot.retry_after_seconds,
        )
    return snapshot

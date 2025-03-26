from fastapi import APIRouter
from genai_engine.utils import utils
from genai_engine.utils.utils import public_endpoint
from schemas.response_schemas import HealthResponse

health_router = APIRouter()


@health_router.get(
    "/health",
    include_in_schema=False,
    responses={200: {"model": HealthResponse}},
)
@public_endpoint
def health():
    return HealthResponse(message="ok", build_version=utils.get_genai_engine_version())

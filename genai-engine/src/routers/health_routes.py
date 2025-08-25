from fastapi import APIRouter
from arthur_common.models.response_schemas import HealthResponse
from utils import utils
from utils.utils import public_endpoint

health_router = APIRouter()


@health_router.get(
    "/health",
    include_in_schema=False,
    responses={200: {"model": HealthResponse}},
)
@public_endpoint
def health():
    return HealthResponse(message="ok", build_version=utils.get_genai_engine_version())

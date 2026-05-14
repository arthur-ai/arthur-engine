from fastapi import APIRouter

from config.config import Config
from routers.route_handler import GenaiEngineRoute
from schemas.response_schemas import EngineConfigResponse
from utils.utils import public_endpoint

engine_config_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@engine_config_routes.get(
    "/engine-config",
    description="Returns engine-level configuration for the frontend. Public endpoint — no authentication required.",
    response_model=EngineConfigResponse,
    tags=["Engine Config"],
)
@public_endpoint
def get_engine_config() -> EngineConfigResponse:
    return EngineConfigResponse(demo_mode=Config.demo_mode())

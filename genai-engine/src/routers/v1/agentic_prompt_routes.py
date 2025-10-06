import logging
from typing import Any, Dict

from fastapi import APIRouter, Body

from repositories.agentic_prompts_repository import AgenticPromptRepository
from routers.route_handler import GenaiEngineRoute

logger = logging.getLogger(__name__)

agentic_prompt_routes = APIRouter(
    prefix="/v1",
    route_class=GenaiEngineRoute,
)


@agentic_prompt_routes.post(
    "/agentic_prompt/run_prompt",
    summary="Run an agentic prompt",
    description="Run an agentic prompt",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
def run_agentic_prompt(body: Dict[str, Any] = Body(...)):
    agentic_prompt_service = AgenticPromptRepository(None)
    prompt = agentic_prompt_service.create_prompt(**body)
    return agentic_prompt_service.run_prompt(prompt)

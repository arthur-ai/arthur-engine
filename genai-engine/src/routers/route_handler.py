from typing import Callable

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError as PydanticValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from dependencies import logger
from schemas.custom_exceptions import GenaiEngineLLMException
from utils import constants as constants


class GenaiEngineRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except HTTPException as exc:
                exc_info: bool = True
                if hasattr(exc, "headers") and isinstance(exc.headers, dict):
                    exc_info = exc.headers.get("full_stacktrace", "true") == "true"
                logger.error(exc.detail, exc_info=exc_info)
                if (
                    hasattr(exc, "headers")
                    and isinstance(exc.headers, dict)
                    and exc.headers.get("full_stacktrace")
                ):
                    del exc.headers["full_stacktrace"]
                raise exc
            except (PydanticValidationError, RequestValidationError) as exc:
                logger.error(str(exc), exc_info=True)
                raise HTTPException(status_code=400, detail=str(exc))
            except GenaiEngineLLMException as exc:
                logger.error(str(exc), exc_info=True)
                raise HTTPException(status_code=400, detail=str(exc.get_message()))
            except Exception as exc:
                logger.error(str(exc), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=constants.ERROR_UNCAUGHT_GENERIC,
                )

        return custom_route_handler

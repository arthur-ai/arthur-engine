import json
import logging
import logging.handlers
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Union, get_args, get_origin

from arthur_common.models.audit_log_schemas import (
    AuditLog,
    AuditLogPathParameter,
    AuditLogResponseID,
)
from arthur_common.models.enums import HTTPRequestMethod
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from config.config import Config
from schemas.audit_log_schemas import RouteInfo

logger = logging.getLogger(__name__)

SKIP_PATHS = {
    r"^/health$",
    r"^/docs$",
    r"^/openapi\.json$",
    r"^/redoc$",
    r".*/tasks/[^/]+/chatbot/stream$",
    r".*/completions$",
}

AUDIT_LOGGER = logging.getLogger("audit")

# Overrides for endpoints where collection_field or id_field differ from defaults.
# Maps response model class name -> (collection_field, id_field).
# collection_field: which field on the wrapper holds the list.
# id_field: which field on the inner type is the identifier (id_field=None will default to "id")
ENDPOINT_OVERRIDES: dict[str, tuple[str | None, str | None]] = {
    # Bare list[T] responses (collection_field=None, response is the list)
    "TokenUsageResponse": (None, "task_id"),
    # Tracing
    "TraceListResponse": ("traces", "trace_id"),
    "SpanListResponse": ("spans", None),
    "SessionListResponse": ("sessions", "session_id"),
    "SessionTracesResponse": ("traces", "trace_id"),
    "TraceUserListResponse": ("users", "user_id"),
    # Datasets
    "SearchDatasetsResponse": ("datasets", None),
    "ListDatasetVersionsResponse": ("versions", "version_number"),
    # Prompts and LLM Evals
    "LLMGetAllMetadataListResponse": ("llm_metadata", "name"),
    "AgenticPromptVersionListResponse": ("versions", "version"),
    "LLMEvalsVersionListResponse": ("versions", "version"),
    "PromptVersionResultListResponse": ("data", "dataset_row_id"),
    "PromptExperimentListResponse": ("data", None),
    # Notebook/Experiments
    "NotebookListResponse": ("data", None),
    "AgenticNotebookListResponse": ("data", None),
    "AgenticExperimentListResponse": ("data", None),
    "AgenticTestCaseListResponse": ("data", "dataset_row_id"),
    "TestCaseListResponse": ("data", "dataset_row_id"),
    # RAG
    "RagNotebookListResponse": ("data", None),
    "RagConfigResultListResponse": ("data", "dataset_row_id"),
    "RagTestCaseListResponse": ("data", "dataset_row_id"),
    "RagExperimentListResponse": ("data", None),
    "SearchRagProviderConfigurationsResponse": ("rag_provider_configurations", None),
    "SearchRagProviderCollectionsResponse": ("rag_provider_collections", "identifier"),
    "ListRagSearchSettingConfigurationsResponse": (
        "rag_provider_setting_configurations",
        None,
    ),
    "ListRagSearchSettingConfigurationVersionsResponse": (
        "rag_provider_setting_configurations",
        "setting_configuration_id",
    ),
    # Model provider
    "ModelProviderList": ("providers", "provider"),
    # Continuous Eval
    "ListContinuousEvalsResponse": ("evals", None),
    "ListAgenticAnnotationsResponse": ("annotations", None),
    "ListContinuousEvalTestRunsResponse": ("test_runs", None),
    # Transform
    "ListTraceTransformsResponse": ("transforms", None),
}


def setup_audit_logger() -> None:
    audit_log_dir = Config.audit_log_dir()
    os.makedirs(audit_log_dir, exist_ok=True)
    AUDIT_LOGGER.setLevel(logging.INFO)
    AUDIT_LOGGER.propagate = False
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(audit_log_dir, "audit.log"),
        when="D",
        interval=1,
        backupCount=Config.audit_log_retention_days(),
        utc=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    AUDIT_LOGGER.addHandler(handler)


def _get_list_inner_type_name(annotation: Any) -> str | None:
    """Extract T.__name__ from list[T]"""
    if get_origin(annotation) is not list:
        return None

    args = get_args(annotation)
    if args and isinstance(args[0], type):
        return args[0].__name__

    return None


def build_route_response_model_map(
    app: FastAPI,
) -> dict[str, RouteInfo]:
    """Build a lookup map from path template to response ID extraction info.

    For wrapper models in LIST_ENDPOINT_OVERRIDES, extracts the inner type name
    from the collection field's list[T] annotation. For bare list[T] responses,
    extracts T directly. All other endpoints are single-object responses.

    Call once at startup after all routes are registered.
    """
    result: dict[str, RouteInfo] = {}

    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.response_model:
            continue

        model = route.response_model

        # Bare list[T] response
        resource_name = _get_list_inner_type_name(model)
        if resource_name is not None:
            override = ENDPOINT_OVERRIDES.get(resource_name)
            id_field = (override[1] if override else None) or "id"
            for method in route.methods or []:
                result[f"{method}:{route.path}"] = RouteInfo(
                    resource_name=resource_name,
                    collection_field=None,
                    id_field=id_field,
                )
            continue

        if not isinstance(model, type):
            continue

        model_name = model.__name__

        if model_name in ENDPOINT_OVERRIDES:
            collection_field, id_field_override = ENDPOINT_OVERRIDES[model_name]
            id_field = id_field_override or "id"
            # Extract T.__name__ from the collection field's annotation
            field_info = (
                model.model_fields.get(collection_field)
                if hasattr(model, "model_fields")
                else None
            )
            inner_name = (
                _get_list_inner_type_name(field_info.annotation) if field_info else None
            )
            for method in route.methods or []:
                result[f"{method}:{route.path}"] = RouteInfo(
                    resource_name=inner_name or model_name,
                    collection_field=collection_field,
                    id_field=id_field,
                )
        else:
            for method in route.methods or []:
                result[f"{method}:{route.path}"] = RouteInfo(
                    resource_name=model_name,
                    collection_field=None,
                    id_field="id",
                )

    return result


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, dispatch: DispatchFunction | None = None) -> None:
        super().__init__(app, dispatch)
        self.route_map: dict[str, RouteInfo] | None = None

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        if any(re.match(p, request.url.path) for p in SKIP_PATHS) or not hasattr(
            request.state,
            "user_id",
        ):
            return response

        try:
            if self.route_map is None:
                self.route_map = build_route_response_model_map(request.app)

            response_ids = await self._get_response_ids(request, response)

            entry = AuditLog(
                id=uuid.uuid4(),
                user_id=request.state.user_id,
                timestamp=datetime.now(timezone.utc),
                request_method=HTTPRequestMethod(request.method.lower()),
                request_path=request.url.path,
                path_params=self._get_path_parameters(request.path_params),
                response_ids=response_ids,
                status_code=response.status_code,
            )

            AUDIT_LOGGER.info(entry.model_dump_json(exclude_none=True))
        except Exception:
            logger.error(
                f"Failed to write audit log entry {request.url.path}",
                exc_info=True,
            )

        return response

    def _get_path_parameters(
        self,
        path_params: dict[str, str],
    ) -> List[AuditLogPathParameter]:
        result = []

        for key, value in path_params.items():
            result.append(AuditLogPathParameter(param_name=key, param_value=value))

        return result

    async def _get_response_ids(
        self,
        request: Request,
        response: Response,
    ) -> List[AuditLogResponseID]:
        if not (200 <= response.status_code < 300):
            return []

        route_info = self._get_route_info(request)
        if not route_info:
            return []

        data = await self._read_response_body(response)
        if data is None:
            return []

        return self._extract_ids(data, route_info)

    def _get_route_info(self, request: Request) -> RouteInfo | None:
        route = request.scope.get("route")
        if not route or not hasattr(route, "path"):
            return None

        if self.route_map is None:
            return None

        key = f"{request.method}:{route.path}"
        return self.route_map.get(key)

    async def _read_response_body(
        self,
        response: Response,
    ) -> Optional[Union[dict[str, Any], list[Any]]]:
        if not hasattr(response, "body_iterator"):
            return None

        res_body_raw = [section async for section in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(res_body_raw))
        res_body_bytes = [
            chunk if isinstance(chunk, bytes) else str(chunk).encode()
            for chunk in res_body_raw
        ]
        body = b"".join(res_body_bytes).decode()

        try:
            parsed: Union[dict[str, Any], list[Any]] = json.loads(body)
            return parsed
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _extract_ids(
        data: Union[dict[str, Any], list[Any]],
        route_info: RouteInfo,
    ) -> List[AuditLogResponseID]:
        resource_name = route_info.resource_name
        collection_field = route_info.collection_field
        id_field = route_info.id_field

        if collection_field and isinstance(data, dict):
            items = data.get(collection_field, [])
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict) and id_field in data:
            return [
                AuditLogResponseID(
                    response_type=resource_name,
                    response_id=str(data[id_field]),
                    id_field=id_field,
                ),
            ]
        else:
            return []

        return [
            AuditLogResponseID(
                response_type=resource_name,
                response_id=str(item[id_field]),
                id_field=id_field,
            )
            for item in items
            if isinstance(item, dict) and id_field in item
        ]

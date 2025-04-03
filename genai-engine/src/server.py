import fcntl
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Callable

import torch
import uvicorn
from clients.telemetry.telemetry_client import TelemetryEventTypes, send_telemetry_event
from config.config import Config
from config.extra_features import extra_feature_config
from dependencies import (
    get_db_engine,
    get_db_session,
    get_keycloak_client,
    get_keycloak_settings,
    get_oauth_client,
    get_scorer_client,
)
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from opentelemetry import _logs, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from routers.api_key_routes import api_keys_routes
from routers.auth_routes import auth_routes
from routers.chat_routes import app_chat_routes
from routers.health_routes import health_router
from routers.user_routes import user_management_routes
from routers.v2.routers import (
    feedback_routes,
    query_routes,
    rule_management_routes,
    system_management_routes,
    task_management_routes,
    validate_routes,
)
from scorer.llm_client import validate_llm_connection
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from utils import constants as constants
from utils.classifiers import get_device
from utils.model_load import (
    get_claim_classifier_embedding_model,
    get_prompt_injection_model,
    get_prompt_injection_tokenizer,
    get_toxicity_model,
    get_toxicity_tokenizer,
)
from utils.utils import (
    get_env_var,
    get_genai_engine_version,
    is_api_only_mode_enabled,
    is_local_environment,
    new_relic_enabled,
)

logger = logging.getLogger()
logger.setLevel(Config.get_log_level())
stream_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
    fmt=os.environ.get("GENAI_ENGINE_LOG_FORMAT", logging.BASIC_FORMAT),
    datefmt="%Y-%m-%d %H:%M:%S %z",
)
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)
logger.info(f"GenAI Engine log level set to: {logging._levelToName[logger.level]}")

tags_metadata = [
    {
        "name": "Rules",
        "description": "Endpoints to manage rules",
    },
    {
        "name": "Tasks",
        "description": "Endpoints to manage tasks and their rules",
    },
    {
        "name": "Default Validation",
        "description": "Endpoints to validate prompt and response on default rules",
    },
    {
        "name": "Task Based Validation",
        "description": "Endpoints to validate prompt and response for a task",
    },
    {
        "name": "Feedback",
        "description": "Endpoints to manage user feedback on inferences",
    },
    {
        "name": "Usage",
        "description": "Endpoints for retrieving token usage",
    },
    {
        "name": "Inferences",
        "description": "Endpoints for querying past inferences",
    },
    {
        "name": "API Keys",
        "description": "Endpoints for API keys management",
    },
]


def bootstrap_genai_engine_keycloak():
    lock_file = "/tmp/bootstrap.lock"
    with open(lock_file, "w") as f:
        # Acquire an exclusive lock (blocking)
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            logger.info("Bootstrapping GenAI Engine Keycloak")
            # Perform the bootstrap operation
            kc_client = get_keycloak_client().__next__()
            kc_client.bootstrap_genai_engine_keycloak()
        finally:
            logger.info("GenAI Engine Keycloak bootstrapped")
            # Release the lock
            fcntl.flock(f, fcntl.LOCK_UN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    send_telemetry_event(TelemetryEventTypes.SERVER_START_INITIATED)

    device = torch.device(get_device())
    logger.info(f"Using device: {device.type}")

    try:
        db = get_db_session()
        db.close()
    except HTTPException as e:
        raise ConnectionError(f"Error connecting to database: {e}") from None

    validate_llm_connection()

    keycloak_settings = get_keycloak_settings()
    if keycloak_settings.ENABLED:
        bootstrap_genai_engine_keycloak()
    if not is_api_only_mode_enabled():
        get_oauth_client()
        time.sleep(random.randint(0, 3))

    get_claim_classifier_embedding_model()
    get_prompt_injection_model()
    get_prompt_injection_tokenizer()
    get_toxicity_model()
    get_toxicity_tokenizer()

    get_scorer_client()

    send_telemetry_event(TelemetryEventTypes.SERVER_START_COMPLETED)

    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __get_default_csp_header_list(self, keycloak_uri: str) -> list[str]:
        headers = [
            # This is the fallback policy for everything else
            "default-src 'none'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'none'",
            # Whitelist things we need:
            # Fonts are served from our url /assets, so whitelist self for them
            "font-src 'self'",
            # This allows us to hit our API
            # Docs site uses some external images / scripts / inline scripts, manually whitelist them
            "img-src 'self' fastapi.tiangolo.com data:",
            "script-src 'self' *.jsdelivr.net 'sha256-QOOQu4W1oxGqd2nbXbxiA1Di6OHQOLQD+o+G9oWL8YY=' 'nonce-b6e054c5-d77e-4712-916e-1c027d548ac4' 'unsafe-inline'",
            # @todo make nonce hash generation as part of the build process
            "style-src 'self' 'nonce-b6e054c5-d77e-4712-916e-1c027d548ac4' cdn.jsdelivr.net",
            "report-uri /api/v2/csp_report",
            "trusted-types dompurify 'allow-duplicates'",
            # "require-trusted-types-for 'script'",
        ]
        if not is_local_environment():
            headers.append("upgrade-insecure-requests")
        if keycloak_uri:
            headers.append(f"connect-src 'self' {keycloak_uri}")
        else:
            headers.append("connect-src 'self'")
        return headers

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Tell browsers to trust the content type header instead of trying to sniff the MIME type
        response.headers[constants.X_CONTENT_TYPE_OPTIONS_HEADER] = "nosniff"
        # Disallow browsers from loading GenAI Engine in an iframe
        response.headers[constants.X_FRAME_OPTIONS_HEADER] = "DENY"
        # Tell browsers to use only HTTPS to connect to this service for the next 2 years from request time
        response.headers[constants.STRICT_TRANSPORT_SECURITY_HEADER] = (
            "max-age=63072000; includeSubDomains"
        )

        keycloak_uri = ""

        # See this issue for why we can't apply the require-trusted-types-for 'script' policy to the entire site: https://github.com/acacode/swagger-typescript-api/issues/985
        response.headers[constants.CONTENT_SECURITY_POLICY_HEADER] = "; ".join(
            self.__get_default_csp_header_list(keycloak_uri),
        )
        response.headers[constants.CROSS_ORIGIN_OPENER_POLICY_HEADER] = "same-origin"
        response.headers[constants.CROSS_ORIGIN_EMBEDDER_POLICY_HEADER] = "require-corp"
        response.headers[constants.CROSS_ORIGIN_RESOURCE_POLICY_HEADER] = "same-origin"
        response.headers[constants.PERMISSIONS_POLICY_HEADER] = (
            "geolocation=(), camera=(), microphone=()"
        )
        response.headers[constants.REFERRER_POLICY_HEADER] = "no-referrer"
        return response


async def add_opentelemetry_custom_attributes(request: Request, call_next):
    s = trace.get_current_span()
    s.set_attribute("http.client_ip", request.client.host)
    if "X-Forwarded-For" in request.headers:
        s.set_attribute("http.x_forwarded_for", request.headers["X-Forwarded-For"])
    response = await call_next(request)
    if s is not None:
        response.headers[constants.RESPONSE_TRACE_ID_HEADER] = hex(
            s.get_span_context().trace_id,
        ).removeprefix("0x")
    return response


def setup_newrelic(app: FastAPI):
    app.add_middleware(BaseHTTPMiddleware, dispatch=add_opentelemetry_custom_attributes)

    OTEL_RESOURCE_ATTRIBUTES = {
        "service.name": get_env_var(constants.NEWRELIC_APP_NAME_ENV_VAR),
    }

    t = TracerProvider(resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES))
    trace.set_tracer_provider(t)

    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter()),
    )

    SQLAlchemyInstrumentor().instrument(tracer_provider=t, engine=get_db_engine())

    FastAPIInstrumentor.instrument_app(app)

    _logs.set_logger_provider(
        LoggerProvider(resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES)),
    )
    h = LoggingHandler(
        logger_provider=_logs.get_logger_provider().add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter()),
        ),
    )

    logger.addHandler(h)
    logging.getLogger("uvicorn.access").addHandler(h)


def get_base_app(
    version: str = get_genai_engine_version(),
    lifespan: Callable | None = lifespan,
) -> FastAPI:
    logger.info(f"Booting up Arthur GenAI Engine: {version}")
    kwargs = {}
    if lifespan:
        kwargs["lifespan"] = lifespan
    app = FastAPI(
        title="Arthur GenAI Engine",
        version=version,
        openapi_tags=tags_metadata,
        **kwargs,
    )
    origins = [
        "http://localhost",
        "http://0.0.0.0:8000",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    if ingress_url := get_env_var(
        constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR,
        none_on_missing=True,
    ):
        origins.append(ingress_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def add_routers(app: FastAPI, routers: list[APIRouter]):
    for router in routers:
        app.include_router(router)


def get_app_with_routes() -> FastAPI:
    app = get_base_app(lifespan=None)
    add_routers(
        app,
        [
            health_router,
            system_management_routes,
            feedback_routes,
            query_routes,
            rule_management_routes,
            task_management_routes,
            validate_routes,
            api_keys_routes,
        ],
    )
    add_routers(app, [auth_routes, user_management_routes])
    add_routers(app, [app_chat_routes])
    return app


def get_test_app() -> FastAPI:
    app = get_base_app()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=Config.app_secret_key())
    add_routers(
        app,
        [
            health_router,
            system_management_routes,
            feedback_routes,
            query_routes,
            rule_management_routes,
            task_management_routes,
            validate_routes,
            api_keys_routes,
        ],
    )
    add_routers(app, [auth_routes, user_management_routes])
    add_routers(app, [app_chat_routes])

    if is_api_only_mode_enabled():

        @app.get("/", include_in_schema=False)
        async def redirect_to_docs():
            return RedirectResponse("/docs")

    return app


def get_app() -> FastAPI:
    app = get_base_app()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=Config.app_secret_key())
    if new_relic_enabled():
        setup_newrelic(app)

    add_routers(
        app,
        [
            health_router,
            system_management_routes,
            feedback_routes,
            query_routes,
            rule_management_routes,
            task_management_routes,
            validate_routes,
            api_keys_routes,
        ],
    )
    if extra_feature_config.CHAT_ENABLED:
        add_routers(app, [app_chat_routes])
    if not is_api_only_mode_enabled():
        add_routers(app, [auth_routes, user_management_routes])

    if is_api_only_mode_enabled():

        @app.get("/", include_in_schema=False)
        async def redirect_to_docs():
            return RedirectResponse("/docs")

    return app


def start():
    send_telemetry_event(TelemetryEventTypes.SERVER_START_INITIATED)
    app = get_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start()

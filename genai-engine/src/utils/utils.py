import asyncio
import functools
import logging
import os
import re
import traceback
import urllib
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

from arthur_common.models.common_schemas import (
    LLMTokenConsumption,
    PaginationParameters,
)
from arthur_common.models.enums import PaginationSortMethod
from dotenv import load_dotenv
from fastapi import HTTPException, Query
from langchain_community.callbacks import OpenAICallbackHandler
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer
from sqlalchemy.orm import Session

import utils.constants as constants
from custom_types import P, T

_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_genai_engine_version = None

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()
load_dotenv()

list_indicator_regex = re.compile(r"^[\-\•\*]|\d+\)|\d+\.")


def new_relic_enabled() -> bool:
    return (
        get_env_var(
            constants.NEWRELIC_ENABLED_ENV_VAR,
            none_on_missing=False,
            default="false",
        )
        == "true"
    )


def relevance_models_enabled() -> bool:
    """Check if relevance models (BERT scorer and reranker) are enabled."""
    if enable_relevance_models := get_env_var(
        constants.ENABLE_RELEVANCE_MODELS_ENV_VAR,
        none_on_missing=False,
        default="false",
    ):
        return enable_relevance_models.lower() == "true"
    return False


def log_llm_metrics(
    operation: str,
    openai_callback: OpenAICallbackHandler,
) -> LLMTokenConsumption:
    prompt_tokens, completion_tokens = (
        openai_callback.prompt_tokens,
        openai_callback.completion_tokens,
    )
    logger.debug(
        "Prompt / response tokens consumed for operation %s: %d/%d"
        % (operation, prompt_tokens, completion_tokens),
    )
    return LLMTokenConsumption(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


class TracedThreadPoolExecutor(ThreadPoolExecutor):
    """Implementation of :class:`ThreadPoolExecutor` that will pass context into sub tasks."""

    def __init__(self, tracer: Tracer, *args: Any, **kwargs: Any) -> None:
        self.tracer = tracer
        super().__init__(*args, **kwargs)

    def with_otel_context(
        self,
        context: otel_context.Context,
        fn: Callable[..., T],
    ) -> T:
        otel_context.attach(context)
        return fn()

    # "/" marker in function signature is to enforce positional-only arguments
    def submit(
        self,
        fn: Callable[P, T],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Future[T]:
        """Submit a new task to the thread pool."""

        # get the current otel context
        context = otel_context.get_current()
        if context:
            return super().submit(
                lambda: self.with_otel_context(context, lambda: fn(*args, **kwargs)),
            )
        else:
            return super().submit(lambda: fn(*args, **kwargs))


def get_postgres_connection_string(
    use_ssl: bool = False,
    ssl_key_path: str | None = None,
) -> str:
    postgres_user = os.environ["POSTGRES_USER"]
    postgres_pass = os.environ["POSTGRES_PASSWORD"]
    postgres_url = os.environ["POSTGRES_URL"]
    postgres_port = os.environ["POSTGRES_PORT"]
    postgres_db_name = os.environ["POSTGRES_DB"]

    params = {}

    if use_ssl:
        params["sslmode"] = "verify-full"
    if ssl_key_path is not None:
        params["sslrootcert"] = ssl_key_path

    query_params = urllib.parse.urlencode(params)

    connection_string = (
        f"postgresql+psycopg2://{postgres_user}:{postgres_pass}@{postgres_url}:{postgres_port}/{postgres_db_name}?"
        + query_params
    )

    return connection_string


def get_jwks_uri() -> str:
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    jwks_uri: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    )
    return jwks_uri


def get_auth_metadata_uri() -> str:
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    auth_metadata_url: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
    )
    return auth_metadata_url


def get_auth_logout_uri(redirect_uri: str, id_token: str) -> str:
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    AUTH_CLIENT_ID = get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)
    auth_logout_uri: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout?post_logout_redirect_uri={redirect_uri}&client_id={AUTH_CLIENT_ID}"
    )
    if id_token:
        auth_logout_uri = auth_logout_uri + f"&id_token_hint={id_token}"
    return auth_logout_uri


def seed_database(db_session: Session) -> None:
    rows: list[Any] = []

    db_session.add_all(rows)
    db_session.commit()


def get_env_var(
    env_var: str,
    none_on_missing: bool = False,
    default: str | None = None,
) -> str | None:
    value = os.environ.get(env_var, default)
    logger.debug(f"Environment variable {env_var} has value {value}")
    if none_on_missing and not value:
        return None
    elif not value:
        raise ValueError("Environment variable %s not defined" % env_var)
    return value


def get_genai_engine_version() -> str:
    global _genai_engine_version
    if _genai_engine_version is not None:
        return _genai_engine_version

    try:
        version_file_dir = get_version_file_path()
        with open(version_file_dir, "r") as f:
            version = f.read().strip()
        _genai_engine_version = version
    except Exception as e:
        logger.error("Can't read the version file")
        logger.error(traceback.format_exception(e))
        raise e
    return _genai_engine_version


def get_version_file_path() -> str:
    version_file_backend_dir_path = f"{_root_dir}/version"
    version_file_genai_engine_dir_path = f"{os.path.dirname(_root_dir)}/version"
    if os.path.exists(version_file_backend_dir_path):
        return version_file_backend_dir_path
    elif os.path.exists(version_file_genai_engine_dir_path):
        return version_file_genai_engine_dir_path
    else:
        raise Exception("The genai-engine version file not found")


def is_local_environment() -> bool:
    return (
        get_env_var(constants.GENAI_ENGINE_ENVIRONMENT_ENV_VAR, none_on_missing=True)
        == "local"
    )


def is_api_only_mode_enabled() -> bool:
    api_only_mode_enabled = (
        get_env_var(
            constants.GENAI_ENGINE_API_ONLY_MODE_ENABLED_ENV_VAR,
            default="enabled",
        )
        == "enabled"
    )
    return api_only_mode_enabled


def is_agentic_ui_enabled() -> bool:
    agentic_ui_enabled = (
        get_env_var(
            constants.GENAI_ENGINE_AGENTIC_UI_ENABLED_ENV_VAR,
            default="enabled",
        )
        == "enabled"
    )
    return agentic_ui_enabled


def internal_features_enabled() -> bool:
    ingress_url = get_env_var(
        constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR,
        none_on_missing=True,
    )
    if not ingress_url:
        return False
    return "arthur.ai" in ingress_url or "localhost" in ingress_url


async def common_pagination_parameters(
    sort: PaginationSortMethod = Query(
        PaginationSortMethod.DESCENDING,
        description="Sort the results (asc/desc)",
    ),
    page_size: int = Query(
        10,
        description=f"Page size. Default is 10. Must be greater than 0 and less than {constants.MAX_PAGE_SIZE}.",
    ),
    page: int = Query(0, description="Page number"),
) -> PaginationParameters:
    if page_size > constants.MAX_PAGE_SIZE or page_size <= 0:
        raise HTTPException(status_code=400, detail=constants.ERROR_PAGE_SIZE_TOO_LARGE)
    return PaginationParameters(sort=sort, page_size=page_size, page=page)


def pad_text(
    text: str | list[str],
    min_length: int = 20,
    delim: str = " ",
    pad_type: str = "whitespace",
) -> str | list[str]:
    """
    Returns the text (as a string or list of strings) padded to extend the string to a minimum length
    """
    if isinstance(text, list):
        result: list[str] = []
        for element in text:
            padded = pad_text(element, min_length=min_length, pad_type=pad_type)
            assert isinstance(padded, str)  # element is str, so result must be str
            result.append(padded)
        return result
    while len(text) < min_length:
        if pad_type == "whitespace":
            text = text + delim
        elif pad_type == "repetition":
            text = text + text + delim
    return text


def alphanumericize(text: str) -> str:
    """
    Removes non-alphanumeric characters (including spaces) from text and converts to lowercase

    :param text: text to alphanumericize
    """
    return re.sub(r"\W+", "", text).lower()


def calculate_duration_ms(start_time: datetime, end_time: datetime) -> float:
    """
    Calculate duration between two datetime objects in milliseconds.

    Args:
        start_time: Start datetime
        end_time: End datetime

    Returns:
        Duration in milliseconds as a float
    """
    return (end_time - start_time).total_seconds() * 1000.0


def public_endpoint(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to explicitly mark an endpoint as publicly available.
    This will log a debug message when the endpoint is accessed.
    """

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        logger.debug(f"Accessing public endpoint: {func.__name__}")
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    # Mark the function as intentionally public
    async_wrapper._is_public = True  # type: ignore[attr-defined]
    return async_wrapper  # type: ignore[return-value]

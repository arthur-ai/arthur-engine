import asyncio
import functools
import logging
import os
import re
import string
import traceback
import urllib
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Union

import commonmark
import utils.constants as constants
from dotenv import load_dotenv
from fastapi import HTTPException, Query
from nltk.tokenize.punkt import PunktSentenceTokenizer
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer
from schemas.common_schemas import LLMTokenConsumption, PaginationParameters
from schemas.enums import PaginationSortMethod
from sqlalchemy.orm import Session
from utils.abbreviations import ABBREVIATIONS

_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_genai_engine_version = None

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()
load_dotenv(os.environ.get(constants.GENAI_ENGINE_ENV_FILE_ENV_VAR))

list_indicator_regex = re.compile(r"^[\-\•\*]|\d+\)|\d+\.")
sentence_tokenizer = PunktSentenceTokenizer()


def new_relic_enabled():
    return (
        get_env_var(
            constants.NEWRELIC_ENABLED_ENV_VAR,
            none_on_missing=False,
            default="false",
        )
        == "true"
    )


def log_llm_metrics(operation: str, openai_callback):
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

    def __init__(self, tracer: Tracer, *args, **kwargs):
        self.tracer = tracer
        super().__init__(*args, **kwargs)

    def with_otel_context(self, context: otel_context.Context, fn: Callable):
        otel_context.attach(context)
        return fn()

    def submit(self, fn, *args, **kwargs):
        """Submit a new task to the thread pool."""

        # get the current otel context
        context = otel_context.get_current()
        if context:
            return super().submit(
                lambda: self.with_otel_context(context, lambda: fn(*args, **kwargs)),
            )
        else:
            return super().submit(lambda: fn(*args, **kwargs))


def get_postgres_connection_string(use_ssl=False, ssl_key_path=None):
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


def get_jwks_uri():
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    jwks_uri: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    )
    return jwks_uri


def get_auth_metadata_uri():
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    auth_metadata_url: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
    )
    return auth_metadata_url


def get_auth_logout_uri(redirect_uri: str, id_token: str):
    KEYCLOAK_HOST_URI = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR)
    KEYCLOAK_REALM = get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR)
    AUTH_CLIENT_ID = get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)
    auth_logout_uri: str = (
        f"{KEYCLOAK_HOST_URI}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout?post_logout_redirect_uri={redirect_uri}&client_id={AUTH_CLIENT_ID}"
    )
    if id_token:
        auth_logout_uri = auth_logout_uri + f"&id_token_hint={id_token}"
    return auth_logout_uri


def seed_database(db_session: Session):
    rows = []

    db_session.add_all(rows)
    db_session.commit()


def get_env_var(env_var: str, none_on_missing=False, default=None):
    value = os.environ.get(env_var, default)
    logger.debug(f"Environment variable {env_var} has value {value}")
    if none_on_missing and not value:
        return None
    elif not value:
        raise ValueError("Environment variable %s not defined" % env_var)
    return value


def get_genai_engine_version():
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


def get_version_file_path():
    version_file_backend_dir_path = f"{_root_dir}/version"
    version_file_genai_engine_dir_path = f"{os.path.dirname(_root_dir)}/version"
    if os.path.exists(version_file_backend_dir_path):
        return version_file_backend_dir_path
    elif os.path.exists(version_file_genai_engine_dir_path):
        return version_file_genai_engine_dir_path
    else:
        raise Exception("The genai-engine version file not found")


def is_local_environment():
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


def internal_features_enabled():
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


def deduplicate(seq: list[str]) -> list[str]:
    """
    Source: https://stackoverflow.com/a/480227/1493011
    """

    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def strip_markdown(text: str) -> str:
    """
    Strip Markdown from a LLM Response
    """
    parser = commonmark.Parser()

    def ast2text(astNode):
        """
        Returns the text from markdown, stripped of the markdown syntax itself
        """
        walker = astNode.walker()
        acc = ""
        iterator = iter(walker)
        list_level = 0
        for current, entering in iterator:
            if current.literal and not (
                current.parent
                and current.parent.t == "link"
                and current.parent.destination == current.literal
            ):
                acc += current.literal
            if current.t == "linebreak":
                acc += "\n"
            elif current.t == "softbreak":
                acc += " "
            elif current.t == "list" and entering:
                if list_level > 0:
                    # Already in a list
                    acc = acc.strip() + " "
                    # Sub the last new line, the rest of the item is supposed to be on the same line
                list_level += 1
            elif current.t == "list" and not entering:
                list_level -= 1
                if list_level <= 1:
                    acc = acc.strip()
                    acc += "\n"
            elif current.t == "paragraph" and not entering:
                if list_level > 1:
                    if acc[-1] in string.punctuation:
                        acc = acc[:-1]  # Strip punctuation for list items
                    acc += " "  # Don't add new line until exiting nested alist
                else:
                    acc = acc.strip()
                    acc += "\n"
            elif current.t == "heading" and not entering:
                acc += " "
            elif current.t in ("link", "image") and entering is False:
                acc += f" {current.destination}"
                if current.title:
                    acc += f" - {current.title}"
        return acc.strip()

    try:
        ast = parser.parse(text)
        parsed = ast2text(ast)
    except Exception as e:
        parsed = text
        logger.warning(f"Failed to parse text with exception {e}")

    return parsed


def custom_text_parser(text, delims="all") -> list[str]:
    """
    Returns a list of texts that should contain sentences & list items from an LLM response
    """
    text = strip_markdown(text)
    abbreviation_pattern = r"([A-Za-z]\.)([A-Za-z]\.)+"
    all_abbreviations = re.finditer(abbreviation_pattern, text)

    # Iterate through all found emails and replace .com
    for abbrev in all_abbreviations:
        found = abbrev.group(0)
        text = text.replace(found, found.replace(".", ""))

    for s in ABBREVIATIONS:
        text = text.replace(s, s.replace(".", ""))

    lines = text.strip().split("\n")
    texts = []
    for line in lines:
        line = line.strip()
        if list_indicator_regex.match(line.strip()):
            texts.append(line.strip())
        else:
            texts.extend(sentence_tokenizer.tokenize(line))
    return deduplicate(texts)


def pad_text(
    text: Union[str, List[str]],
    min_length: int = 20,
    delim: str = " ",
    type: str = "whitespace",
) -> Union[str, List[str]]:
    """
    Returns the text (as a string or list of strings) padded to extend the string to a minimum length
    """
    if isinstance(text, list):
        return [pad_text(t, min_length=min_length, type=type) for t in text]
    while len(text) < min_length:
        if type == "whitespace":
            text = text + delim
        elif type == "repetition":
            text = text + text + delim
    return text


def alphanumericize(text: str) -> str:
    """
    Removes non-alphanumeric characters (including spaces) from text and converts to lowercase

    :param text: text to alphanumericize
    """
    return re.sub(r"\W+", "", text).lower()


def public_endpoint(func):
    """
    Decorator to explicitly mark an endpoint as publicly available.
    This will log a debug message when the endpoint is accessed.
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger.debug(f"Accessing public endpoint: {func.__name__}")
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    # Mark the function as intentionally public
    async_wrapper._is_public = True
    return async_wrapper

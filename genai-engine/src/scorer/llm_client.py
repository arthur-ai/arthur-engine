import datetime
import logging
import os
import random
from datetime import datetime as dt

import openai
from config.openai_config import GenaiEngineOpenAIProvider, OpenAISettings
from langchain_community.callbacks import get_openai_callback
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)
from opentelemetry import trace
from schemas.common_schemas import LLMTokenConsumption
from schemas.custom_exceptions import (
    LLMContentFilterException,
    LLMExecutionException,
    LLMMaxRequestTokensException,
    LLMTokensPerPeriodRateLimitException,
)
from schemas.enums import RuleResultEnum
from schemas.scorer_schemas import RuleScore, ScorerRuleDetails

logger = logging.getLogger()

from utils import constants, utils

llm_executor = None

tracer = trace.get_tracer(__name__)

DEFAULT_TEMPERATURE = 0.0


class LLMTokensPerPeriodRateLimiter:
    def __init__(self, rate_limit=20000, period_seconds=60):
        self.calls = []
        self.rate_limit = rate_limit
        self.period_milliseconds = period_seconds * 1000

    def add_request(self, token_consumption: LLMTokenConsumption):
        self.calls.append((dt.now(), token_consumption.total_tokens()))

    def request_allowed(self):
        t = dt.now()
        self.calls = [
            c
            for c in self.calls
            if (t - c[0]) < datetime.timedelta(milliseconds=self.period_milliseconds)
        ]
        window_token_consumption = sum([c[1] for c in self.calls])
        if window_token_consumption < self.rate_limit:
            return True
        else:
            logger.warning(
                "%d tokens used in the past %d milliseconds exceeded the rate limit of %d"
                % (window_token_consumption, self.period_milliseconds, self.rate_limit),
            )
            raise LLMTokensPerPeriodRateLimitException


class LLMExecutor:
    def __init__(self, llm_config: OpenAISettings):
        self.azure_openai_enabled = (
            llm_config.GENAI_ENGINE_OPENAI_PROVIDER.value
            == GenaiEngineOpenAIProvider.AZURE.value
        )
        self.openai_enable = (
            llm_config.GENAI_ENGINE_OPENAI_PROVIDER.value
            == GenaiEngineOpenAIProvider.OPENAI.value
        )
        self.requests = LLMTokensPerPeriodRateLimiter(
            rate_limit=llm_config.GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD,
            period_seconds=llm_config.GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS,
        )

        self.gpt_hosts = llm_config.GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS

        self.embeddings_hosts = (
            llm_config.GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS
        )
        if self.azure_openai_enabled:
            self.api_version = llm_config.OPENAI_API_VERSION

    @staticmethod
    def _get_random_connection_details(
        contract: str,
    ) -> tuple[str | None, str | None, str | None]:
        try:
            random_model = random.choice(contract.strip().split(","))
            model_name, endpoint, api_key = random_model.split("::")

            model_name = model_name if model_name else None
            endpoint = endpoint if endpoint else None
            api_key = api_key if api_key else None
        except (ValueError, IndexError, AttributeError):
            logger.warning(f"LLM connection string could not be parsed: {contract}")
            model_name, endpoint, api_key = None, None, None
        return model_name, endpoint, api_key

    def get_gpt_model(
        self,
        chat_temperature=DEFAULT_TEMPERATURE,
    ) -> AzureChatOpenAI | ChatOpenAI:
        model_name, endpoint, key = self._get_random_connection_details(self.gpt_hosts)
        if not model_name or not key:
            return None
        elif self.azure_openai_enabled:
            return AzureChatOpenAI(
                deployment_name=model_name,
                azure_endpoint=endpoint,
                api_key=key,
                temperature=chat_temperature,
                api_version=self.api_version,
            )
        elif self.openai_enable:
            if endpoint:
                logger.info(
                    f"""
                    You are using the OpenAI API with a custom base_url.
                    This is not recommended if you are using the OpenAI API and only
                    makes sense if you are using the OpenAI API with a proxy or pointing at a model that is compatible with the OpenAI API.

                    If this was unintentional, please update your GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS and leave the base_url value empty.
                    """,
                )
                return ChatOpenAI(
                    model=model_name,
                    base_url=endpoint,
                    api_key=key,
                    temperature=chat_temperature,
                )
            else:
                return ChatOpenAI(
                    model=model_name,
                    api_key=key,
                    temperature=chat_temperature,
                )

    def get_embeddings_model(self) -> AzureOpenAIEmbeddings | OpenAIEmbeddings | None:
        model_name, endpoint, key = self._get_random_connection_details(
            self.embeddings_hosts,
        )
        model = None
        if self.azure_openai_enabled:
            model = AzureOpenAIEmbeddings(
                deployment=model_name,
                azure_endpoint=endpoint,
                openai_api_key=key,
            )
        elif self.openai_enable:
            model = OpenAIEmbeddings(
                model=model_name,
                base_url=endpoint,
                api_key=key,
                openai_api_type="openai",
            )
        return model

    @tracer.start_as_current_span("OpenAI")
    def execute(self, f, operation_name: str):
        if not self.requests.request_allowed():
            # Throw an error, delay, what do?
            pass
        with get_openai_callback() as cb:
            try:
                result = f()
                token_consumption = utils.log_llm_metrics(operation_name, cb)
                self.requests.add_request(token_consumption)
                return result, token_consumption
            except openai.RateLimitError as e:
                logger.warning(
                    f"OpenAI API request exceeded rate limit by {operation_name}: {e}",
                )
                raise LLMExecutionException(
                    "GenAI Engine was unable to evaluate due to an upstream API rate limit",
                )
            except openai.APIConnectionError as e:
                logger.warning(
                    f"Failed to connect to OpenAI API by {operation_name}: {e}",
                )
                raise LLMExecutionException(
                    "GenAI Engine was unable to evaluate due to an upstream API connection error",
                )
            except openai.APIError as e:
                if e.code == "context_length_exceeded":
                    logger.warning(
                        f"OpenAI API request context length exceeded by {operation_name}: {e}",
                    )
                    raise LLMMaxRequestTokensException(
                        "GenAI Engine was unable to evaluate due to max request token.",
                    )
                elif e.code == "rate_limit_exceeded":
                    logger.warning(
                        f"OpenAI API request rate limit exceeded by {operation_name}: {e}",
                    )
                    raise LLMExecutionException(
                        "GenAI Engine was unable to evaluate due to upstream API rate limit",
                    )
                elif e.code == "insufficient_quota":
                    logger.warning(
                        f"OpenAI API request experienced insufficient quota by {operation_name}: {e}",
                    )
                    raise LLMExecutionException(
                        "GenAI Engine was unable to evaluate due to upstream API quota",
                    )
                elif e.code == "content_filter":
                    logger.warning(
                        f"OpenAI API request content filter triggered by {operation_name}: {e}",
                    )
                    raise LLMContentFilterException()
                else:
                    logger.warning(
                        f"OpenAI API request error triggered by {operation_name}: {e}",
                    )
                    raise LLMExecutionException(
                        "GenAI Engine was unable to evaluate due to an upstream API request error",
                    )


def get_llm_executor():
    global llm_executor
    openai_config = OpenAISettings(
        _env_file=os.environ.get("OPENAI_CONFIG_FILE", ".env"),
    )
    if llm_executor is None:
        llm_executor = LLMExecutor(llm_config=openai_config)
    return llm_executor


def validate_llm_connection():
    get_llm_executor().get_gpt_model().invoke("Return 1")


def handle_llm_exception(e) -> RuleScore:
    error_message = constants.ERROR_DEFAULT_RULE_ENGINE
    if isinstance(e, LLMContentFilterException):
        error_message = str(e)
    elif isinstance(e, LLMTokensPerPeriodRateLimitException):
        error_message = constants.ERROR_GENAI_ENGINE_RATE_LIMIT_EXCEEDED
    elif isinstance(e, LLMMaxRequestTokensException):
        error_message = constants.ERROR_TOKEN_LIMIT_EXCEEDED
    elif isinstance(e, LLMExecutionException):
        error_message = str(e)

    return RuleScore(
        result=RuleResultEnum.UNAVAILABLE,
        details=ScorerRuleDetails(message=error_message),
    )

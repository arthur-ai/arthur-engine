"""The model the built-in LLM checks run on, resolved on every call.

The checks (hallucination, sensitive data, relevance, tool selection) keep their
LangChain prompts and run them through a judge:

- EnvJudge runs them exactly as before, on the GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
  model through LangChain.
- DefaultModelJudge renders the same prompt into messages and calls the default model
  provider through LLMClient, which bills the org and enforces its quota.

GENAI_ENGINE_LLM_CHECKS_MODEL_SOURCE picks between them. In "auto", the env model wins
when it is set, so an install whose checks were benchmarked on it doesn't move to the
default model just because someone set one for the chatbot. A judge is never swapped
after a failure: a runtime error (auth, rate limit, timeout) leaves the rule unavailable.
"""

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Protocol, TypeVar, cast

import litellm
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from langchain_core.messages import convert_to_openai_messages
from langchain_core.prompts import BasePromptTemplate
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.openai_config import LLMChecksModelSource, LLMChecksSettings
from db_models import DatabaseTask
from monitoring.ai_activity import record_model_invocation
from schemas.audit_log_schemas import ModelInvocation
from schemas.custom_exceptions import (
    LLMContentFilterException,
    LLMExecutionException,
    LLMMaxRequestTokensException,
)
from scorer.llm_client import LLMExecutor, get_llm_executor
from utils.constants import DEFAULT_ORG_ID

if TYPE_CHECKING:
    # The LLM client imports repositories that import dependencies, which builds the
    # scorers that import this module; at run time it's imported where it's used.
    from clients.llm.llm_client import LLMClient, LLMModelResponse

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)
# The checks pass string and chat prompts alike
Prompt = BasePromptTemplate[Any]

_billing_org: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "llm_checks_billing_org",
    default=None,
)


@contextmanager
def llm_checks_billed_to(org_id: uuid.UUID | None) -> Iterator[None]:
    """Bill the default-model LLM checks resolved inside this block to the org; the
    default org when None (a taskless validation)."""
    token = _billing_org.set(org_id)
    try:
        yield
    finally:
        _billing_org.reset(token)


def task_org_id(db_session: Session, task_id: str | None) -> uuid.UUID | None:
    """The org that owns the task, which the task's LLM checks are billed to."""
    if not task_id:
        return None
    org_id: uuid.UUID | None = db_session.scalar(
        select(DatabaseTask.org_id).where(DatabaseTask.id == task_id),
    )
    return org_id


class LLMJudge(Protocol):
    model_name: str | None

    def supports_structured_output(self) -> bool: ...

    def max_input_tokens(self) -> int | None: ...

    def structured(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        schema: type[SchemaT],
        operation: str,
    ) -> tuple[SchemaT, LLMTokenConsumption]: ...

    def text(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        operation: str,
    ) -> tuple[str, LLMTokenConsumption]: ...


def message_text(content: Any) -> str:
    """A model message's content as text; LangChain may return a list of parts."""
    if isinstance(content, str):
        return content
    return "".join(str(part) for part in content or [])


class EnvJudge:
    """The GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS model, through LangChain."""

    def __init__(self, executor: LLMExecutor, temperature: float):
        model = executor.get_gpt_model(chat_temperature=temperature)
        if model is None:
            raise ValueError("No model is configured in the environment.")
        self.executor = executor
        self.model = model
        self.model_name: str | None = getattr(model, "model_name", None)

    def supports_structured_output(self) -> bool:
        return self.executor.supports_structured_outputs()

    def max_input_tokens(self) -> int | None:
        limit = self.executor.get_gpt_model_token_limit()
        return None if limit == -1 else limit

    def structured(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        schema: type[SchemaT],
        operation: str,
    ) -> tuple[SchemaT, LLMTokenConsumption]:
        chain = prompt | self.model.with_structured_output(schema)
        result, tokens = self.executor.execute(
            lambda: chain.invoke(inputs),
            operation,
            model_name=self.model_name,
        )
        # Some LangChain structured-output methods return a dict, not the schema
        if not isinstance(result, schema):
            result = schema.model_validate(result)
        return result, tokens

    def text(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        operation: str,
    ) -> tuple[str, LLMTokenConsumption]:
        chain = prompt | self.model
        message, tokens = self.executor.execute(
            lambda: chain.invoke(inputs),
            operation,
            model_name=self.model_name,
        )
        return message_text(message.content), tokens


class DefaultModelJudge:
    """The default model provider, through LiteLLM."""

    def __init__(
        self,
        client: "LLMClient",
        provider: ModelProvider,
        model_name: str,
        org_id: uuid.UUID,
    ):
        self.client = client
        self.provider = provider
        self.model_name: str | None = model_name
        self.org_id = org_id

    def supports_structured_output(self) -> bool:
        from clients.llm.llm_client import supports_structured_output

        return supports_structured_output(self.provider, str(self.model_name))

    def max_input_tokens(self) -> int | None:
        try:
            info = litellm.get_model_info(
                model=str(self.model_name),
                custom_llm_provider=self.provider.value,
            )
        except Exception:  # litellm raises for models missing from its map
            return None
        window: int | None = info.get("max_input_tokens")
        return window

    def structured(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        schema: type[SchemaT],
        operation: str,
    ) -> tuple[SchemaT, LLMTokenConsumption]:
        response, tokens = self._complete(prompt, inputs, operation, schema)
        # _complete checked the type, inside the audited call
        return cast(SchemaT, response.structured_output_response), tokens

    def text(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        operation: str,
    ) -> tuple[str, LLMTokenConsumption]:
        response, tokens = self._complete(prompt, inputs, operation, None)
        return _response_text(response), tokens

    def _complete(
        self,
        prompt: Prompt,
        inputs: dict[str, Any],
        operation: str,
        schema: type[BaseModel] | None,
    ) -> tuple["LLMModelResponse", LLMTokenConsumption]:
        kwargs: dict[str, Any] = {
            "model": f"{self.provider.value}/{self.model_name}",
            "messages": convert_to_openai_messages(
                prompt.format_prompt(**inputs).to_messages(),
            ),
        }
        if schema is not None:
            kwargs["response_format"] = schema
        # No temperature: current Claude models reject it, and the checks' prompts
        # don't depend on one.
        tokens = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)
        start = time.perf_counter()
        error_type: str | None = None
        try:
            response = self.client.completion(org_id=self.org_id, **kwargs)
            usage = getattr(response.response, "usage", None)
            tokens = LLMTokenConsumption(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            )
            # A reply with no answer must not read as one: a check scoring
            # "no 'yes' in the text" would pass it
            if schema is not None:
                if not isinstance(response.structured_output_response, schema):
                    raise LLMExecutionException(
                        "GenAI Engine was unable to evaluate: the model's response "
                        "didn't match the expected format",
                    )
            elif not _response_text(response).strip():
                raise LLMExecutionException(
                    "GenAI Engine was unable to evaluate: the model returned no answer",
                )
            return response, tokens
        except Exception as e:
            error_type = type(_provider_error(e)).__name__
            raise _scorer_exception(e) from e
        finally:
            record_model_invocation(
                ModelInvocation(
                    model_name=self.model_name,
                    provider=self.provider.value,
                    model_type="llm",
                    operation=operation,
                    prompt_tokens=tokens.prompt_tokens,
                    completion_tokens=tokens.completion_tokens,
                    total_tokens=tokens.prompt_tokens + tokens.completion_tokens,
                    latency_ms=int((time.perf_counter() - start) * 1000),
                    success=error_type is None,
                    error_type=error_type,
                ),
            )


def _response_text(response: "LLMModelResponse") -> str:
    choices = getattr(response.response, "choices", None) or []
    return message_text(choices[0].message.content) if choices else ""


def _provider_error(e: Exception) -> BaseException:
    # LLMClient re-raises LiteLLM errors as HTTPException inside its except blocks,
    # which leaves the original on __context__.
    if isinstance(e, HTTPException) and e.__context__ is not None:
        return e.__context__
    return e


def _scorer_exception(e: Exception) -> Exception:
    """The exception the checks turn into an unavailable rule result."""
    if isinstance(e, LLMExecutionException):
        return e
    cause = _provider_error(e)
    if isinstance(cause, litellm.ContextWindowExceededError):
        return LLMMaxRequestTokensException(
            "GenAI Engine was unable to evaluate due to max request token.",
        )
    if isinstance(cause, litellm.ContentPolicyViolationError):
        return LLMContentFilterException()
    if isinstance(cause, litellm.RateLimitError):
        return LLMExecutionException(
            "GenAI Engine was unable to evaluate due to an upstream API rate limit",
        )
    if isinstance(cause, (litellm.Timeout, litellm.APIConnectionError)):
        return LLMExecutionException(
            "GenAI Engine was unable to evaluate due to an upstream API connection error",
        )
    if isinstance(e, HTTPException):
        return LLMExecutionException(
            f"GenAI Engine was unable to evaluate due to an upstream API request error: {e.detail}",
        )
    if isinstance(e, ValidationError):
        return LLMExecutionException(
            "GenAI Engine was unable to evaluate: the model's response didn't match "
            "the expected format",
        )
    return LLMExecutionException(
        f"GenAI Engine was unable to evaluate due to an upstream error: {type(e).__name__}",
    )


# The deployment templates ship GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS with
# these, and setup writes them when an LLM is skipped.
PLACEHOLDER_MODEL_NAME = "model_name"
PLACEHOLDER_API_KEY = "my_api_key"


def env_model_is_placeholder(names_endpoints_keys: str | None) -> bool:
    """True when the env model setting holds only the templates' placeholders."""
    if not isinstance(names_endpoints_keys, str):
        return names_endpoints_keys is None
    entries = [e for e in names_endpoints_keys.split(",") if e.strip()]
    if not entries:
        return True
    for entry in entries:
        parts = entry.strip().split("::")
        model_name = parts[0]
        api_key = parts[2] if len(parts) > 2 else ""
        if model_name != PLACEHOLDER_MODEL_NAME and api_key != PLACEHOLDER_API_KEY:
            return False
    return True


def _env_judge(temperature: float) -> EnvJudge | None:
    try:
        # Settings validation fails when the env model isn't configured at all
        executor = get_llm_executor()
    except Exception:
        return None
    if env_model_is_placeholder(executor.gpt_hosts):
        return None
    try:
        return EnvJudge(executor, temperature)
    except Exception:
        return None


def _default_model_judge() -> DefaultModelJudge | None:
    # Imported here: dependencies builds the scorers, which import this module
    from dependencies import db_session_context
    from repositories.model_provider_repository import ModelProviderRepository

    with db_session_context() as db_session:
        repo = ModelProviderRepository(db_session)
        default = repo.get_default_model_provider()
        if default.provider is None or default.model_name is None:
            return None
        try:
            client = repo.get_model_provider_client(default.provider)
        except HTTPException:
            logger.warning(
                "The default model provider %s has no usable credentials; the LLM "
                "checks can't use it",
                default.provider.value,
            )
            return None
    return DefaultModelJudge(
        client=client,
        provider=default.provider,
        model_name=default.model_name,
        org_id=_billing_org.get() or DEFAULT_ORG_ID,
    )


def resolve_judge(temperature: float = 0.0) -> LLMJudge | None:
    """The model to run an LLM check on now; None when nothing is configured.

    temperature applies to the env model only."""
    source = LLMChecksSettings().GENAI_ENGINE_LLM_CHECKS_MODEL_SOURCE
    if source == LLMChecksModelSource.ENV:
        return _env_judge(temperature)
    if source == LLMChecksModelSource.DEFAULT_MODEL:
        return _default_model_judge()
    return _env_judge(temperature) or _default_model_judge()

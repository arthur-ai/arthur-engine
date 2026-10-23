from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Protocol, Sequence
from uuid import UUID

import litellm
import openai
import tiktoken
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, convert_to_openai_messages
from litellm.types.utils import ModelResponse
from pydantic import BaseModel, ConfigDict

from monitoring.ai_activity import record_model_invocation
from schemas.audit_log_schemas import ModelInvocation
from schemas.custom_exceptions import (
    LLMContentFilterException,
    LLMMaxRequestTokensException,
    LLMTokensPerPeriodRateLimitException,
)
from schemas.scorer_schemas import RuleScore, ScorerRuleDetails
from utils import constants

if TYPE_CHECKING:
    from clients.llm.llm_client import LLMClient


NOT_CONFIGURED = "Guardrail judge is not configured."
CONFIGURATION_UNAVAILABLE = "Guardrail judge configuration is unavailable."


def zero_tokens() -> LLMTokenConsumption:
    return LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)


@dataclass(frozen=True)
class JudgeCallResult:
    text: str
    structured: BaseModel | None
    tokens: LLMTokenConsumption


class JudgeHandle(Protocol):
    def invoke(
        self,
        messages: Sequence[BaseMessage],
        response_format: type[BaseModel] | None,
        observe: Callable[[LLMTokenConsumption], None],
        started: Callable[[], None],
    ) -> JudgeCallResult: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class ProviderJudgeHandle:
    client: LLMClient = field(repr=False)
    sdk_client: openai.OpenAI | openai.AzureOpenAI | None = field(repr=False)
    org_id: UUID
    model: str
    temperature_supported: bool

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        response_format: type[BaseModel] | None,
        observe: Callable[[LLMTokenConsumption], None],
        started: Callable[[], None],
    ) -> JudgeCallResult:
        tokens = zero_tokens()

        def raw_response(response: ModelResponse) -> None:
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens.prompt_tokens = int(usage.prompt_tokens or 0)
                tokens.completion_tokens = int(usage.completion_tokens or 0)
            observe(tokens)

        kwargs: dict[str, object] = {}
        if self.temperature_supported:
            kwargs["temperature"] = 0.0
        if response_format is not None:
            kwargs["response_format"] = response_format
        prefix = f"{self.client.provider.value}/"
        routing_model = (
            self.model if self.model.startswith(prefix) else prefix + self.model
        )
        response = self.client.completion(
            model=routing_model,
            custom_llm_provider=self.client.provider.value,
            messages=convert_to_openai_messages(list(messages)),
            org_id=self.org_id,
            sdk_client=self.sdk_client,
            raw_response_observer=raw_response,
            call_started_observer=started,
            num_retries=0,
            **kwargs,
        )
        if not isinstance(response.response, ModelResponse):
            raise ValueError("Unexpected streaming judge response.")
        content = response.response.choices[0].message.content
        return JudgeCallResult(
            text=content if isinstance(content, str) else "",
            structured=response.structured_output_response,
            tokens=tokens,
        )

    def close(self) -> None:
        if self.sdk_client is not None:
            self.sdk_client.close()


class _StructuredEnvironmentResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    raw: AIMessage
    parsed: BaseModel | None = None
    parsing_error: Exception | None = None


@dataclass(frozen=True)
class EnvironmentJudgeHandle:
    model: BaseChatModel = field(repr=False)
    org_id: UUID
    enforce_quota: Callable[[UUID], None] = field(repr=False)
    record_usage: Callable[[UUID, int], None] = field(repr=False)

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        response_format: type[BaseModel] | None,
        observe: Callable[[LLMTokenConsumption], None],
        started: Callable[[], None],
    ) -> JudgeCallResult:
        self.enforce_quota(self.org_id)
        output: AIMessage | None = None
        try:
            started()
            if response_format is not None:
                response = _StructuredEnvironmentResponse.model_validate(
                    self.model.with_structured_output(
                        response_format, method="json_mode", include_raw=True
                    ).invoke(list(messages))
                )
                output = response.raw
                if response.parsing_error is not None or response.parsed is None:
                    raise ValueError("Invalid structured judge response.")
                return JudgeCallResult("", response.parsed, zero_tokens())
            message = self.model.invoke(list(messages))
            if not isinstance(message, AIMessage):
                raise ValueError("Invalid judge response.")
            output = message
            text = (
                output.content
                if isinstance(output.content, str)
                else "".join(str(part) for part in output.content)
            )
            return JudgeCallResult(text, None, zero_tokens())
        finally:
            usage = output.usage_metadata if output is not None else None
            tokens = LLMTokenConsumption(
                prompt_tokens=usage["input_tokens"] if usage else 0,
                completion_tokens=usage["output_tokens"] if usage else 0,
            )
            self.record_usage(self.org_id, tokens.total_tokens())
            observe(tokens)

    def close(self) -> None:
        client = getattr(self.model, "http_client", None)
        if client is not None:
            client.close()


class JudgeRateLimiter:
    def __init__(self, token_limit: int, period_seconds: int):
        self.token_limit = token_limit
        self.period_seconds = period_seconds
        self.calls: deque[tuple[float, int]] = deque()
        self.lock = threading.Lock()

    def check(self) -> None:
        with self.lock:
            cutoff = time.monotonic() - self.period_seconds
            while self.calls and self.calls[0][0] <= cutoff:
                self.calls.popleft()
            if sum(tokens for _, tokens in self.calls) >= self.token_limit:
                raise LLMTokensPerPeriodRateLimitException()

    def record(self, tokens: LLMTokenConsumption) -> None:
        with self.lock:
            self.calls.append((time.monotonic(), tokens.total_tokens()))


_limiters: dict[tuple[int, int], JudgeRateLimiter] = {}
_limiter_lock = threading.Lock()


def get_judge_rate_limiter(token_limit: int, period_seconds: int) -> JudgeRateLimiter:
    with _limiter_lock:
        return _limiters.setdefault(
            (token_limit, period_seconds), JudgeRateLimiter(token_limit, period_seconds)
        )


@dataclass(frozen=True)
class JudgeContext:
    org_id: UUID
    provider: ModelProvider | None = None
    model: str | None = None
    metadata_model: str | None = None
    structured_output: bool = False
    input_limit: int | None = None
    handle: JudgeHandle | None = field(default=None, repr=False)
    limiter: JudgeRateLimiter | None = field(default=None, repr=False)
    error: str | None = None

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()


class JudgeEvaluation:
    """A rule-local ledger shared only by that rule's nested call workers."""

    def __init__(self, context: JudgeContext | None):
        self.context = context
        self.tokens = zero_tokens()
        self.lock = threading.Lock()

    def complete(
        self,
        messages: Sequence[BaseMessage],
        operation: str,
        response_format: type[BaseModel] | None = None,
    ) -> JudgeCallResult:
        context = self.context
        if context is None or context.handle is None:
            raise JudgeConfigurationError(
                context.error if context and context.error else NOT_CONFIGURED
            )
        if context.input_limit is not None:
            try:
                count = litellm.token_counter(
                    model=context.metadata_model or context.model,
                    messages=convert_to_openai_messages(list(messages)),
                )
            except Exception:
                encoder = tiktoken.get_encoding("cl100k_base")
                count = (
                    sum(
                        len(encoder.encode(str(message.content))) + 4
                        for message in messages
                    )
                    + 3
                )
            if count > context.input_limit:
                raise LLMMaxRequestTokensException(constants.ERROR_TOKEN_LIMIT_EXCEEDED)
        if context.limiter is not None:
            context.limiter.check()
        observed = zero_tokens()
        started = time.perf_counter()
        success = False
        call_started = False
        error_type: str | None = None

        def observe(tokens: LLMTokenConsumption) -> None:
            observed.prompt_tokens = tokens.prompt_tokens
            observed.completion_tokens = tokens.completion_tokens

        def started_call() -> None:
            nonlocal call_started
            call_started = True

        try:
            result = context.handle.invoke(
                messages, response_format, observe, started_call
            )
            success = True
            return JudgeCallResult(result.text, result.structured, observed)
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            with self.lock:
                self.tokens.add(observed)
            if context.limiter is not None and call_started:
                context.limiter.record(observed)
            try:
                if call_started:
                    record_model_invocation(
                        ModelInvocation(
                            model_name=context.model or "unknown",
                            provider=(
                                context.provider.value
                                if context.provider
                                else "unknown"
                            ),
                            model_type="llm",
                            operation=operation,
                            prompt_tokens=observed.prompt_tokens,
                            completion_tokens=observed.completion_tokens,
                            total_tokens=observed.total_tokens(),
                            latency_ms=int((time.perf_counter() - started) * 1000),
                            success=success,
                            error_type=error_type,
                        ),
                    )
            except Exception:
                pass

    def unavailable(self, error: Exception) -> RuleScore:
        message = constants.ERROR_DEFAULT_RULE_ENGINE
        if isinstance(error, JudgeConfigurationError):
            message = str(error)
        elif isinstance(error, LLMContentFilterException):
            message = str(error)
        elif isinstance(error, LLMMaxRequestTokensException):
            message = constants.ERROR_TOKEN_LIMIT_EXCEEDED
        elif isinstance(error, LLMTokensPerPeriodRateLimitException):
            message = constants.ERROR_GENAI_ENGINE_RATE_LIMIT_EXCEEDED
        elif isinstance(error, HTTPException):
            if error.status_code == 429:
                if (
                    isinstance(error.detail, dict)
                    and error.detail.get("error_code") == "TOKEN_LIMIT_EXCEEDED"
                ):
                    message = str(error.detail["message"])
                else:
                    message = "GenAI Engine was unable to evaluate due to an upstream API rate limit"
        elif isinstance(error, openai.RateLimitError):
            message = (
                "GenAI Engine was unable to evaluate due to an upstream API rate limit"
            )
        elif isinstance(error, openai.APIConnectionError):
            message = "GenAI Engine was unable to evaluate due to an upstream API connection error"
        elif isinstance(error, openai.APIError) and error.code == "content_filter":
            message = str(LLMContentFilterException())
        elif (
            isinstance(error, openai.APIError)
            and error.code == "context_length_exceeded"
        ):
            message = constants.ERROR_TOKEN_LIMIT_EXCEEDED
        return RuleScore(
            result=RuleResultEnum.UNAVAILABLE,
            details=ScorerRuleDetails(message=message),
            prompt_tokens=self.tokens.prompt_tokens,
            completion_tokens=self.tokens.completion_tokens,
        )


class JudgeConfigurationError(Exception):
    pass

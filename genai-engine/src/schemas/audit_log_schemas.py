from typing import Literal, Optional

from arthur_common.models.audit_log_schemas import AuditLog
from pydantic import BaseModel, Field


class RouteInfo(BaseModel):
    resource_name: str
    collection_field: str | None
    id_field: str


class ModelInvocation(BaseModel):
    """A single AI model invocation performed by the engine while serving a request.

    Metadata only — never carries prompt/response content, consistent with the
    audit log's no-payload design.
    """

    model_name: Optional[str] = Field(
        default=None,
        description="The model that was invoked (e.g. an LLM deployment name or a "
        "local classifier model id). None when the engine could not resolve it.",
    )
    provider: str = Field(
        description="Where the model ran: 'azure', 'openai', 'proxy', or 'local'.",
    )
    model_type: Literal["llm", "ml_classifier"] = Field(
        description="'llm' for hosted LLM judge calls, 'ml_classifier' for on-box models.",
    )
    operation: str = Field(
        description="The check/operation that issued the call (e.g. 'hallucination', 'toxicity').",
    )
    prompt_tokens: Optional[int] = Field(
        default=None,
        description="Prompt tokens consumed. None for local models that do not tokenize via an LLM.",
    )
    completion_tokens: Optional[int] = Field(
        default=None,
        description="Completion tokens produced. None for local models.",
    )
    total_tokens: Optional[int] = Field(
        default=None,
        description="Total tokens consumed. None for local models.",
    )
    latency_ms: int = Field(
        description="Wall-clock duration of the invocation in milliseconds.",
    )
    success: bool = Field(
        description="Whether the invocation completed without raising.",
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Exception class name when the invocation failed, else None.",
    )


class ExtendedAuditLog(AuditLog):
    """Audit event extended with the model invocations made while serving the request.

    Emitted in place of the base ``AuditLog`` (V1) only when
    ``AUDIT_LOG_INCLUDE_AI_ACTIVITY`` is enabled, so existing V1 log consumers see
    no change unless the feature is turned on.
    """

    # Intentionally bumps the event version literal for the extended event; the
    # narrowing override is not Liskov-compatible with the base V1 literal, which
    # is the whole point of a distinct event type.
    audit_log_meta_version: Literal["ArthurAuditLogEventV2"] = "ArthurAuditLogEventV2"  # type: ignore[assignment]
    model_invocations: list[ModelInvocation] = Field(
        default_factory=list,
        description="AI model invocations performed while serving this request.",
    )

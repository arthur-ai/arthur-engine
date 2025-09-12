from datetime import datetime
from typing import Optional

from openinference.semconv.trace import OpenInferenceSpanKindValues
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from schemas.enums import (
    DocumentStorageEnvironment,
    ToolClassEnum,
)


class DocumentStorageConfigurationUpdateRequest(BaseModel):
    environment: DocumentStorageEnvironment
    connection_string: Optional[str] = None
    container_name: Optional[str] = None
    bucket_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None

    @model_validator(mode="before")
    def check_azure_or_aws_complete_config(cls, values):
        if values.get("environment") == "azure":
            if (values.get("connection_string") is None) or (
                values.get("container_name") is None
            ):
                raise ValueError(
                    "Both connection string and container name must be supplied for Azure document configuration",
                )
        elif values.get("environment") == "aws":
            if values.get("bucket_name") is None:
                raise ValueError(
                    "Bucket name must be supplied for AWS document configuration",
                )
            if values.get("assumable_role_arn") is None:
                raise ValueError(
                    "Role ARN must be supplied for AWS document configuration",
                )
        return values


class ApplicationConfigurationUpdateRequest(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[
        DocumentStorageConfigurationUpdateRequest
    ] = None
    max_llm_rules_per_task_count: Optional[int] = None


class TraceQueryRequest(BaseModel):
    """Request schema for querying traces with comprehensive filtering."""

    # Required
    task_ids: list[str] = Field(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    )

    # Common optional filters
    trace_ids: Optional[list[str]] = Field(
        None,
        description="Trace IDs to filter on. Optional.",
    )
    start_time: Optional[datetime] = Field(
        None,
        description="Inclusive start date in ISO8601 string format.",
    )
    end_time: Optional[datetime] = Field(
        None,
        description="Exclusive end date in ISO8601 string format.",
    )

    # New trace-level filters
    tool_name: Optional[str] = Field(
        None,
        description="Return only results with this tool name.",
    )
    span_types: Optional[list[str]] = Field(
        None,
        description="Span types to filter on. Optional.",
    )

    # Query relevance filters
    query_relevance_eq: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Equal to this value.",
    )
    query_relevance_gt: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Greater than this value.",
    )
    query_relevance_gte: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Greater than or equal to this value.",
    )
    query_relevance_lt: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Less than this value.",
    )
    query_relevance_lte: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Less than or equal to this value.",
    )

    # Response relevance filters
    response_relevance_eq: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Equal to this value.",
    )
    response_relevance_gt: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Greater than this value.",
    )
    response_relevance_gte: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Greater than or equal to this value.",
    )
    response_relevance_lt: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Less than this value.",
    )
    response_relevance_lte: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Less than or equal to this value.",
    )

    # Tool classification filters
    tool_selection: Optional[ToolClassEnum] = Field(
        None,
        description="Tool selection evaluation result.",
    )
    tool_usage: Optional[ToolClassEnum] = Field(
        None,
        description="Tool usage evaluation result.",
    )

    # Trace duration filters
    trace_duration_eq: Optional[float] = Field(
        None,
        ge=0,
        description="Duration exactly equal to this value (seconds).",
    )
    trace_duration_gt: Optional[float] = Field(
        None,
        ge=0,
        description="Duration greater than this value (seconds).",
    )
    trace_duration_gte: Optional[float] = Field(
        None,
        ge=0,
        description="Duration greater than or equal to this value (seconds).",
    )
    trace_duration_lt: Optional[float] = Field(
        None,
        ge=0,
        description="Duration less than this value (seconds).",
    )
    trace_duration_lte: Optional[float] = Field(
        None,
        ge=0,
        description="Duration less than or equal to this value (seconds).",
    )

    @field_validator(
        "query_relevance_eq",
        "query_relevance_gt",
        "query_relevance_gte",
        "query_relevance_lt",
        "query_relevance_lte",
        "response_relevance_eq",
        "response_relevance_gt",
        "response_relevance_gte",
        "response_relevance_lt",
        "response_relevance_lte",
        mode="before",
    )
    @classmethod
    def validate_relevance_scores(
        cls,
        value: Optional[float],
        info: ValidationInfo,
    ) -> Optional[float]:
        """Validate that relevance scores are between 0 and 1 (inclusive)."""
        if value is not None:
            if not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"{info.field_name} value must be between 0 and 1 (inclusive)",
                )
        return value

    @field_validator(
        "trace_duration_eq",
        "trace_duration_gt",
        "trace_duration_gte",
        "trace_duration_lt",
        "trace_duration_lte",
        mode="before",
    )
    @classmethod
    def validate_trace_duration(
        cls,
        value: Optional[float],
        info: ValidationInfo,
    ) -> Optional[float]:
        """Validate that trace duration values are positive."""
        if value is not None:
            if value <= 0:
                raise ValueError(
                    f"{info.field_name} value must be positive (greater than 0)",
                )
        return value

    @field_validator("tool_selection", "tool_usage", mode="before")
    @classmethod
    def validate_tool_classification(cls, value) -> Optional[ToolClassEnum]:
        """Validate tool classification enum values."""
        if value is not None:
            # Handle both integer and enum inputs
            if isinstance(value, int):
                if value not in [0, 1, 2]:
                    raise ValueError(
                        "Tool classification must be 0 (INCORRECT), "
                        "1 (CORRECT), or 2 (NA)",
                    )
                return ToolClassEnum(value)
            elif isinstance(value, ToolClassEnum):
                return value
            else:
                raise ValueError(
                    "Tool classification must be an integer (0, 1, 2) or ToolClassEnum instance",
                )
        return value

    @field_validator("span_types")
    @classmethod
    def validate_span_types(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Validate that all span_types are valid OpenInference span kinds."""
        if not value:
            return value

        # Get all valid span kind values
        valid_span_kinds = [kind.value for kind in OpenInferenceSpanKindValues]
        invalid_types = [st for st in value if st not in valid_span_kinds]

        if invalid_types:
            raise ValueError(
                f"Invalid span_types received: {invalid_types}. "
                f"Valid values: {', '.join(sorted(valid_span_kinds))}",
            )
        return value

    @model_validator(mode="after")
    def validate_filter_combinations(self):
        """Validate that filter combinations are logically valid."""
        # Check mutually exclusive filters for each metric type
        for prefix in ["query_relevance", "response_relevance", "trace_duration"]:
            eq_field = f"{prefix}_eq"
            comparison_fields = [f"{prefix}_{op}" for op in ["gt", "gte", "lt", "lte"]]

            if getattr(self, eq_field) and any(
                getattr(self, field) for field in comparison_fields
            ):
                raise ValueError(
                    f"{eq_field} cannot be combined with other {prefix} comparison operators",
                )

            # Check for incompatible operator combinations
            if getattr(self, f"{prefix}_gt") and getattr(self, f"{prefix}_gte"):
                raise ValueError(f"Cannot combine {prefix}_gt with {prefix}_gte")
            if getattr(self, f"{prefix}_lt") and getattr(self, f"{prefix}_lte"):
                raise ValueError(f"Cannot combine {prefix}_lt with {prefix}_lte")

        return self

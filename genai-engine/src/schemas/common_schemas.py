from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from arthur_common.models.enums import (
    UserPermissionAction,
    UserPermissionResource,
)
from pydantic import BaseModel, Field, model_validator

from schemas.enums import ContinuousEvalTraceFilterOperator


class LLMTokenConsumption(BaseModel):
    prompt_tokens: int
    completion_tokens: int

    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, token_consumption: LLMTokenConsumption) -> "LLMTokenConsumption":
        self.prompt_tokens += token_consumption.prompt_tokens
        self.completion_tokens += token_consumption.completion_tokens
        return self


class AuthUserRole(BaseModel):
    id: str | None = None
    name: str
    description: str
    composite: bool


class UserPermission(BaseModel):
    action: UserPermissionAction
    resource: UserPermissionResource

    def __hash__(self) -> int:
        return hash((self.action, self.resource))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UserPermission) and self.__hash__() == other.__hash__()


class NewDatasetVersionRowColumnItemRequest(BaseModel):
    """Represents a single column-value pair in a dataset row."""

    column_name: str = Field(description="Name of column.")
    column_value: str = Field(description="Value of column for the row.")


class NewDatasetVersionRowRequest(BaseModel):
    """Represents a row to be added to a dataset version."""

    id: Optional[str] = Field(
        default=None,
        description="Optional ID for the row (used for synthetic data generation).",
    )
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the new dataset row.",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="ID of the trace this row was extracted from, if the row originated from a trace.",
    )


class NewDatasetVersionUpdateRowRequest(BaseModel):
    """Represents a row to be updated in a dataset version."""

    id: UUID = Field(description="UUID of row to be updated.")
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the updated row.",
    )


class BasePaginationResponse(BaseModel):
    """Mixin for paginated list responses."""

    page: int = Field(description="Current page number (0-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of records")


class ContinuousEvalTraceFilterCondition(BaseModel):
    """One condition a trace must meet for a continuous eval to judge it.

    Checks the spans in the trace (only spans named `span_name`, when set):
    `equals`, `contains` and `exists` hold when any of them has a value at
    `attribute_path` that meets the operator; `not_equals` holds when none of them
    has that value, so a trace without the attribute counts as not equal.
    """

    span_name: Optional[str] = Field(
        default=None,
        description="Only check spans with this name. Null checks every span in the trace.",
    )
    attribute_path: str = Field(
        min_length=1,
        description=(
            "Dot-separated path into the span, the same paths transforms use, "
            "e.g. 'attributes.metadata.plan' or 'attributes.llm.model_name'."
        ),
    )
    operator: ContinuousEvalTraceFilterOperator = Field(
        description=(
            "How to compare the value at attribute_path. 'not_equals' holds when no "
            "checked span has the value, including when none has the attribute."
        ),
    )
    value: Optional[str] = Field(
        default=None,
        description="Value to compare against. Required unless operator is 'exists'.",
    )

    @model_validator(mode="after")
    def validate_value(self) -> "ContinuousEvalTraceFilterCondition":
        if self.operator == ContinuousEvalTraceFilterOperator.EXISTS:
            if self.value is not None:
                raise ValueError("value must be null when operator is 'exists'")
        elif self.value is None:
            raise ValueError(
                f"value is required when operator is '{self.operator.value}'"
            )
        return self

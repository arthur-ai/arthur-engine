from __future__ import annotations

from typing import List
from uuid import UUID

from arthur_common.models.enums import (
    UserPermissionAction,
    UserPermissionResource,
)
from pydantic import BaseModel, Field


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

    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the new dataset row.",
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

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from arthur_common.models.enums import (
    UserPermissionAction,
    UserPermissionResource,
)
from pydantic import BaseModel, Field


class LLMTokenConsumption(BaseModel):
    prompt_tokens: int
    completion_tokens: int

    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    def add(self, token_consumption: LLMTokenConsumption):
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

    def __hash__(self):
        return hash((self.action, self.resource))

    def __eq__(self, other):
        return isinstance(other, UserPermission) and self.__hash__() == other.__hash__()


class JsonPropertySchema(BaseModel):
    type: str = Field(
        default="string",
        description="The argument's type (e.g. string, boolean, etc.)",
    )
    description: Optional[str] = Field(
        default=None,
        description="A description of the argument",
    )
    enum: Optional[List[str]] = Field(
        default=None,
        description="An enum for the argument (e.g. ['celsius', 'fahrenheit'])",
    )
    items: Optional[Any] = Field(
        default=None,
        description="For array types, describes the items",
    )


class JsonSchema(BaseModel):
    type: str = Field(default="object")
    properties: Dict[str, JsonPropertySchema] = Field(
        ...,
        description="The name of the property and the property schema (e.g. {'topic': {'type': 'string', 'description': 'the topic to generate a joke for'})",
    )
    required: List[str] = Field(
        default_factory=list,
        description="The required properties of the function",
    )
    additionalProperties: Optional[bool] = Field(
        default=None,
        description="Whether the function definition should allow additional properties",
    )


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

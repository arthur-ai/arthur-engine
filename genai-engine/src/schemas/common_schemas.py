from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    name: str = Field(..., description="The name of the argument")
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

    def to_dict(self) -> Dict[str, Any]:
        result = {self.name: {"type": self.type}}

        if self.description:
            result[self.name]["description"] = self.description

        if self.enum:
            result[self.name]["enum"] = self.enum

        if self.items:
            result[self.name]["items"] = self.items

        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "JsonPropertySchema":
        return cls(
            name=name,
            type=data["type"],
            description=data.get("description"),
            enum=data.get("enum"),
            items=data.get("items"),
        )


class JsonSchema(BaseModel):
    type: str = Field(default="object")
    properties: List[JsonPropertySchema] = Field(
        ...,
        description="The properties of the function",
    )
    required: List[str] = Field(
        default_factory=list,
        description="The required properties of the function",
    )
    additional_properties: Optional[bool] = Field(
        default=None,
        description="Whether the function definition should allow additional properties",
    )

    def to_dict(self) -> Dict[str, Any]:
        properties_dict = {}
        for prop in self.properties:
            properties_dict.update(prop.to_dict())

        result = {
            "type": self.type,
            "properties": properties_dict,
        }

        if self.required:
            result["required"] = self.required

        if self.additional_properties is not None:
            result["additionalProperties"] = self.additional_properties

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JsonSchema":
        properties = []
        for prop_name, prop_data in data["properties"].items():
            properties.append(JsonPropertySchema.from_dict(prop_name, prop_data))

        return cls(
            type=data["type"],
            properties=properties,
            required=data.get("required", []),
            additional_properties=data.get("additionalProperties"),
        )

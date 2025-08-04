from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas.enums import (
    PaginationSortMethod,
    PIIEntityTypes,
    UserPermissionAction,
    UserPermissionResource,
)
from utils.constants import (
    DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD,
    DEFAULT_TOXICITY_RULE_THRESHOLD,
)


class PaginationParameters(BaseModel):
    sort: Optional[PaginationSortMethod] = PaginationSortMethod.DESCENDING
    page_size: int = 10
    page: int = 0

    def calculate_total_pages(self, total_items_count: int) -> int:
        return total_items_count // self.page_size + 1


class KeywordsConfig(BaseModel):
    keywords: List[str] = Field(description="List of Keywords")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"keywords": ["Blocked_Keyword_1", "Blocked_Keyword_2"]},
        },
    )


class RegexConfig(BaseModel):
    regex_patterns: List[str] = Field(
        description="List of Regex patterns to be used for validation. Be sure to encode requests in JSON and account for escape characters.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "regex_patterns": ["\\d{3}-\\d{2}-\\d{4}", "\\d{5}-\\d{6}-\\d{7}"],
            },
        },
        extra="forbid",
    )


class ToxicityConfig(BaseModel):
    threshold: float = Field(
        default=DEFAULT_TOXICITY_RULE_THRESHOLD,
        description=f"Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: {DEFAULT_TOXICITY_RULE_THRESHOLD}",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"threshold": DEFAULT_TOXICITY_RULE_THRESHOLD}},
    )

    @field_validator("threshold")
    def validate_toxicity_threshold(cls, v):
        if v is None:
            return DEFAULT_TOXICITY_RULE_THRESHOLD
        if (v < 0) | (v > 1):
            raise ValueError(f'"threshold" must be between 0 and 1')
        return v


class PIIConfig(BaseModel):
    disabled_pii_entities: Optional[list[str]] = Field(
        description=f"Optional. List of PII entities to disable. Valid values are: {PIIEntityTypes.to_string()}",
        default=None,
    )

    confidence_threshold: Optional[float] = Field(
        description=f"Optional. Float (0, 1) indicating the level of tolerable PII to consider the rule passed or failed. Min: 0 (less confident) Max: 1 (very confident). Default: {DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD}",
        default=DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD,
        json_schema_extra={"deprecated": True},
    )

    allow_list: Optional[list[str]] = Field(
        description="Optional. List of strings to pass PII validation.",
        default=None,
    )

    @field_validator("disabled_pii_entities")
    def validate_pii_entities(cls, v):
        if v:
            entities_passed = set(v)
            entities_supported = set(PIIEntityTypes.values())
            invalid_entities = entities_passed - entities_supported
            if invalid_entities:
                raise ValueError(
                    f"The following values are not valid PII entities: {invalid_entities}",
                )

            # Fail the case where they are trying to disable all PII entity types
            if (not invalid_entities) & (
                len(entities_passed) == len(entities_supported)
            ):
                raise ValueError(
                    f"Cannot disable all supported PII entities on PIIDataRule",
                )
            return v
        else:
            return v

    @field_validator("confidence_threshold")
    def validate_confidence_threshold(cls, v):
        if v:
            if (v < 0) | (v > 1):
                raise ValueError(f'"confidence_threshold" must be between 0 and 1')
            return v
        else:
            return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "disabled_pii_entities": ["PERSON", "URL"],
                "confidence_threshold": "0.5",
                "allow_list": ["arthur.ai", "Arthur"],
            },
        },
        extra="forbid",
    )


class ExampleConfig(BaseModel):
    example: str = Field(description="Custom example for the sensitive data")
    result: bool = Field(
        description="Boolean value representing if the example passes or fails the the sensitive "
        "data rule ",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"example": "John has O negative blood group", "result": True},
        },
    )


class ExamplesConfig(BaseModel):
    examples: List[ExampleConfig] = Field(
        description="List of all the examples for Sensitive Data Rule",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "examples": [
                    {"example": "John has O negative blood group", "result": True},
                    {
                        "example": "Most og the people have A positive blood group",
                        "result": False,
                    },
                ],
                "hint": "specific individual's blood type",
            },
        },
    )
    hint: Optional[str] = Field(
        description="Optional. hint added to describe what Sensitive Data Rule should be checking for",
        default=None,
    )

    def to_dict(self):
        d = self.__dict__
        d["examples"] = [ex.__dict__ for ex in self.examples]
        d["hint"] = self.hint
        return d


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

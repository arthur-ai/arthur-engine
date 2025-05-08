from enum import Enum
from typing import Any, Dict, List, Optional, Self, Type, Union

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_TOXICITY_RULE_THRESHOLD = 0.5
DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD = 0


class RuleType(str, Enum):
    KEYWORD = "KeywordRule"
    MODEL_HALLUCINATION = "ModelHallucinationRule"
    MODEL_HALLUCINATION_V2 = "ModelHallucinationRuleV2"
    MODEL_HALLUCINATION_V3 = "ModelHallucinationRuleV3"
    MODEL_SENSITIVE_DATA = "ModelSensitiveDataRule"
    PII_DATA = "PIIDataRule"
    PROMPT_INJECTION = "PromptInjectionRule"
    REGEX = "RegexRule"
    TOXICITY = "ToxicityRule"

    def __str__(self) -> str:
        return self.value


class RuleScope(str, Enum):
    DEFAULT = "default"
    TASK = "task"


class BaseEnum(str, Enum):
    @classmethod
    def values(cls) -> list[Any]:
        values: list[str] = [e for e in cls]
        return values

    def __str__(self) -> Any:
        return self.value


# Note: These string values are not arbitrary and map to Presidio entity types: https://microsoft.github.io/presidio/supported_entities/
class PIIEntityTypes(BaseEnum):
    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    URL = "URL"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"

    @classmethod
    def to_string(cls) -> str:
        return ",".join(member.value for member in cls)


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
    def validate_toxicity_threshold(cls, v: float) -> float:
        if v and ((v < 0) | (v > 1)):
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
    def validate_pii_entities(cls, v: Optional[List[str]]) -> Optional[List[str]]:
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
    def validate_confidence_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v and ((v < 0) | (v > 1)):
            raise ValueError(f'"confidence_threshold" must be between 0 and 1')
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


NEGATIVE_BLOOD_EXAMPLE = "John has O negative blood group"


class ExampleConfig(BaseModel):
    example: str = Field(description="Custom example for the sensitive data")
    result: bool = Field(
        description="Boolean value representing if the example passes or fails the the sensitive "
        "data rule ",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"example": NEGATIVE_BLOOD_EXAMPLE, "result": True},
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
                    {"example": NEGATIVE_BLOOD_EXAMPLE, "result": True},
                    {
                        "example": "Most of the people have A positive blood group",
                        "result": False,
                    },
                ],
                "hint": "specific individual's blood type",
            },
        },
    )
    hint: Optional[str] = Field(
        description="Optional. Hint added to describe what Sensitive Data Rule should be checking for",
        default=None,
    )

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__
        d["examples"] = [ex.__dict__ for ex in self.examples]
        d["hint"] = self.hint
        return d


class RuleResponse(BaseModel):
    id: str = Field(description="ID of the Rule")
    name: str = Field(description="Name of the Rule")
    type: RuleType = Field(description="Type of Rule")
    apply_to_prompt: bool = Field(description="Rule applies to prompt")
    apply_to_response: bool = Field(description="Rule applies to response")
    enabled: Optional[bool] = Field(
        description="Rule is enabled for the task",
        default=None,
    )
    scope: RuleScope = Field(
        description="Scope of the rule. The rule can be set at default level or task level.",
    )
    # UNIX millis format
    created_at: int = Field(
        description="Time the rule was created in unix milliseconds",
    )
    updated_at: int = Field(
        description="Time the rule was updated in unix milliseconds",
    )
    # added a title to this to differentiate it in the generated client from the
    # config field on the NewRuleRequest object
    config: Optional[
        Union[KeywordsConfig, RegexConfig, ExamplesConfig, ToxicityConfig, PIIConfig]
    ] = Field(
        description="Config of the rule",
        default=None,
        title="Rule Response Config",
    )


class TaskResponse(BaseModel):
    id: str = Field(description=" ID of the task")
    name: str = Field(description="Name of the task")
    created_at: int = Field(
        description="Time the task was created in unix milliseconds",
    )
    updated_at: int = Field(
        description="Time the task was created in unix milliseconds",
    )
    rules: List[RuleResponse] = Field(description="List of all the rules for the task.")


class UpdateRuleRequest(BaseModel):
    enabled: bool = Field(description="Boolean value to enable or disable the rule. ")


HALLUCINATION_RULE_NAME = "Hallucination Rule"


class NewRuleRequest(BaseModel):
    name: str = Field(description="Name of the rule", examples=["SSN Regex Rule"])
    type: str = Field(
        description="Type of the rule. It can only be one of KeywordRule, RegexRule, "
        "ModelSensitiveDataRule, ModelHallucinationRule, ModelHallucinationRuleV2, PromptInjectionRule, PIIDataRule",
        examples=["RegexRule"],
    )
    apply_to_prompt: bool = Field(
        description="Boolean value to enable or disable the rule for llm prompt",
        examples=[True],
    )
    apply_to_response: bool = Field(
        description="Boolean value to enable or disable the rule for llm response",
        examples=[False],
    )
    config: Optional[
        Union[RegexConfig, KeywordsConfig, ToxicityConfig, PIIConfig, ExamplesConfig]
    ] = Field(description="Config for the rule", default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example1": {
                "summary": "Sensitive Data Example",
                "description": "Sensitive Data Example with its required configuration",
                "value": {
                    "name": "Sensitive Data Rule",
                    "type": "ModelSensitiveDataRule",
                    "apply_to_prompt": True,
                    "apply_to_response": False,
                    "config": {
                        "examples": [
                            {
                                "example": NEGATIVE_BLOOD_EXAMPLE,
                                "result": True,
                            },
                            {
                                "example": "Most of the people have A positive blood group",
                                "result": False,
                            },
                        ],
                        "hint": "specific individual's blood types",
                    },
                },
            },
            "example2": {
                "summary": "Regex Example",
                "description": "Regex Example with its required configuration. Be sure to properly encode requests "
                "using JSON libraries. For example, the regex provided encodes to a different string "
                "when encoded to account for escape characters.",
                "value": {
                    "name": "SSN Regex Rule",
                    "type": "RegexRule",
                    "apply_to_prompt": True,
                    "apply_to_response": True,
                    "config": {
                        "regex_patterns": [
                            "\\d{3}-\\d{2}-\\d{4}",
                            "\\d{5}-\\d{6}-\\d{7}",
                        ],
                    },
                },
            },
            "example3": {
                "summary": "Keywords Rule Example",
                "description": "Keywords Rule Example with its required configuration",
                "value": {
                    "name": "Blocked Keywords Rule",
                    "type": "KeywordRule",
                    "apply_to_prompt": True,
                    "apply_to_response": True,
                    "config": {"keywords": ["Blocked_Keyword_1", "Blocked_Keyword_2"]},
                },
            },
            "example4": {
                "summary": "Prompt Injection Rule Example",
                "description": "Prompt Injection Rule Example, no configuration required",
                "value": {
                    "name": "Prompt Injection Rule",
                    "type": "PromptInjectionRule",
                    "apply_to_prompt": True,
                    "apply_to_response": False,
                },
            },
            "example5": {
                "summary": "Hallucination Rule V1 Example (Deprecated)",
                "description": "Hallucination Rule Example, no configuration required (This rule is deprecated. Use "
                "ModelHallucinationRuleV2 instead.)",
                "value": {
                    "name": HALLUCINATION_RULE_NAME,
                    "type": "ModelHallucinationRule",
                    "apply_to_prompt": False,
                    "apply_to_response": True,
                },
            },
            "example6": {
                "summary": "Hallucination Rule V2 Example",
                "description": "Hallucination Rule Example, no configuration required",
                "value": {
                    "name": HALLUCINATION_RULE_NAME,
                    "type": "ModelHallucinationRuleV2",
                    "apply_to_prompt": False,
                    "apply_to_response": True,
                },
            },
            "example7": {
                "summary": "Hallucination Rule V3 Example (Beta)",
                "description": "Hallucination Rule Example, no configuration required. This rule is in beta and must "
                "be enabled by the system administrator.",
                "value": {
                    "name": HALLUCINATION_RULE_NAME,
                    "type": "ModelHallucinationRuleV3",
                    "apply_to_prompt": False,
                    "apply_to_response": True,
                },
            },
            "example8": {
                "summary": "PII Rule Example",
                "description": f'PII Rule Example, no configuration required. "disabled_pii_entities", '
                f'"confidence_threshold", and "allow_list" accepted. Valid value for '
                f'"confidence_threshold" is 0.0-1.0. Valid values for "disabled_pii_entities" '
                f"are {PIIEntityTypes.to_string()}",
                "value": {
                    "name": "PII Rule",
                    "type": "PIIDataRule",
                    "apply_to_prompt": True,
                    "apply_to_response": True,
                    "config": {
                        "disabled_pii_entities": [
                            "EMAIL_ADDRESS",
                            "PHONE_NUMBER",
                        ],
                        "confidence_threshold": "0.5",
                        "allow_list": ["arthur.ai", "Arthur"],
                    },
                },
            },
            "example9": {
                "summary": "Toxicity Rule Example",
                "description": "Toxicity Rule Example, no configuration required. Threshold accepted",
                "value": {
                    "name": "Toxicity Rule",
                    "type": "ToxicityRule",
                    "apply_to_prompt": True,
                    "apply_to_response": True,
                    "config": {"threshold": 0.5},
                },
            },
        },
    )

    @model_validator(mode="before")
    def set_config_type(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        config_type_to_class: Dict[str, Type[BaseModel]] = {
            RuleType.REGEX: RegexConfig,
            RuleType.KEYWORD: KeywordsConfig,
            RuleType.TOXICITY: ToxicityConfig,
            RuleType.PII_DATA: PIIConfig,
            RuleType.MODEL_SENSITIVE_DATA: ExamplesConfig,
        }

        config_type = values["type"]
        config_class = config_type_to_class.get(config_type)

        if config_class is not None:
            config_values = values.get("config")
            if config_values is None:
                if config_type in [RuleType.REGEX, RuleType.KEYWORD]:
                    raise HTTPException(
                        status_code=400,
                        detail="This rule must be created with a config parameter",
                    )
                config_values = {}
            if isinstance(config_values, BaseModel):
                config_values = config_values.model_dump()
            values["config"] = config_class(**config_values)
        return values

    @model_validator(mode="after")
    def check_prompt_or_response(self) -> Self:
        if (self.type == RuleType.MODEL_SENSITIVE_DATA) and (
            self.apply_to_response is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelSensitiveDataRule can only be enabled for prompt. Please set the 'apply_to_response' "
                "field to false.",
            )
        if (self.type == RuleType.PROMPT_INJECTION) and (
            self.apply_to_response is True
        ):
            raise HTTPException(
                status_code=400,
                detail="PromptInjectionRule can only be enabled for prompt. Please set the 'apply_to_response' field "
                "to false.",
            )
        if (self.type == RuleType.MODEL_HALLUCINATION) and (
            self.apply_to_prompt is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelHallucinationRule can only be enabled for response. Please set the 'apply_to_prompt' "
                "field to false.",
            )
        if (self.type == RuleType.MODEL_HALLUCINATION_V2) and (
            self.apply_to_prompt is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelHallucinationRuleV2 can only be enabled for response. Please set the 'apply_to_prompt' "
                "field to false.",
            )
        if (self.type == RuleType.MODEL_HALLUCINATION_V3) and (
            self.apply_to_prompt is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelHallucinationRuleV3 can only be enabled for response. Please set the "
                "'apply_to_prompt' field to false.",
            )
        if (self.apply_to_prompt is False) and (self.apply_to_response is False):
            raise HTTPException(
                status_code=400,
                detail="Rule must be either applied to the prompt or to the response.",
            )

        return self

    @model_validator(mode="after")
    def check_examples_non_null(self) -> Self:
        if self.type == RuleType.MODEL_SENSITIVE_DATA:
            config = self.config
            if (
                config is not None
                and isinstance(config, ExamplesConfig)
                and (config.examples is None or len(config.examples) == 0)
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Examples must be provided to onboard a ModelSensitiveDataRule",
                )
        return self

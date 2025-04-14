from typing import Dict, Optional, Type

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from schemas.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from schemas.enums import (
    APIKeysRolesEnum,
    DocumentStorageEnvironment,
    InferenceFeedbackTarget,
    PIIEntityTypes,
    RuleScope,
    RuleType,
)
from utils import constants


class UpdateRuleRequest(BaseModel):
    enabled: bool = Field(description="Boolean value to enable or disable the rule. ")


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
    config: (
        KeywordsConfig
        | RegexConfig
        | ExamplesConfig
        | ToxicityConfig
        | PIIConfig
        | None
    ) = Field(description="Config of the rule", default=None)

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
                                "example": "John has O negative blood group",
                                "result": True,
                            },
                            {
                                "example": "Most og the people have A positive blood group",
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
                "summary": "Hallucination Rule V2 Example",
                "description": "Hallucination Rule Example, no configuration required",
                "value": {
                    "name": "Hallucination Rule",
                    "type": "ModelHallucinationRuleV2",
                    "apply_to_prompt": False,
                    "apply_to_response": True,
                },
            },
            "example6": {
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
            "example7": {
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
    def set_config_type(cls, values):
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
                        headers={"full_stacktrace": "false"},
                    )
                config_values = {}
            if isinstance(config_values, BaseModel):
                config_values = config_values.model_dump()
            values["config"] = config_class(**config_values)
        return values

    @model_validator(mode="after")
    def check_prompt_or_response(cls, values: "NewRuleRequest"):
        if (values.type == RuleType.MODEL_SENSITIVE_DATA) and (
            values.apply_to_response is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelSensitiveDataRule can only be enabled for prompt. Please set the 'apply_to_response' "
                "field to false.",
                headers={"full_stacktrace": "false"},
            )
        if (values.type == RuleType.PROMPT_INJECTION) and (
            values.apply_to_response is True
        ):
            raise HTTPException(
                status_code=400,
                detail="PromptInjectionRule can only be enabled for prompt. Please set the 'apply_to_response' field "
                "to false.",
                headers={"full_stacktrace": "false"},
            )
        if (values.type == RuleType.MODEL_HALLUCINATION_V2) and (
            values.apply_to_prompt is True
        ):
            raise HTTPException(
                status_code=400,
                detail="ModelHallucinationRuleV2 can only be enabled for response. Please set the 'apply_to_prompt' "
                "field to false.",
                headers={"full_stacktrace": "false"},
            )
        if (values.apply_to_prompt is False) and (values.apply_to_response is False):
            raise HTTPException(
                status_code=400,
                detail="Rule must be either applied to the prompt or to the response.",
                headers={"full_stacktrace": "false"},
            )

        return values

    @model_validator(mode="after")
    def check_examples_non_null(cls, values: "NewRuleRequest"):
        if values.type == RuleType.MODEL_SENSITIVE_DATA:
            config = values.config
            if config is not None and (
                config.examples is None or len(config.examples) == 0
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Examples must be provided to onboard a ModelSensitiveDataRule",
                )
        return values


class SearchTasksRequest(BaseModel):
    task_ids: Optional[list[str]] = Field(
        description="List of tasks to query for.",
        default=None,
    )
    task_name: Optional[str] = Field(
        description="Task name substring search string.",
        default=None,
    )


class SearchRulesRequest(BaseModel):
    rule_ids: Optional[list[str]] = Field(
        description="List of rule IDs to search for.",
        default=None,
    )
    rule_scopes: Optional[list[RuleScope]] = Field(
        description="List of rule scopes to search for.",
        default=None,
    )
    prompt_enabled: Optional[bool] = Field(
        description="Include or exclude prompt-enabled rules.",
        default=None,
    )
    response_enabled: Optional[bool] = Field(
        description="Include or exclude response-enabled rules.",
        default=None,
    )
    rule_types: Optional[list[RuleType]] = Field(
        description="List of rule types to search for.",
        default=None,
    )


class NewTaskRequest(BaseModel):
    name: str = Field(description="Name of the task.", min_length=1)


class NewApiKeyRequest(BaseModel):
    description: Optional[str] = Field(
        description="Description of the API key. Optional.",
        default=None,
    )
    roles: Optional[list[APIKeysRolesEnum]] = Field(
        description=f"Role that will be assigned to API key. Allowed values: {[role for role in APIKeysRolesEnum]}",
        default=[APIKeysRolesEnum.VALIDATION_USER],
    )


class PromptValidationRequest(BaseModel):
    prompt: str = Field(description="Prompt to be validated by GenAI Engine")
    # context: Optional[str] = Field(
    #     description="Optional data provided as context for the prompt validation. "
    #     "Currently not used"
    # )
    conversation_id: Optional[str] = Field(
        description="The unique conversation ID this prompt belongs to. All prompts and responses from this \
        conversation can later be reconstructed with this ID.",
        default=None,
    )
    user_id: Optional[str] = Field(
        description="The user ID this prompt belongs to",
        default=None,
    )


class ResponseValidationRequest(BaseModel):
    response: str = Field(description="LLM Response to be validated by GenAI Engine")
    context: Optional[str] = Field(
        description="Optional data provided as context for the validation.",
        default=None,
    )
    # tokens: Optional[List[str]] = Field(description="optional, not used currently")
    # token_likelihoods: Optional[List[str]] = Field(
    #     description="optional, not used currently"
    # )

    @model_validator(mode="after")
    def check_prompt_or_response(cls, values):
        if isinstance(values, PromptValidationRequest) and values.prompt is None:
            raise ValueError("prompt is required when validating a prompt")
        if isinstance(values, ResponseValidationRequest) and values.response is None:
            raise ValueError("response is required when validating a response")
        return values


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
    max_llm_rules_per_task_count: Optional[int] = None


class FeedbackRequest(BaseModel):
    target: InferenceFeedbackTarget
    score: int
    reason: str | None
    user_id: str | None = None


class CreateUserRequest(BaseModel):
    email: str
    password: str
    temporary: bool = True
    roles: list[str]
    firstName: str
    lastName: str


class PasswordResetRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def password_meets_security(cls, value: str) -> str:
        special_characters = '!@#$%^&*()-+?_=,<>/"'
        if not len(value) >= constants.GENAI_ENGINE_KEYCLOAK_PASSWORD_LENGTH:
            raise ValueError(constants.ERROR_PASSWORD_POLICY_NOT_MET)
        if (
            not any(c.isupper() for c in value)
            or not any(c.islower() for c in value)
            or not any(c.isdigit() for c in value)
            or not any(c in special_characters for c in value)
        ):
            raise ValueError(constants.ERROR_PASSWORD_POLICY_NOT_MET)
        return value

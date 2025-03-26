from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from schemas.common_schemas import (
    AuthUserRole,
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from schemas.enums import (
    InferenceFeedbackTarget,
    PIIEntityTypes,
    RuleResultEnum,
    RuleScope,
    RuleType,
    ToxicityViolationType,
)


class HTTPError(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "HTTPException raised."},
        },
    )


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
    config: (
        KeywordsConfig
        | RegexConfig
        | ExamplesConfig
        | ToxicityConfig
        | PIIConfig
        | None
    ) = Field(description="Config of the rule", default=None)


class HallucinationClaimResponse(BaseModel):
    claim: str
    valid: bool
    reason: str
    order_number: Optional[int] = Field(
        default=-1,
        description="This field is a helper for ordering the claims",
    )


class PIIEntitySpanResponse(BaseModel):
    entity: PIIEntityTypes
    span: str = Field(
        description="The subtext within the input string that was identified as PII.",
    )
    # Only optional to keep reverse compatibility with old inferences
    confidence: Optional[float] = Field(
        description="Float value representing the confidence score of a given PII identification.",
        default=None,
    )


class KeywordSpanResponse(BaseModel):
    keyword: str = Field(
        description="The keyword from the rule that matched within the input string.",
    )


class RegexSpanResponse(BaseModel):
    matching_text: str = Field(
        description="The subtext within the input string that matched the regex rule.",
    )
    pattern: Optional[str] = Field(
        description="Pattern that yielded the match.",
        default=None,
    )


class BaseDetailsResponse(BaseModel):
    score: Optional[bool] = None
    message: Optional[str] = None


class HallucinationDetailsResponse(BaseDetailsResponse):
    claims: list[HallucinationClaimResponse]


class PIIDetailsResponse(BaseDetailsResponse):
    pii_entities: list[PIIEntitySpanResponse]


class ToxicityDetailsResponse(BaseDetailsResponse):
    toxicity_score: Optional[float] = None
    toxicity_violation_type: ToxicityViolationType

    model_config = ConfigDict(extra="forbid")


class KeywordDetailsResponse(BaseDetailsResponse):
    keyword_matches: list[KeywordSpanResponse] = Field(
        [],
        description="Each keyword in this list corresponds to a keyword that was both configured in the rule that was "
        "run and found in the input text.",
    )

    model_config = ConfigDict(extra="forbid")


class RegexDetailsResponse(BaseDetailsResponse):
    regex_matches: list[RegexSpanResponse] = Field(
        [],
        description="Each string in this list corresponds to a matching span from the input text that matches the "
        "configured regex rule.",
    )

    model_config = ConfigDict(extra="forbid")


class ExternalRuleResult(BaseModel):
    id: str = Field(description=" ID of the rule")
    name: str = Field(description="Name of the rule")
    rule_type: RuleType = Field(description="Type of the rule")
    scope: RuleScope = Field(
        description="Scope of the rule. The rule can be set at default level or task level.",
    )
    result: RuleResultEnum = Field(description="Result if the rule")
    latency_ms: int = Field(description="Duration in millisesconds of rule execution")

    # The super class (BaseDetailsResponse) must come last in this ordering otherwise the fastapi serializer will pick
    # it for the less specific types and you'll waste time figuring out why type1 is being serialized as type2
    # https://github.com/tiangolo/fastapi/issues/2783#issuecomment-776662347
    details: Optional[
        Union[
            KeywordDetailsResponse,
            RegexDetailsResponse,
            HallucinationDetailsResponse,
            PIIDetailsResponse,
            ToxicityDetailsResponse,
            BaseDetailsResponse,
        ]
    ] = Field(description="Details of the rule output", default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "90f18c69-d793-4913-9bde-a0c7f3643de0",
                "name": "PII Rule",
                "result": "Pass",
            },
        },
    )


class ValidationResult(BaseModel):
    inference_id: Optional[str] = Field(description="ID of the inference", default=None)
    rule_results: Optional[List[ExternalRuleResult]] = Field(
        description="List of rule results",
        default=None,
    )
    user_id: Optional[str] = Field(
        description="The user ID this prompt belongs to",
        default=None,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inference_id": "4dd1fae1-34b9-4aec-8abe-fe7bf12af31d",
                "rule_results": [
                    {
                        "id": "90f18c69-d793-4913-9bde-a0c7f3643de0",
                        "name": "PII Check",
                        "result": "Pass",
                    },
                    {
                        "id": "946c4a44-b367-4229-84d4-1a8e461cb132",
                        "name": "Sensitive Data Check",
                        "result": "Pass",
                    },
                ],
            },
        },
    )
    user_id: Optional[str] = Field(
        description="The unique user ID this prompt belongs to",
        default=None,
    )


class ExternalInferencePrompt(BaseModel):
    id: str
    inference_id: str
    result: RuleResultEnum
    created_at: int
    updated_at: int
    message: str
    prompt_rule_results: List[ExternalRuleResult]
    tokens: int | None = None


class ExternalInferenceResponse(BaseModel):
    id: str
    inference_id: str
    result: RuleResultEnum
    created_at: int
    updated_at: int
    message: str
    context: Optional[str] = None
    response_rule_results: List[ExternalRuleResult]
    tokens: int | None = None


class InferenceFeedbackResponse(BaseModel):
    id: str
    inference_id: str
    target: InferenceFeedbackTarget
    score: int
    reason: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class QueryFeedbackResponse(BaseModel):
    feedback: list[InferenceFeedbackResponse] = Field(
        description="List of inferences matching the search filters. Length is less than or equal to page_size parameter",
    )
    page: int = Field(description="The current page number")
    page_size: int = Field(description="The number of feedback items per page")
    total_pages: int = Field(description="The total number of pages")
    total_count: int = Field(
        description="The total number of feedback items matching the query parameters",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback": [
                    {
                        "id": "90f18c69-d793-4913-9bde-a0c7f3643de0",
                        "inference_id": "81437d71-9557-4611-981b-9283d1c98643",
                        "target": "context",
                        "score": "0",
                        "reason": "good reason",
                        "user_id": "user_1",
                        "created_at": "2024-06-06T06:37:46.123-04:00",
                        "updated_at": "2024-06-06T06:37:46.123-04:00",
                    },
                    {
                        "id": "248381c2-543b-4de0-98cd-d7511fee6241",
                        "inference_id": "bcbc7ca0-4cfc-4f67-9cf8-26cb2291ba33",
                        "target": "response_results",
                        "score": "1",
                        "reason": "some reason",
                        "user_id": "user_2",
                        "created_at": "2023-05-05T05:26:35.987-04:00",
                        "updated_at": "2023-05-05T05:26:35.987-04:00",
                    },
                ],
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
                "total_count": 2,
            },
        },
    )


class ExternalInference(BaseModel):
    id: str
    result: RuleResultEnum
    created_at: int
    updated_at: int
    task_id: Optional[str] = None
    task_name: str | None = None
    conversation_id: Optional[str] = None
    inference_prompt: ExternalInferencePrompt
    inference_response: Optional[ExternalInferenceResponse] = None
    inference_feedback: List[InferenceFeedbackResponse]
    user_id: str | None = None


class QueryInferencesResponse(BaseModel):
    count: int = Field(
        description="The total number of inferences matching the query parameters",
    )
    inferences: list[ExternalInference] = Field(
        description="List of inferences matching the search filters. Length is less than or equal to page_size parameter",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 1,
                "inferences": [
                    {
                        "id": "957df309-c907-4b77-abe5-15dd00c081f7",
                        "result": "Pass",
                        "created_at": 1723204737120,
                        "updated_at": 1723204787050,
                        "task_id": "957df309-c907-4b77-abe5-15dd00c081f8",
                        "task_name": "My task name",
                        "conversation_id": "957df309-c907-4b77-abe5-15dd00c08112",
                        "inference_prompt": {
                            "id": "834f7ebd-cd6b-4691-9473-8bc350f8922c",
                            "inference_id": "957df309-c907-4b77-abe5-15dd00c081f7",
                            "result": "Pass",
                            "created_at": 1723204737121,
                            "updated_at": 1723204737121,
                            "message": "How many stars are in the solar system?",
                            "prompt_rule_results": [
                                {
                                    "id": "bc599a56-2e31-4cb7-910d-9e5ed6455db2",
                                    "name": "My_PII_Rule",
                                    "rule_type": "PIIDataRule",
                                    "scope": "default",
                                    "result": "Pass",
                                    "latency_ms": 73,
                                    "details": None,
                                },
                            ],
                            "tokens": 100,
                        },
                        "inference_response": {
                            "id": "ec765a75-1479-4938-8e1c-6334b7deb8ce",
                            "inference_id": "957df309-c907-4b77-abe5-15dd00c081f7",
                            "result": "Pass",
                            "created_at": 1723204786599,
                            "updated_at": 1723204786599,
                            "message": "There is one star in solar system.",
                            "context": "Solar system contains one star.",
                            "response_rule_results": [
                                {
                                    "id": "a45267c5-96d9-4de2-a871-debf2c8fdb86",
                                    "name": "My_another_PII_Rule",
                                    "rule_type": "PIIDataRule",
                                    "scope": "default",
                                    "result": "Pass",
                                    "latency_ms": 107,
                                    "details": None,
                                },
                                {
                                    "id": "92b7b46e-eaf2-4226-82d4-be12ceb3e4b7",
                                    "name": "My_Hallucination_Rule",
                                    "rule_type": "ModelHallucinationRuleV2",
                                    "scope": "default",
                                    "result": "Pass",
                                    "latency_ms": 700,
                                    "details": {
                                        "score": True,
                                        "message": "All claims were supported by the context!",
                                        "claims": [
                                            {
                                                "claim": "There is one star in solar system.",
                                                "valid": True,
                                                "reason": "No hallucination detected!",
                                                "order_number": 0,
                                            },
                                        ],
                                        "pii_results": [],
                                        "pii_entities": [],
                                        "toxicity_score": None,
                                    },
                                },
                            ],
                            "tokens": 100,
                        },
                        "inference_feedback": [
                            {
                                "id": "0d602e5c-4ae6-4fc9-a610-68a1d8928ad7",
                                "inference_id": "957df309-c907-4b77-abe5-15dd00c081f7",
                                "target": "context",
                                "score": 100,
                                "reason": "Perfect answer.",
                                "user_id": "957df309-2137-4b77-abe5-15dd00c081f8",
                                "created_at": "2024-08-09T12:08:34.847381",
                                "updated_at": "2024-08-09T12:08:34.847386",
                            },
                        ],
                        "user_id": "957df309-2137-4b77-abe5-15dd00c081f8",
                    },
                ],
            },
        },
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
    rules: List[RuleResponse] = Field(description="List of all the rule for the task.")


class SearchTasksResponse(BaseModel):
    count: int = Field(description="The total number of tasks matching the parameters")
    tasks: list[TaskResponse] = Field(
        description="List of tasks matching the search filters. Length is less than or equal to page_size parameter",
    )


class SearchRulesResponse(BaseModel):
    count: int = Field(description="The total number of rules matching the parameters")
    rules: list[RuleResponse] = Field(
        description="List of rules matching the search filters. Length is less than or equal to page_size parameter",
    )


class FileUploadResult(BaseModel):
    id: str
    name: str
    type: str
    word_count: int
    success: bool


class ExternalDocument(BaseModel):
    id: str
    name: str
    type: str
    owner_id: str


class ChatDocumentContext(BaseModel):
    id: str
    seq_num: int
    context: str


class ChatResponse(BaseModel):
    inference_id: str = Field(description="ID of the inference sent to the chat")
    conversation_id: str = Field(description="ID of the conversation session")
    timestamp: int = Field(
        description="Time the inference was made in unix milliseconds",
    )
    retrieved_context: List[ChatDocumentContext] = Field(
        description="related sections of documents that were most relevant to the inference prompt. "
        "Formatted as a list of retrieved context chunks which include document name, seq num, and context.",
    )
    llm_response: str = Field(
        description="response from the LLM for the original user prompt",
    )
    prompt_results: List[ExternalRuleResult] = Field(
        description="list of rule results for the user prompt",
    )
    response_results: List[ExternalRuleResult] = Field(
        description="list of rule results for the llm response",
    )


class DocumentStorageConfigurationResponse(BaseModel):
    storage_environment: Optional[str] = None
    bucket_name: Optional[str] = None
    container_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None


class ApplicationConfigurationResponse(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[DocumentStorageConfigurationResponse] = (
        None
    )
    max_llm_rules_per_task_count: int


class TokenUsageCount(BaseModel):
    inference: int = Field(description="Number of inference tokens sent to Arthur.")
    eval_prompt: int = Field(
        description="Number of Prompt tokens incurred by Arthur rules.",
    )
    eval_completion: int = Field(
        description="Number of Completion tokens incurred by Arthur rules.",
    )
    user_input: int = Field(
        description="Number of user input tokens sent to Arthur. This field is deprecated and will be removed in the future. Use inference instead.",
        json_schema_extra={"deprecated": True},
    )
    prompt: int = Field(
        description="Number of Prompt tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_prompt instead.",
        json_schema_extra={"deprecated": True},
    )
    completion: int = Field(
        description="Number of Completion tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_completion instead.",
        json_schema_extra={"deprecated": True},
    )


class TokenUsageResponse(BaseModel):
    rule_type: Optional[str] = None
    task_id: Optional[str] = None
    count: TokenUsageCount


class ApiKeyResponse(BaseModel):
    id: str = Field(description="ID of the key")
    key: Optional[str] = Field(
        description="The generated GenAI Engine API key. The key is displayed on key creation request only.",
        default=None,
    )
    description: Optional[str] = Field(
        description="Description of the API key",
        default=None,
    )
    is_active: bool = Field(description="Status of the key.")
    created_at: datetime = Field(description="Creation time of the key")
    deactivated_at: Optional[datetime] = Field(
        description="Deactivation time of the key",
        default=None,
    )
    message: Optional[str] = Field(description="Optional Message", default=None)
    roles: list[str] = Field(
        description="Roles of the API key",
        default=[],
    )


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list[AuthUserRole]


class ConversationBaseResponse(BaseModel):
    id: str
    updated_at: datetime


class ConversationResponse(ConversationBaseResponse):
    inferences: list[ExternalInference]


class HealthResponse(BaseModel):
    message: str
    build_version: Optional[str] = None


class ChatDefaultTaskResponse(BaseModel):
    task_id: str

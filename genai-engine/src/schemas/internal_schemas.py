import json
import logging
import uuid
from datetime import datetime
from typing import List, Literal, Optional, Union

from arthur_common.models.common_schemas import (
    AuthUserRole,
    ExampleConfig,
    ExamplesConfig,
    KeywordsConfig,
    PaginationParameters,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from arthur_common.models.enums import (
    ComparisonOperatorEnum,
    InferenceFeedbackTarget,
    MetricType,
    PIIEntityTypes,
    RuleResultEnum,
    RuleScope,
    RuleType,
    ToolClassEnum,
    ToxicityViolationType,
)
from arthur_common.models.request_schemas import (
    NewMetricRequest,
    NewRuleRequest,
    NewTaskRequest,
    TraceQueryRequest,
)
from arthur_common.models.response_schemas import (
    ApiKeyResponse,
    BaseDetailsResponse,
    ChatDocumentContext,
    ExternalDocument,
    ExternalInference,
    ExternalInferencePrompt,
    ExternalInferenceResponse,
    ExternalRuleResult,
    HallucinationClaimResponse,
    HallucinationDetailsResponse,
    InferenceFeedbackResponse,
    KeywordDetailsResponse,
    KeywordSpanResponse,
    MetricResponse,
    MetricResultResponse,
    NestedSpanWithMetricsResponse,
    PIIDetailsResponse,
    PIIEntitySpanResponse,
    RegexDetailsResponse,
    RegexSpanResponse,
    RuleResponse,
    SpanWithMetricsResponse,
    TaskResponse,
    TokenCountCostSchema,
    ToxicityDetailsResponse,
    UserResponse,
)
from fastapi import HTTPException
from opentelemetry import trace
from pydantic import BaseModel, Field, SecretStr
from pydantic_core import Url

from db_models import (
    DatabaseApiKey,
    DatabaseApplicationConfiguration,
    DatabaseDataset,
    DatabaseDocument,
    DatabaseEmbedding,
    DatabaseEmbeddingReference,
    DatabaseHallucinationClaim,
    DatabaseInference,
    DatabaseInferenceFeedback,
    DatabaseInferencePrompt,
    DatabaseInferencePromptContent,
    DatabaseInferenceResponse,
    DatabaseInferenceResponseContent,
    DatabaseKeywordEntity,
    DatabaseMetric,
    DatabaseMetricResult,
    DatabasePIIEntity,
    DatabasePromptRuleResult,
    DatabaseRegexEntity,
    DatabaseResponseRuleResult,
    DatabaseRule,
    DatabaseRuleResultDetail,
    DatabaseSecretStorage,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTaskToMetrics,
    DatabaseTaskToRules,
    DatabaseToxicityScore,
    DatabaseTraceMetadata,
    DatabaseUser,
)
from db_models.dataset_models import DatabaseDatasetVersion, DatabaseDatasetVersionRow
from db_models.rag_provider_models import (
    DatabaseApiKeyRagProviderConfiguration,
    DatabaseRagProviderAuthenticationConfigurationTypes,
)
from schemas.enums import (
    ApplicationConfigurations,
    DocumentStorageEnvironment,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RuleDataType,
    RuleScoringMethod,
    SecretType,
)
from schemas.metric_schemas import MetricScoreDetails
from schemas.request_schemas import (
    ApiKeyRagAuthenticationConfigRequest,
    NewDatasetRequest,
    NewDatasetVersionRequest,
    NewDatasetVersionRowColumnItemRequest,
    RagProviderConfigurationRequest,
)
from schemas.response_schemas import (
    ApiKeyRagAuthenticationConfigResponse,
    ApplicationConfigurationResponse,
    DatasetResponse,
    DatasetVersionMetadataResponse,
    DatasetVersionResponse,
    DatasetVersionRowColumnItemResponse,
    DatasetVersionRowResponse,
    DocumentStorageConfigurationResponse,
    ListDatasetVersionsResponse,
    RagProviderConfigurationResponse,
    SessionMetadataResponse,
    SpanMetadataResponse,
    TraceMetadataResponse,
    TraceUserMetadataResponse,
)
from schemas.rules_schema_utils import CONFIG_CHECKERS, RuleData
from schemas.scorer_schemas import (
    RuleScore,
    ScorerHallucinationClaim,
    ScorerKeywordSpan,
    ScorerPIIEntitySpan,
    ScorerRegexSpan,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from utils import constants
from utils import trace as trace_utils
from utils.constants import MAX_DATASET_ROWS
from utils.utils import calculate_duration_ms

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()


def _serialize_datetime(dt: datetime) -> int:
    epoch = datetime.fromtimestamp(0)
    return int((dt - epoch).total_seconds() * 1000.0)


############################################################
# API V2 Schemas
############################################################
class Rule(BaseModel):
    id: str
    name: str
    type: RuleType
    prompt_enabled: bool
    response_enabled: bool
    scoring_method: RuleScoringMethod
    created_at: datetime
    updated_at: datetime
    rule_data: List[RuleData]
    scope: RuleScope
    archived: bool

    @staticmethod
    def _from_request_model(x: NewRuleRequest, scope: RuleScope):
        rule_configurations = []
        scoring_method = RuleScoringMethod.BINARY
        if x.type in [rule_type.value for rule_type in RuleType]:
            config_checker = CONFIG_CHECKERS[x.type]
            rule_type = RuleType(x.type)

            if x.config:
                rule_configurations = config_checker(x.config)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unknown rule type: %s" % x.type,
            )

        return Rule(
            id=str(uuid.uuid4()),
            name=x.name,
            type=rule_type,
            prompt_enabled=x.apply_to_prompt,
            response_enabled=x.apply_to_response,
            scoring_method=scoring_method,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            rule_data=rule_configurations,
            scope=scope,
            archived=False,
        )

    @staticmethod
    def _from_database_model(x: DatabaseRule):
        return Rule(
            id=x.id,
            name=x.name,
            type=x.type,
            prompt_enabled=x.prompt_enabled,
            response_enabled=x.response_enabled,
            scoring_method=x.scoring_method,
            created_at=x.created_at,
            updated_at=x.updated_at,
            rule_data=[RuleData._from_database_model(x) for x in x.rule_data],
            archived=x.archived,
            scope=x.scope,
        )

    def _to_database_model(self):
        return DatabaseRule(
            id=self.id,
            name=self.name,
            type=self.type,
            prompt_enabled=self.prompt_enabled,
            response_enabled=self.response_enabled,
            scoring_method=self.scoring_method,
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived=self.archived,
            scope=self.scope,
            rule_data=[d._to_database_model() for d in self.rule_data],
        )

    def _to_response_model(self):
        config = None
        if self.type == RuleType.REGEX:
            config = self.get_regex_config()
        elif self.type == RuleType.KEYWORD:
            config = self.get_keywords_config()
        elif self.type == RuleType.MODEL_SENSITIVE_DATA:
            config = self.get_examples_config()
        elif self.type == RuleType.TOXICITY:
            config = self.get_threshold_config()
        elif self.type == RuleType.PII_DATA:
            config = self.get_pii_config()
        return RuleResponse(
            id=self.id,
            name=self.name,
            type=self.type,
            apply_to_prompt=self.prompt_enabled,
            apply_to_response=self.response_enabled,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            config=config,
            scope=self.scope,
        )

    def get_keywords_config(self):
        return KeywordsConfig(
            keywords=[
                d.data for d in self.rule_data if d.data_type == RuleDataType.KEYWORD
            ],
        )

    def get_regex_config(self):
        regex_patterns = [rd.data for rd in self.rule_data]
        config = RegexConfig(regex_patterns=regex_patterns)
        return config

    def get_examples_config(self):
        examples = []
        hint = ""
        for d in self.rule_data:
            if d.data_type == RuleDataType.JSON:
                examples.append(ExampleConfig.model_validate_json(d.data))
            if d.data_type == RuleDataType.HINT:
                hint = d.data
        return ExamplesConfig(
            examples=examples,
            hint=hint,
        )

    def get_threshold_config(self):
        thresholds = [
            d.data
            for d in self.rule_data
            if d.data_type == RuleDataType.TOXICITY_THRESHOLD
        ]
        threshold = constants.DEFAULT_TOXICITY_RULE_THRESHOLD
        if thresholds:
            threshold = float(thresholds[0])
        return ToxicityConfig(threshold=threshold)

    """Converts a given rule and its rule_data to PIIConfig"""

    def get_pii_config(self):
        allow_list = []
        disabled_pii_entities = []
        confidence_threshold = constants.DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD
        for config in self.rule_data:
            if config.data_type == RuleDataType.PII_DISABLED_PII:
                disabled_pii_entities = config.data.split(",")

            if config.data_type == RuleDataType.PII_THRESHOLD:
                confidence_threshold = config.data

            if config.data_type == RuleDataType.PII_ALLOW_LIST:
                allow_list = config.data.split(",")

        return PIIConfig(
            disabled_pii_entities=disabled_pii_entities,
            confidence_threshold=confidence_threshold,
            allow_list=allow_list,
        )


class Metric(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    type: MetricType
    name: str
    metric_metadata: Optional[str] = None
    config: Optional[str] = None  # JSON-serialized config

    @staticmethod
    def _from_request_model(request: NewMetricRequest) -> "Metric":
        config_json = None
        if request.config:
            config_json = request.config.model_dump_json()

        return Metric(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            type=request.type,
            name=request.name,
            metric_metadata=request.metric_metadata,
            config=config_json,
        )

    @staticmethod
    def _from_database_model(x: DatabaseMetric):
        return Metric(
            id=x.id,
            created_at=x.created_at,
            updated_at=x.updated_at,
            type=x.type,
            name=x.name,
            metric_metadata=x.metric_metadata,
            config=x.config,
        )

    def _to_database_model(self) -> DatabaseMetric:
        return DatabaseMetric(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            type=self.type,
            name=self.name,
            metric_metadata=self.metric_metadata,
            config=self.config,
        )

    def _to_response_model(self) -> MetricResponse:
        return MetricResponse(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            type=self.type,
            name=self.name,
            metric_metadata=self.metric_metadata,
            config=self.config,
        )


class MetricResult(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metric_type: MetricType
    details: Optional[MetricScoreDetails] = None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    span_id: Optional[str] = None
    metric_id: Optional[str] = None

    @staticmethod
    def _from_database_model(x: DatabaseMetricResult):
        return MetricResult(
            id=x.id,
            created_at=x.created_at,
            updated_at=x.updated_at,
            metric_type=x.metric_type,
            details=(
                MetricScoreDetails.model_validate(
                    json.loads(x.details) if isinstance(x.details, str) else x.details,
                )
                if x.details
                else None
            ),
            prompt_tokens=x.prompt_tokens,
            completion_tokens=x.completion_tokens,
            latency_ms=x.latency_ms,
            span_id=x.span_id,
            metric_id=x.metric_id,
        )

    def _to_database_model(self) -> DatabaseMetricResult:
        if self.span_id is None or self.metric_id is None:
            raise ValueError(
                "span_id and metric_id must be set before converting to database model",
            )

        details_dict = None
        if self.details:
            details_dict = self.details.model_dump()
        return DatabaseMetricResult(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metric_type=self.metric_type,
            details=details_dict,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            span_id=self.span_id,
            metric_id=self.metric_id,
        )

    def _to_response_model(self):

        return MetricResultResponse(
            id=self.id,
            metric_type=self.metric_type,
            details=self.details.model_dump_json() if self.details else None,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            span_id=self.span_id,
            metric_id=self.metric_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class TaskToRuleLink(BaseModel):
    task_id: str
    rule_id: str
    enabled: bool
    rule: Rule

    @staticmethod
    def _from_database_model(x: DatabaseTaskToRules):
        return TaskToRuleLink(
            task_id=x.task_id,
            rule_id=x.rule_id,
            enabled=x.enabled,
            rule=Rule._from_database_model(x.rule),
        )


class TaskToMetricLink(BaseModel):
    task_id: str
    metric_id: str
    enabled: bool
    metric: Metric

    @staticmethod
    def _from_database_model(x: DatabaseTaskToMetrics):
        return TaskToMetricLink(
            task_id=x.task_id,
            metric_id=x.metric_id,
            enabled=x.enabled,
            metric=Metric._from_database_model(x.metric),
        )


class Task(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    is_agentic: bool = False
    rule_links: Optional[List[TaskToRuleLink]] = None
    metric_links: Optional[List[TaskToMetricLink]] = None

    @staticmethod
    def _from_request_model(x: NewTaskRequest):
        return Task(
            id=str(uuid.uuid4()),
            name=x.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=x.is_agentic,
        )

    @staticmethod
    def _from_database_model(x: DatabaseTask):
        return Task(
            id=x.id,
            name=x.name,
            created_at=x.created_at,
            updated_at=x.updated_at,
            is_agentic=x.is_agentic,
            rule_links=[
                TaskToRuleLink._from_database_model(link) for link in x.rule_links
            ],
            metric_links=[
                TaskToMetricLink._from_database_model(link) for link in x.metric_links
            ],
        )

    def _to_database_model(self):
        return DatabaseTask(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            updated_at=self.updated_at,
            is_agentic=self.is_agentic,
        )

    def _to_response_model(self):
        response_rules = []
        for link in self.rule_links:
            response_rule: RuleResponse = link.rule._to_response_model()
            response_rule.enabled = link.enabled
            response_rules.append(response_rule)

        response_metrics = []
        for link in self.metric_links:
            response_metric: MetricResponse = link.metric._to_response_model()
            response_metric.enabled = link.enabled
            response_metrics.append(response_metric)

        return TaskResponse(
            id=self.id,
            name=self.name,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            is_agentic=self.is_agentic,
            rules=response_rules,
            metrics=response_metrics,
        )


class TraceMetadata(TokenCountCostSchema):
    trace_id: str
    task_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    span_count: int
    created_at: datetime
    updated_at: datetime
    input_content: Optional[str] = None
    output_content: Optional[str] = None

    @staticmethod
    def _from_database_model(x: DatabaseTraceMetadata):
        return TraceMetadata(
            trace_id=x.trace_id,
            task_id=x.task_id,
            user_id=x.user_id,
            session_id=x.session_id,
            start_time=x.start_time,
            end_time=x.end_time,
            span_count=x.span_count,
            prompt_token_count=x.prompt_token_count,
            completion_token_count=x.completion_token_count,
            total_token_count=x.total_token_count,
            prompt_token_cost=x.prompt_token_cost,
            completion_token_cost=x.completion_token_cost,
            total_token_cost=x.total_token_cost,
            created_at=x.created_at,
            updated_at=x.updated_at,
            input_content=x.input_content,
            output_content=x.output_content,
        )

    def _to_database_model(self):
        return DatabaseTraceMetadata(
            trace_id=self.trace_id,
            task_id=self.task_id,
            user_id=self.user_id,
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=self.end_time,
            span_count=self.span_count,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
            created_at=self.created_at,
            updated_at=self.updated_at,
            input_content=self.input_content,
            output_content=self.output_content,
        )

    def _to_metadata_response_model(self) -> TraceMetadataResponse:
        """Convert to lightweight metadata response"""
        duration_ms = calculate_duration_ms(self.start_time, self.end_time)
        return TraceMetadataResponse(
            trace_id=self.trace_id,
            task_id=self.task_id,
            user_id=self.user_id,
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=self.end_time,
            span_count=self.span_count,
            duration_ms=duration_ms,
            created_at=self.created_at,
            updated_at=self.updated_at,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
            input_content=self.input_content,
            output_content=self.output_content,
        )


class HallucinationClaims(BaseModel):
    claim: str
    valid: bool
    reason: str
    order_number: int = -1

    @staticmethod
    def _from_database_model(x: DatabaseHallucinationClaim):
        return HallucinationClaims(
            claim=x.claim,
            valid=x.valid,
            reason=x.reason,
            order_number=x.order_number,
        )

    def _to_database_model(self, rule_result_detail_id: str):
        return DatabaseHallucinationClaim(
            id=str(uuid.uuid4()),
            rule_result_detail_id=rule_result_detail_id,
            claim=self.claim,
            valid=self.valid,
            reason=self.reason,
            order_number=self.order_number,
        )

    def _to_response_model(self):
        return HallucinationClaimResponse(
            claim=self.claim,
            valid=self.valid,
            reason=self.reason,
            order_number=self.order_number,
        )

    @staticmethod
    def _from_scorer_model(x: ScorerHallucinationClaim):
        return HallucinationClaims(
            claim=x.claim,
            valid=x.valid,
            reason=x.reason,
            order_number=x.order_number,
        )


class PIIEntitySpan(BaseModel):
    entity: PIIEntityTypes
    span: str
    confidence: Optional[float] = None

    @staticmethod
    def _from_database_model(x: DatabasePIIEntity):
        return PIIEntitySpan(entity=x.entity, span=x.span, confidence=x.confidence)

    def _to_database_model(self, rule_result_detail_id: str):
        return DatabasePIIEntity(
            id=str(uuid.uuid4()),
            rule_result_detail_id=rule_result_detail_id,
            entity=self.entity,
            span=self.span,
            confidence=self.confidence,
        )

    def _to_response_model(self):
        return PIIEntitySpanResponse(
            entity=self.entity,
            span=self.span,
            confidence=self.confidence,
        )

    @staticmethod
    def _from_scorer_model(x: ScorerPIIEntitySpan):
        return PIIEntitySpan(entity=x.entity, span=x.span, confidence=x.confidence)


class KeywordSpan(BaseModel):
    keyword: str

    @staticmethod
    def _from_database_model(x: DatabaseKeywordEntity):
        return KeywordSpan(keyword=x.keyword)

    def _to_database_model(self, rule_result_detail_id: str):
        return DatabaseKeywordEntity(
            id=str(uuid.uuid4()),
            rule_result_detail_id=rule_result_detail_id,
            keyword=self.keyword,
        )

    def _to_response_model(self):
        return KeywordSpanResponse(
            keyword=self.keyword,
        )

    @staticmethod
    def _from_scorer_model(x: ScorerKeywordSpan):
        return KeywordSpan(keyword=x.keyword)


class RegexSpan(BaseModel):
    matching_text: str
    # Nullable for past inferences before this feature that won't have this field populated
    pattern: Optional[str] = None

    @staticmethod
    def _from_database_model(x: DatabaseRegexEntity):
        return RegexSpan(matching_text=x.matching_text, pattern=x.pattern)

    def _to_database_model(self, rule_result_detail_id: str):
        return DatabaseRegexEntity(
            id=str(uuid.uuid4()),
            rule_result_detail_id=rule_result_detail_id,
            matching_text=self.matching_text,
            pattern=self.pattern,
        )

    def _to_response_model(self):
        return RegexSpanResponse(
            matching_text=self.matching_text,
            pattern=self.pattern,
        )

    @staticmethod
    def _from_scorer_model(x: ScorerRegexSpan):
        return RegexSpan(matching_text=x.matching_text, pattern=x.pattern)


class ToxicityScore(BaseModel):
    toxicity_score: float
    toxicity_violation_type: ToxicityViolationType

    @staticmethod
    def _from_database_model(x: DatabaseToxicityScore):
        return ToxicityScore(
            toxicity_score=x.toxicity_score,
            toxicity_violation_type=ToxicityViolationType(x.toxicity_violation_type),
        )

    def _to_database_model(self, rule_result_detail_id: str):
        return DatabaseToxicityScore(
            id=str(uuid.uuid4()),
            rule_result_detail_id=rule_result_detail_id,
            toxicity_score=self.toxicity_score,
            toxicity_violation_type=self.toxicity_violation_type.value,
        )

    @staticmethod
    def _from_scorer_model(x: ScorerToxicityScore):
        return ToxicityScore(
            toxicity_score=x.toxicity_score,
            toxicity_violation_type=x.toxicity_violation_type,
        )


class RuleDetails(BaseModel):
    score: Optional[bool] = None
    message: Optional[str] = None
    claims: Optional[list[HallucinationClaims]] = None
    pii_results: Optional[list[PIIEntityTypes]] = None
    pii_entities: Optional[list[PIIEntitySpan]] = None
    toxicity_score: Optional[ToxicityScore] = None
    keyword_matches: Optional[list[KeywordSpan]] = None
    regex_matches: Optional[list[RegexSpan]] = None

    @staticmethod
    def _from_scorer_model(x: ScorerRuleDetails):
        return RuleDetails(
            score=x.score,
            message=x.message,
            claims=(
                [HallucinationClaims._from_scorer_model(h) for h in x.claims]
                if x.claims is not None
                else []
            ),
            pii_results=x.pii_results,
            pii_entities=(
                [PIIEntitySpan._from_scorer_model(e) for e in x.pii_entities]
                if x.pii_entities is not None
                else []
            ),
            toxicity_score=(
                ToxicityScore._from_scorer_model(x.toxicity_score)
                if x.toxicity_score is not None
                else None
            ),
            keyword_matches=(
                [KeywordSpan._from_scorer_model(e) for e in x.keywords]
                if x.keywords is not None
                else []
            ),
            regex_matches=(
                [RegexSpan._from_scorer_model(e) for e in x.regex_matches]
                if x.regex_matches is not None
                else []
            ),
        )

    @staticmethod
    def _from_database_model(x: DatabaseRuleResultDetail):
        return RuleDetails(
            score=x.score,
            message=x.message,
            claims=[HallucinationClaims._from_database_model(c) for c in x.claims],
            pii_results=[c.entity for c in x.pii_entities],
            pii_entities=[
                PIIEntitySpan._from_database_model(c) for c in x.pii_entities
            ],
            toxicity_score=(
                ToxicityScore._from_database_model(x.toxicity_score)
                if x.toxicity_score
                else None
            ),
            keyword_matches=[
                KeywordSpan._from_database_model(c) for c in x.keyword_matches
            ],
            regex_matches=[RegexSpan._from_database_model(c) for c in x.regex_matches],
        )

    def _to_database_model(
        self,
        parent_prompt_rule_result_id: str = None,
        parent_response_rule_result_id: str = None,
    ):
        if not (parent_prompt_rule_result_id or parent_response_rule_result_id):
            raise ValueError("One of prompt or response result id must be supplied")
        id = str(uuid.uuid4())
        return DatabaseRuleResultDetail(
            id=id,
            prompt_rule_result_id=parent_prompt_rule_result_id,
            response_rule_result_id=parent_response_rule_result_id,
            score=self.score,
            message=self.message,
            claims=(
                [claim._to_database_model(id) for claim in self.claims]
                if self.claims
                else []
            ),
            pii_entities=(
                [entity._to_database_model(id) for entity in self.pii_entities]
                if self.pii_entities
                else []
            ),
            toxicity_score=(
                self.toxicity_score._to_database_model(id)
                if self.toxicity_score
                else None
            ),
            keyword_matches=(
                [match._to_database_model(id) for match in self.keyword_matches]
                if self.keyword_matches
                else []
            ),
            regex_matches=(
                [match._to_database_model(id) for match in self.regex_matches]
                if self.regex_matches
                else []
            ),
        )

    def _to_response_model(self, rule_type: RuleType):
        match rule_type:
            case RuleType.MODEL_HALLUCINATION_V2:
                return HallucinationDetailsResponse(
                    score=self.score,
                    message=self.message,
                    claims=sorted(
                        [c._to_response_model() for c in self.claims],
                        key=lambda x: x.order_number,
                    ),
                )
            case RuleType.PII_DATA:
                return PIIDetailsResponse(
                    score=self.score,
                    message=self.message,
                    pii_results=[c.entity for c in self.pii_entities],
                    pii_entities=[c._to_response_model() for c in self.pii_entities],
                )
            case RuleType.TOXICITY:
                return ToxicityDetailsResponse(
                    score=self.score,
                    message=self.message,
                    toxicity_score=(
                        self.toxicity_score.toxicity_score
                        if self.toxicity_score
                        else None
                    ),
                    toxicity_violation_type=(
                        self.toxicity_score.toxicity_violation_type
                        if self.toxicity_score
                        else ToxicityViolationType.UNKNOWN
                    ),
                )
            case RuleType.KEYWORD:
                return KeywordDetailsResponse(
                    score=self.score,
                    message=self.message,
                    keyword_matches=[
                        k._to_response_model() for k in self.keyword_matches
                    ],
                )
            case RuleType.REGEX:
                return RegexDetailsResponse(
                    score=self.score,
                    message=self.message,
                    regex_matches=[k._to_response_model() for k in self.regex_matches],
                )
            case _:
                return BaseDetailsResponse(score=self.score, message=self.message)


class RuleResult(BaseModel):
    id: str
    rule: Rule
    rule_result: RuleResultEnum
    rule_details: Optional[RuleDetails] = None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int

    def _to_response_model(self):
        return ExternalRuleResult(
            id=self.rule.id,
            name=self.rule.name,
            rule_type=self.rule.type,
            scope=self.rule.scope,
            result=self.rule_result,
            details=(
                self.rule_details._to_response_model(rule_type=self.rule.type)
                if self.rule_details
                else None
            ),
            latency_ms=self.latency_ms,
        )


class RuleEngineResult(BaseModel):
    rule_score_result: RuleScore
    rule: Rule
    latency_ms: int


class PromptRuleResult(RuleResult):
    @staticmethod
    def _from_database_model(x: DatabasePromptRuleResult):
        return PromptRuleResult(
            id=x.id,
            rule=Rule._from_database_model(x.rule),
            rule_result=x.rule_result,
            rule_details=(
                RuleDetails._from_database_model(x.rule_details)
                if x.rule_details
                else None
            ),
            prompt_tokens=x.prompt_tokens,
            completion_tokens=x.completion_tokens,
            latency_ms=x.latency_ms,
        )

    @staticmethod
    def _from_rule_engine_model(x: RuleEngineResult):
        return PromptRuleResult(
            id=str(uuid.uuid4()),
            rule=x.rule,
            rule_result=x.rule_score_result.result,
            rule_details=(
                RuleDetails._from_scorer_model(x.rule_score_result.details)
                if x.rule_score_result.details
                else None
            ),
            prompt_tokens=x.rule_score_result.prompt_tokens,
            completion_tokens=x.rule_score_result.completion_tokens,
            latency_ms=x.latency_ms,
        )

    def _to_database_model(self):
        return DatabasePromptRuleResult(
            id=self.id,
            rule_id=self.rule.id,
            rule_result=self.rule_result.value,
            rule_details=(
                self.rule_details._to_database_model(
                    parent_prompt_rule_result_id=self.id,
                )
                if self.rule_details
                else None
            ),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class ResponseRuleResult(RuleResult):
    @staticmethod
    def _from_database_model(x: DatabaseResponseRuleResult):
        return ResponseRuleResult(
            id=x.id,
            rule=Rule._from_database_model(x.rule),
            rule_result=x.rule_result,
            rule_details=(
                RuleDetails._from_database_model(x.rule_details)
                if x.rule_details
                else None
            ),
            prompt_tokens=x.prompt_tokens,
            completion_tokens=x.completion_tokens,
            latency_ms=x.latency_ms,
        )

    @staticmethod
    def _from_rule_engine_model(x: RuleEngineResult):
        return ResponseRuleResult(
            id=str(uuid.uuid4()),
            rule=x.rule,
            rule_result=x.rule_score_result.result,
            rule_details=(
                RuleDetails._from_scorer_model(x.rule_score_result.details)
                if x.rule_score_result.details
                else None
            ),
            prompt_tokens=x.rule_score_result.prompt_tokens,
            completion_tokens=x.rule_score_result.completion_tokens,
            latency_ms=x.latency_ms,
        )

    def _to_database_model(self):
        return DatabaseResponseRuleResult(
            id=self.id,
            rule_id=self.rule.id,
            rule_result=self.rule_result.value,
            rule_details=(
                self.rule_details._to_database_model(
                    parent_response_rule_result_id=self.id,
                )
                if self.rule_details
                else None
            ),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class InferenceResponse(BaseModel):
    id: str
    inference_id: str
    result: RuleResultEnum
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None
    context: Optional[str] = None
    response_rule_results: List[ResponseRuleResult] = []
    tokens: int | None = None
    model_name: Optional[str] = None

    @staticmethod
    def _from_database_model(x: DatabaseInferenceResponse):
        return InferenceResponse(
            id=x.id,
            inference_id=x.inference_id,
            result=x.result,
            created_at=x.created_at,
            updated_at=x.updated_at,
            message=x.content.content,
            context=x.content.context,
            response_rule_results=[
                ResponseRuleResult._from_database_model(r)
                for r in x.response_rule_results
            ],
            tokens=x.tokens,
            model_name=x.model_name,
        )

    def _to_response_model(self):
        return ExternalInferenceResponse(
            id=self.id,
            inference_id=self.inference_id,
            result=self.result,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            # Blank message vs empty (in case of error for example) since we kinda expect this to always be present
            message=self.message if self.message else "",
            context=self.context if self.context else "",
            response_rule_results=[
                r._to_response_model() for r in self.response_rule_results
            ],
            tokens=self.tokens,
        )

    def _to_database_model(self):
        return DatabaseInferenceResponse(
            id=self.id,
            inference_id=self.inference_id,
            result=self.result,
            created_at=self.created_at,
            updated_at=self.updated_at,
            content=DatabaseInferenceResponseContent(
                inference_response_id=self.id,
                content=self.message,
                context=self.context,
            ),
            response_rule_results=[
                r._to_database_model() for r in self.response_rule_results
            ],
            tokens=self.tokens,
            model_name=self.model_name,
        )


class InferencePrompt(BaseModel):
    id: str
    inference_id: str
    result: RuleResultEnum
    created_at: datetime
    updated_at: datetime
    message: str = None
    prompt_rule_results: Optional[List[PromptRuleResult]] = None
    tokens: int | None = None

    @staticmethod
    def _from_database_model(x: DatabaseInferencePrompt):
        return InferencePrompt(
            id=x.id,
            inference_id=x.inference_id,
            result=x.result,
            created_at=x.created_at,
            updated_at=x.updated_at,
            message=x.content.content,
            prompt_rule_results=[
                PromptRuleResult._from_database_model(r) for r in x.prompt_rule_results
            ],
            tokens=x.tokens,
        )

    def _to_response_model(self):
        return ExternalInferencePrompt(
            id=self.id,
            inference_id=self.inference_id,
            result=self.result,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            # Blank message vs empty (in case of error for example) since we kinda expect this to always be present
            message=self.message if self.message is not None else "",
            prompt_rule_results=[
                r._to_response_model() for r in self.prompt_rule_results
            ],
            tokens=self.tokens,
        )

    def _to_database_model(self):
        return DatabaseInferencePrompt(
            id=self.id,
            inference_id=self.inference_id,
            result=self.result,
            created_at=self.created_at,
            updated_at=self.updated_at,
            content=DatabaseInferencePromptContent(
                inference_prompt_id=self.id,
                content=self.message,
            ),
            prompt_rule_results=[
                r._to_database_model() for r in self.prompt_rule_results
            ],
            tokens=self.tokens,
        )


class InferenceFeedback(BaseModel):
    id: str | None = None
    inference_id: str
    target: InferenceFeedbackTarget
    score: int
    reason: Optional[str] = None
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_database_model(dif: DatabaseInferenceFeedback):
        return InferenceFeedback(
            id=dif.id,
            inference_id=dif.inference_id,
            target=dif.target,
            score=dif.score,
            reason=dif.reason,
            user_id=dif.user_id,
            created_at=dif.created_at,
            updated_at=dif.updated_at,
        )

    def to_response_model(self):
        return InferenceFeedbackResponse(
            id=self.id,
            inference_id=self.inference_id,
            target=self.target,
            score=self.score,
            reason=self.reason,
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class Inference(BaseModel):
    id: str
    result: RuleResultEnum
    created_at: datetime
    updated_at: datetime
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    conversation_id: Optional[str] = None
    inference_prompt: Optional[InferencePrompt] = None
    inference_response: Optional[InferenceResponse] = None
    inference_feedback: List[InferenceFeedback]
    user_id: Optional[str] = None
    model_name: Optional[str] = None

    def has_prompt(self):
        return self.inference_prompt != None

    def has_response(self):
        return self.inference_response != None

    @staticmethod
    def _from_database_model(x: DatabaseInference):
        ip = (
            InferencePrompt._from_database_model(x.inference_prompt)
            if x.inference_prompt != None
            else None
        )
        ir = (
            InferenceResponse._from_database_model(x.inference_response)
            if x.inference_response != None
            else None
        )

        return Inference(
            id=x.id,
            result=x.result,
            created_at=x.created_at,
            updated_at=x.updated_at,
            task_id=x.task_id,
            task_name=x.task.name if x.task else None,
            conversation_id=x.conversation_id,
            inference_prompt=ip,
            inference_response=ir,
            inference_feedback=[
                InferenceFeedback.from_database_model(i) for i in x.inference_feedback
            ],
            user_id=x.user_id,
            model_name=x.model_name,
        )

    def _to_response_model(self):
        return ExternalInference(
            id=self.id,
            result=self.result,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            task_id=self.task_id,
            task_name=self.task_name,
            conversation_id=self.conversation_id,
            inference_prompt=self.inference_prompt._to_response_model(),
            inference_response=(
                self.inference_response._to_response_model()
                if self.inference_response != None
                else None
            ),
            inference_feedback=[i.to_response_model() for i in self.inference_feedback],
            user_id=self.user_id,
            model_name=self.model_name,
        )

    def _to_database_model(self):
        return DatabaseInference(
            id=self.id,
            result=self.result,
            created_at=self.created_at,
            updated_at=self.updated_at,
            task_id=self.task_id,
            conversation_id=self.conversation_id,
            inference_prompt=self.inference_prompt._to_database_model(),
            inference_response=(
                self.inference_response._to_database_model()
                if self.inference_response != None
                else None
            ),
            user_id=self.user_id,
            model_name=self.model_name,
        )


class ValidationRequest(BaseModel):
    prompt: Optional[str] = Field(
        description="User prompt to be used by GenAI Engine for validating.",
        default=None,
    )
    response: Optional[str] = Field(
        description="LLM Response to be validated by GenAI Engine",
        default=None,
    )
    context: Optional[str] = Field(
        description="Optional data provided as context for the validation.",
        default=None,
    )
    model_name: Optional[str] = Field(
        description="Model name to be used for the validation.",
        default=None,
    )
    tokens: Optional[List[str]] = Field(
        description="optional, not used currently",
        default=None,
    )
    token_likelihoods: Optional[List[str]] = Field(
        description="optional, not used currently",
        default=None,
    )

    def get_scoring_text(self):
        return self.response if self.response else self.prompt


class Document(BaseModel):
    id: str
    owner_id: str
    type: str
    name: str
    path: str
    is_global: bool

    @staticmethod
    def _from_database_model(x: DatabaseDocument):
        return Document(
            id=x.id,
            owner_id=x.owner_id,
            type=x.type,
            name=x.name,
            path=x.path,
            is_global=x.is_global,
        )

    def _to_response_model(self):
        return ExternalDocument(
            id=self.id,
            name=self.name,
            type=self.type,
            owner_id=self.owner_id,
        )


class Embedding(BaseModel):
    id: str
    document_id: str
    text: str
    seq_num: int
    embedding: List[float]
    owner_id: Optional[str] = None

    @classmethod
    def _from_database_model(cls, e: DatabaseEmbedding):
        return cls(
            id=e.id,
            document_id=e.document_id,
            text=e.text,
            seq_num=e.seq_num,
            embedding=list(e.embedding),
            owner_id=e.documents.owner_id,
        )

    def _to_reference_database_model(
        self,
        inference_id: str,
    ) -> DatabaseEmbeddingReference:
        return DatabaseEmbeddingReference(
            id=str(uuid.uuid4()),
            inference_id=inference_id,
            embedding_id=self.id,
        )

    def _to_response_model(self) -> ChatDocumentContext:
        return ChatDocumentContext(
            id=self.document_id,
            seq_num=self.seq_num,
            context=self.text,
        )


class AugmentedRetrieval(BaseModel):
    messages: List[str] = []
    embeddings: List[Embedding] = []

    def prompts_to_str(self) -> str:
        """converts the prompt templates to a string"""
        return "\n".join(self.messages)


class User(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list[AuthUserRole]

    @staticmethod
    def _from_database_model(user: DatabaseUser):
        return User(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    def _to_response_model(self) -> UserResponse:
        return UserResponse(
            id=self.id,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            # For now, sanitize non-genai-engine defined roles
            roles=[
                role
                for role in self.roles
                if role.name
                in [
                    constants.TASK_ADMIN,
                    constants.CHAT_USER,
                ]
            ],
        )

    def get_role_names_set(self) -> set[str]:
        return set([role.name.upper() for role in self.roles])


class DocumentStorageConfiguration(BaseModel):
    document_storage_environment: DocumentStorageEnvironment
    connection_string: Optional[str] = None
    container_name: Optional[str] = None
    bucket_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None

    def _to_response_model(self):
        return DocumentStorageConfigurationResponse(
            storage_environment=self.document_storage_environment,
            bucket_name=self.bucket_name,
            container_name=self.container_name,
            assumable_role_arn=self.assumable_role_arn,
        )


class ApplicationConfiguration(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[DocumentStorageConfiguration] = None
    max_llm_rules_per_task_count: int

    @staticmethod
    def _from_database_model(configs: List[DatabaseApplicationConfiguration]):
        doc_storage = None
        max_llm_rules_per_task_count = constants.DEFAULT_MAX_LLM_RULES_PER_TASK
        config_dict = {c.name: c.value for c in configs}

        if ApplicationConfigurations.DOCUMENT_STORAGE_ENV in config_dict:
            storage_env_config = config_if_exists(
                ApplicationConfigurations.DOCUMENT_STORAGE_ENV,
                configs,
            )
            doc_storage = DocumentStorageConfiguration(
                document_storage_environment=storage_env_config,
            )

            container_name_config = config_if_exists(
                ApplicationConfigurations.DOCUMENT_STORAGE_CONTAINER_NAME,
                configs,
            )
            if container_name_config is not None:
                doc_storage.container_name = container_name_config

            connection_string_config = config_if_exists(
                ApplicationConfigurations.DOCUMENT_STORAGE_CONNECTION_STRING,
                configs,
            )
            if connection_string_config is not None:
                doc_storage.connection_string = connection_string_config

            bucket_name_config = config_if_exists(
                ApplicationConfigurations.DOCUMENT_STORAGE_BUCKET_NAME,
                configs,
            )
            if bucket_name_config is not None:
                doc_storage.bucket_name = bucket_name_config

            role_arn_config = config_if_exists(
                ApplicationConfigurations.DOCUMENT_STORAGE_ROLE_ARN,
                configs,
            )
            if role_arn_config is not None:
                doc_storage.assumable_role_arn = role_arn_config

        if ApplicationConfigurations.MAX_LLM_RULES_PER_TASK_COUNT in config_dict:
            max_llm_rules_per_task_count = int(
                config_if_exists(
                    ApplicationConfigurations.MAX_LLM_RULES_PER_TASK_COUNT,
                    configs,
                ),
            )
        return ApplicationConfiguration(
            chat_task_id=config_if_exists(
                ApplicationConfigurations.CHAT_TASK_ID,
                configs,
            ),
            document_storage_configuration=doc_storage,
            max_llm_rules_per_task_count=max_llm_rules_per_task_count,
        )

    def _to_response_model(self):
        return ApplicationConfigurationResponse(
            chat_task_id=self.chat_task_id,
            document_storage_configuration=(
                self.document_storage_configuration._to_response_model()
                if self.document_storage_configuration is not None
                else None
            ),
            max_llm_rules_per_task_count=self.max_llm_rules_per_task_count,
        )


class ApiKey(BaseModel):
    id: str
    key: Optional[str] = None
    key_hash: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    deactivated_at: Optional[datetime] = None
    roles: list[str] = [constants.TASK_ADMIN]

    @staticmethod
    def _from_database_model(api_key: DatabaseApiKey):
        return ApiKey(
            id=api_key.id,
            key_hash=api_key.key_hash,
            description=api_key.description,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            deactivated_at=api_key.deactivated_at,
            roles=api_key.roles,
        )

    def _to_response_model(self, message="") -> ApiKeyResponse:
        return ApiKeyResponse(
            id=self.id,
            key=self.key,
            description=self.description,
            is_active=self.is_active,
            created_at=self.created_at,
            deactivated_at=self.deactivated_at,
            message=message,
            roles=self.roles,
        )

    def set_key(self, key: str):
        self.key = key

    def get_user_representation(self) -> User:
        return User(
            id=self.id,
            email="",
            roles=[
                AuthUserRole(name=role, description="API Key user", composite=True)
                for role in self.roles
            ],
        )


class Span(TokenCountCostSchema):
    id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    span_kind: Optional[str] = None
    span_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    status_code: str = "Unset"
    raw_data: dict
    created_at: datetime
    updated_at: datetime
    metric_results: Optional[List[MetricResult]] = None

    @property
    def input_content(self) -> Optional[str]:
        """Get input value from span attributes using OpenInference conventions.

        Extracts from raw_data.attributes.input.value per OpenInference semantic conventions.
        Uses get_nested_value for safe nested dictionary access.
        Converts dicts/lists to JSON strings to ensure string return type.
        """
        value = trace_utils.get_nested_value(
            self.raw_data,
            "attributes.input.value",
            default=None,
        )
        if value is None:
            return None
        try:
            return trace_utils.value_to_string(value)
        except Exception:
            return None

    @property
    def output_content(self) -> Optional[str]:
        """Get output value from span attributes using OpenInference conventions.

        Extracts from raw_data.attributes.output.value per OpenInference semantic conventions.
        Uses get_nested_value for safe nested dictionary access.
        Converts dicts/lists to JSON strings to ensure string return type.
        """
        value = trace_utils.get_nested_value(
            self.raw_data,
            "attributes.output.value",
            default=None,
        )
        if value is None:
            return None
        try:
            return trace_utils.value_to_string(value)
        except Exception:
            return None

    @staticmethod
    def _from_database_model(db_span: DatabaseSpan) -> "Span":
        return Span(
            id=db_span.id,
            trace_id=db_span.trace_id,
            span_id=db_span.span_id,
            parent_span_id=db_span.parent_span_id,
            span_kind=db_span.span_kind,
            span_name=db_span.span_name,
            start_time=db_span.start_time,
            end_time=db_span.end_time,
            task_id=db_span.task_id,
            session_id=db_span.session_id,
            user_id=db_span.user_id,
            status_code=db_span.status_code,
            raw_data=db_span.raw_data,
            prompt_token_count=db_span.prompt_token_count,
            completion_token_count=db_span.completion_token_count,
            total_token_count=db_span.total_token_count,
            prompt_token_cost=db_span.prompt_token_cost,
            completion_token_cost=db_span.completion_token_cost,
            total_token_cost=db_span.total_token_cost,
            created_at=db_span.created_at,
            updated_at=db_span.updated_at,
            metric_results=[
                MetricResult._from_database_model(m)
                for m in (db_span.metric_results or [])
            ],
        )

    def _to_database_model(self) -> DatabaseSpan:
        return DatabaseSpan(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_kind=self.span_kind,
            span_name=self.span_name,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            session_id=self.session_id,
            user_id=self.user_id,
            status_code=self.status_code,
            raw_data=self.raw_data,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def _to_response_model(self) -> "SpanWithMetricsResponse":
        return SpanWithMetricsResponse(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_kind=self.span_kind,
            span_name=self.span_name,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            session_id=self.session_id,
            user_id=self.user_id,
            status_code=self.status_code,
            raw_data=self.raw_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
            input_content=self.input_content,
            output_content=self.output_content,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
            metric_results=[
                result._to_response_model() for result in (self.metric_results or [])
            ],
        )

    def _to_nested_metrics_response_model(
        self,
        children: Optional[List["NestedSpanWithMetricsResponse"]] = None,
    ) -> "NestedSpanWithMetricsResponse":
        return NestedSpanWithMetricsResponse(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_kind=self.span_kind,
            span_name=self.span_name,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            session_id=self.session_id,
            user_id=self.user_id,
            status_code=self.status_code,
            raw_data=self.raw_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
            input_content=self.input_content,
            output_content=self.output_content,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
            metric_results=[
                result._to_response_model() for result in (self.metric_results or [])
            ],
            children=children or [],
        )

    def _to_metadata_response_model(self) -> SpanMetadataResponse:
        """Convert to lightweight metadata response"""
        duration_ms = calculate_duration_ms(self.start_time, self.end_time)
        return SpanMetadataResponse(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_kind=self.span_kind,
            span_name=self.span_name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=duration_ms,
            task_id=self.task_id,
            session_id=self.session_id,
            user_id=self.user_id,
            status_code=self.status_code,
            created_at=self.created_at,
            updated_at=self.updated_at,
            input_content=self.input_content,
            output_content=self.output_content,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
        )

    @staticmethod
    def from_span_data(span_data: dict) -> "Span":
        """Create a Span from raw span data received from OpenTelemetry"""
        return Span(
            id=str(uuid.uuid4()),
            trace_id=span_data["trace_id"],
            span_id=span_data["span_id"],
            parent_span_id=span_data.get("parent_span_id"),
            span_kind=span_data.get("span_kind"),
            span_name=span_data.get("span_name"),
            start_time=span_data["start_time"],
            end_time=span_data["end_time"],
            task_id=span_data["task_id"],
            session_id=span_data.get("session_id"),
            user_id=span_data.get("user_id"),
            status_code=span_data.get("status_code", "Unset"),
            raw_data=span_data["raw_data"],
            prompt_token_count=span_data.get("prompt_token_count"),
            completion_token_count=span_data.get("completion_token_count"),
            total_token_count=span_data.get("total_token_count"),
            prompt_token_cost=span_data.get("prompt_token_cost"),
            completion_token_cost=span_data.get("completion_token_cost"),
            total_token_cost=span_data.get("total_token_cost"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metric_results=[
                MetricResult._from_database_model(m)
                for m in span_data.get("metric_results", [])
            ],
        )


class OrderedClaim(BaseModel):
    index_number: int
    text: str


class SessionMetadata(TokenCountCostSchema):
    """Internal session metadata representation"""

    session_id: str
    task_id: str
    user_id: Optional[str] = None
    trace_ids: list[str]
    span_count: int
    earliest_start_time: datetime
    latest_end_time: datetime

    def _to_metadata_response_model(self) -> SessionMetadataResponse:
        """Convert to API response model"""
        duration_ms = calculate_duration_ms(
            self.earliest_start_time,
            self.latest_end_time,
        )
        return SessionMetadataResponse(
            session_id=self.session_id,
            task_id=self.task_id,
            user_id=self.user_id,
            trace_ids=self.trace_ids,
            trace_count=len(self.trace_ids),
            span_count=self.span_count,
            earliest_start_time=self.earliest_start_time,
            latest_end_time=self.latest_end_time,
            duration_ms=duration_ms,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
        )


class TraceUserMetadata(TokenCountCostSchema):
    """Internal trace user metadata representation"""

    user_id: str
    task_id: str
    session_ids: list[str]
    trace_ids: list[str]
    span_count: int
    earliest_start_time: datetime
    latest_end_time: datetime

    def _to_metadata_response_model(self) -> TraceUserMetadataResponse:
        """Convert to API response model"""
        return TraceUserMetadataResponse(
            user_id=self.user_id,
            task_id=self.task_id,
            session_ids=self.session_ids,
            session_count=len(self.session_ids),
            trace_ids=self.trace_ids,
            trace_count=len(self.trace_ids),
            span_count=self.span_count,
            earliest_start_time=self.earliest_start_time,
            latest_end_time=self.latest_end_time,
            prompt_token_count=self.prompt_token_count,
            completion_token_count=self.completion_token_count,
            total_token_count=self.total_token_count,
            prompt_token_cost=self.prompt_token_cost,
            completion_token_cost=self.completion_token_cost,
            total_token_cost=self.total_token_cost,
        )


def config_if_exists(key: str, configs: List[DatabaseApplicationConfiguration]):
    configs = {c.name: c.value for c in configs}
    if key in configs:
        return configs[key]
    else:
        return None


class FloatRangeFilter(BaseModel):
    value: float
    operator: ComparisonOperatorEnum


class TraceQuerySchema(BaseModel):
    task_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Task IDs to filter on. At least one is required.",
    )
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
    tool_name: Optional[str] = Field(
        None,
        description="Return only results with this tool name.",
    )
    span_types: Optional[list[str]] = Field(
        None,
        description="Span types to filter on. Optional.",
    )
    tool_selection: Optional[ToolClassEnum] = None
    tool_usage: Optional[ToolClassEnum] = None
    query_relevance_filters: Optional[list[FloatRangeFilter]] = None
    response_relevance_filters: Optional[list[FloatRangeFilter]] = None
    trace_duration_filters: Optional[list[FloatRangeFilter]] = None
    user_ids: Optional[list[str]] = Field(
        None,
        description="User IDs to filter on. Optional.",
    )

    @staticmethod
    def _from_request_model(request: TraceQueryRequest) -> "TraceQuerySchema":
        def resolve_filters(prefix: str) -> Optional[list[FloatRangeFilter]]:
            filters = []
            for op in ComparisonOperatorEnum:
                attr_name = f"{prefix}_{op.value}"
                value = getattr(request, attr_name, None)
                if value is not None:
                    filters.append(FloatRangeFilter(value=value, operator=op))
            return filters if filters else None

        query_relevance = resolve_filters("query_relevance")
        response_relevance = resolve_filters("response_relevance")
        trace_duration = resolve_filters("trace_duration")

        return TraceQuerySchema(
            task_ids=request.task_ids,
            trace_ids=request.trace_ids,
            start_time=request.start_time,
            end_time=request.end_time,
            tool_name=request.tool_name,
            span_types=request.span_types,
            tool_selection=request.tool_selection,
            tool_usage=request.tool_usage,
            query_relevance_filters=query_relevance,
            response_relevance_filters=response_relevance,
            trace_duration_filters=trace_duration,
        )


class Dataset(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    description: Optional[str]
    metadata: Optional[dict]
    latest_version_number: Optional[int]

    def to_response_model(self) -> DatasetResponse:
        return DatasetResponse(
            id=self.id,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            name=self.name,
            description=self.description,
            metadata=self.metadata,
            latest_version_number=self.latest_version_number,
        )

    def _to_database_model(self) -> DatabaseDataset:
        return DatabaseDataset(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            name=self.name,
            description=self.description,
            dataset_metadata=self.metadata,
            latest_version_number=self.latest_version_number,
        )

    @staticmethod
    def _from_request_model(request: NewDatasetRequest) -> "Dataset":
        curr_time = datetime.now()
        return Dataset(
            id=uuid.uuid4(),
            created_at=curr_time,
            updated_at=curr_time,
            name=request.name,
            description=request.description,
            metadata=request.metadata,
            latest_version_number=None,
        )

    @staticmethod
    def _from_database_model(db_dataset: DatabaseDataset) -> "Dataset":
        return Dataset(
            id=db_dataset.id,
            created_at=db_dataset.created_at,
            updated_at=db_dataset.updated_at,
            name=db_dataset.name,
            description=db_dataset.description,
            metadata=db_dataset.dataset_metadata,
            latest_version_number=db_dataset.latest_version_number,
        )


class DatasetVersionRowColumnItem(BaseModel):
    column_name: str
    column_value: str

    @staticmethod
    def _from_request_model(
        request: NewDatasetVersionRowColumnItemRequest,
    ) -> "DatasetVersionRowColumnItem":
        return DatasetVersionRowColumnItem(
            column_name=request.column_name,
            column_value=request.column_value,
        )


class DatasetVersionRow(BaseModel):
    id: uuid.UUID
    data: list[DatasetVersionRowColumnItem]
    created_at: datetime

    @staticmethod
    def _from_database_model(
        db_dataset_version_row: DatabaseDatasetVersionRow,
    ) -> "DatasetVersionRow":
        return DatasetVersionRow(
            id=db_dataset_version_row.id,
            data=[
                DatasetVersionRowColumnItem(column_name=key, column_value=value)
                for key, value in db_dataset_version_row.data.items()
            ],
            created_at=db_dataset_version_row.created_at,
        )


class DatasetVersionMetadata(BaseModel):
    version_number: int
    created_at: datetime
    dataset_id: uuid.UUID
    column_names: List[str]

    @staticmethod
    def _calculate_column_names(rows: List[DatasetVersionRow]) -> List[str]:
        """Returns list of all column names in the dataset version.
        :param:rows: list of all rows in the version
        """
        column_names = set()
        for row in rows:
            for col_item in row.data:
                column_names.add(col_item.column_name)
        return list(column_names)

    @staticmethod
    def _from_database_model(
        db_dataset_version: DatabaseDatasetVersion,
    ) -> "DatasetVersionMetadata":
        return DatasetVersionMetadata(
            version_number=db_dataset_version.version_number,
            created_at=db_dataset_version.created_at,
            dataset_id=db_dataset_version.dataset_id,
            column_names=db_dataset_version.column_names,
        )

    def to_response_model(self) -> DatasetVersionMetadataResponse:
        return DatasetVersionMetadataResponse(
            version_number=self.version_number,
            created_at=_serialize_datetime(self.created_at),
            dataset_id=self.dataset_id,
            column_names=self.column_names,
        )


class DatasetVersion(DatasetVersionMetadata):
    rows: List[DatasetVersionRow]
    page: int = Field(description="The current page number for the included rows.")
    page_size: int = Field(description="The number of rows per page.")
    total_pages: int = Field(description="The total number of pages.")
    total_count: int = Field(
        description="The total number of rows in the dataset version.",
    )

    @staticmethod
    def _from_request_model(
        dataset_id: uuid.UUID,
        latest_version: Optional[DatabaseDatasetVersion],
        new_version: NewDatasetVersionRequest,
    ) -> "DatasetVersion":
        """
        :param: dataset_id: dataset the version belongs to.
        :param: latest_version: DatabaseBDatasetVersion of the latest version of the dataset before the new one.
        :param: new_version: NewDatasetVersionRequest with the diff changes for the new dataset version
        """
        # assemble data rows
        ids_rows_to_update = set(row.id for row in new_version.rows_to_update)
        if latest_version is not None:
            unchanged_rows = [
                DatasetVersionRow._from_database_model(db_row)
                for db_row in latest_version.version_rows
                if db_row.id not in new_version.rows_to_delete
                and db_row.id not in ids_rows_to_update
            ]
            existing_row_id_to_row = {
                db_row.id: db_row for db_row in latest_version.version_rows
            }
        elif latest_version is None and new_version.rows_to_update:
            raise HTTPException(
                status_code=400,
                detail="Cannot specify rows to update if there is no previous version of the dataset.",
            )
        else:
            unchanged_rows = []
            existing_row_id_to_row = {}

        # validate updated rows do exist in the last version while creating updated_rows object
        updated_rows = []
        for updated_row in new_version.rows_to_update:
            if updated_row.id not in existing_row_id_to_row:
                raise HTTPException(
                    status_code=404,
                    detail="At least one row specified to update does not exist.",
                )
            else:
                updated_rows.append(
                    DatasetVersionRow(
                        id=updated_row.id,
                        data=[
                            DatasetVersionRowColumnItem._from_request_model(row_item)
                            for row_item in updated_row.data
                        ],
                        created_at=existing_row_id_to_row[updated_row.id].created_at,
                    ),
                )
        curr_time = datetime.now()
        new_rows = [
            DatasetVersionRow(
                id=uuid.uuid4(),
                data=[
                    DatasetVersionRowColumnItem._from_request_model(row_item)
                    for row_item in new_row.data
                ],
                created_at=curr_time,
            )
            for new_row in new_version.rows_to_add
        ]
        all_rows = unchanged_rows + new_rows + updated_rows

        if len(all_rows) > MAX_DATASET_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"Total number of rows {len(all_rows)} exceeds max allowed length, {MAX_DATASET_ROWS}.",
            )

        return DatasetVersion(
            version_number=latest_version.version_number + 1 if latest_version else 1,
            created_at=curr_time,
            dataset_id=dataset_id,
            rows=all_rows,
            page=0,
            page_size=len(all_rows),
            total_pages=1,
            total_count=len(all_rows),
            column_names=DatasetVersionMetadata._calculate_column_names(all_rows),
        )

    def _to_database_model(self) -> DatabaseDatasetVersion:
        if self.page_size != self.total_count:
            raise ValueError(
                "Should not be using the database model without all version rows present.",
            )

        return DatabaseDatasetVersion(
            version_number=self.version_number,
            dataset_id=self.dataset_id,
            created_at=self.created_at,
            version_rows=[
                DatabaseDatasetVersionRow(
                    version_number=self.version_number,
                    dataset_id=self.dataset_id,
                    id=version_row.id,
                    data={
                        row_item.column_name: row_item.column_value
                        for row_item in version_row.data
                    },
                    created_at=version_row.created_at,
                )
                for version_row in self.rows
            ],
            column_names=self.column_names,
        )

    def to_response_model(self) -> DatasetVersionResponse:
        return DatasetVersionResponse(
            version_number=self.version_number,
            dataset_id=self.dataset_id,
            created_at=_serialize_datetime(self.created_at),
            rows=[
                DatasetVersionRowResponse(
                    id=row.id,
                    data=[
                        DatasetVersionRowColumnItemResponse(
                            column_name=row_item.column_name,
                            column_value=row_item.column_value,
                        )
                        for row_item in row.data
                    ],
                    created_at=_serialize_datetime(self.created_at),
                )
                for row in self.rows
            ],
            page=self.page,
            page_size=self.page_size,
            total_pages=self.total_pages,
            total_count=self.total_count,
            column_names=self.column_names,
        )

    @staticmethod
    def _from_database_model(
        db_dataset_version: DatabaseDatasetVersion,
        total_count: int,
        pagination_params: PaginationParameters,
    ) -> "DatasetVersion":
        return DatasetVersion(
            version_number=db_dataset_version.version_number,
            created_at=db_dataset_version.created_at,
            dataset_id=db_dataset_version.dataset_id,
            rows=[
                DatasetVersionRow._from_database_model(db_row)
                for db_row in db_dataset_version.version_rows
            ],
            page=pagination_params.page,
            page_size=pagination_params.page_size,
            total_pages=(
                pagination_params.calculate_total_pages(total_count)
                if total_count > 0
                else 0
            ),
            total_count=total_count,
            column_names=db_dataset_version.column_names,
        )


class ListDatasetVersions(BaseModel):
    versions: List[DatasetVersionMetadata]
    page: int = Field(description="The current page number for the included versions.")
    page_size: int = Field(description="The number of versions per page.")
    total_pages: int = Field(description="The total number of pages.")
    total_count: int = Field(
        description="The total number of versions for the dataset.",
    )

    @staticmethod
    def _from_database_model(
        db_dataset_versions: List[DatabaseDatasetVersion],
        total_count: int,
        pagination_params: PaginationParameters,
    ) -> "ListDatasetVersions":
        return ListDatasetVersions(
            versions=[
                DatasetVersionMetadata._from_database_model(db_dataset_version)
                for db_dataset_version in db_dataset_versions
            ],
            page=pagination_params.page,
            page_size=pagination_params.page_size,
            total_pages=(
                pagination_params.calculate_total_pages(total_count)
                if total_count > 0
                else 0
            ),
            total_count=total_count,
        )

    def to_response_model(self) -> ListDatasetVersionsResponse:
        return ListDatasetVersionsResponse(
            versions=[version.to_response_model() for version in self.versions],
            page=self.page,
            page_size=self.page_size,
            total_pages=self.total_pages,
            total_count=self.total_count,
        )


class ApiKeyRagProviderSecretValue(BaseModel):
    api_key: SecretStr

    def _to_sensitive_dict(self) -> dict[str, str]:
        """Returns dict with all fields in the object. Secrets will be revealed as strings.
        WARNING: should be very infrequently used. The secret will need to be revealed in a dictionary to store
        its value in the database.
        """
        model_dict = vars(self)
        model_dict["api_key"] = model_dict["api_key"].get_secret_value()
        return model_dict


class ApiKeyRagProviderSecret(BaseModel):
    id: str
    name: str
    value: ApiKeyRagProviderSecretValue
    secret_type: SecretType
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _to_database_model(
        provider_config: "RagProviderConfiguration",
    ) -> DatabaseSecretStorage:
        api_key_secret_id = uuid.uuid4()
        curr_time = datetime.now()
        secret_value = ApiKeyRagProviderSecretValue(
            api_key=provider_config.authentication_config.api_key,
        )
        return DatabaseSecretStorage(
            id=str(api_key_secret_id),
            name=f"api_key_rag_provider_config_{provider_config.id}",
            value=secret_value._to_sensitive_dict(),
            secret_type=SecretType.RAG_PROVIDER,
            created_at=curr_time,
            updated_at=curr_time,
        )

    @staticmethod
    def _from_database_model(
        db_secret: DatabaseSecretStorage,
    ) -> "ApiKeyRagProviderSecret":
        return ApiKeyRagProviderSecret(
            id=db_secret.id,
            name=db_secret.name,
            value=ApiKeyRagProviderSecretValue.model_validate(db_secret.value),
            secret_type=SecretType.RAG_PROVIDER,
            created_at=db_secret.created_at,
            updated_at=db_secret.updated_at,
        )


class ApiKeyRagAuthenticationConfig(BaseModel):
    authentication_method: Literal[
        RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    ] = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    api_key: SecretStr
    host_url: Url
    rag_provider: RagAPIKeyAuthenticationProviderEnum

    @staticmethod
    def _from_request_model(
        request: ApiKeyRagAuthenticationConfigRequest,
    ) -> "ApiKeyRagAuthenticationConfig":
        return ApiKeyRagAuthenticationConfig(
            authentication_method=request.authentication_method,
            api_key=request.api_key,
            host_url=request.host_url,
            rag_provider=request.rag_provider,
        )

    @staticmethod
    def _from_database_model(
        db_config: "DatabaseApiKeyRagProviderConfiguration",
    ) -> "ApiKeyRagAuthenticationConfig":
        api_key_secret = ApiKeyRagProviderSecret._from_database_model(db_config.api_key)
        return ApiKeyRagAuthenticationConfig(
            authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
            api_key=api_key_secret.value.api_key,
            host_url=Url(db_config.host_url),
            rag_provider=db_config.rag_provider,
        )

    def to_response_model(self) -> ApiKeyRagAuthenticationConfigResponse:
        return ApiKeyRagAuthenticationConfigResponse(
            authentication_method=self.authentication_method,
            host_url=self.host_url,
            rag_provider=self.rag_provider,
        )

    @staticmethod
    def _to_database_model(
        provider_config: "RagProviderConfiguration",
    ) -> DatabaseApiKeyRagProviderConfiguration:
        api_key_secret_db = ApiKeyRagProviderSecret._to_database_model(provider_config)
        return DatabaseApiKeyRagProviderConfiguration(
            id=provider_config.id,
            authentication_method=provider_config.authentication_config.authentication_method,
            task_id=provider_config.task_id,
            name=provider_config.name,
            description=provider_config.description,
            created_at=provider_config.created_at,
            updated_at=provider_config.updated_at,
            api_key=api_key_secret_db,
            api_key_secret_id=api_key_secret_db.id,
            host_url=str(provider_config.authentication_config.host_url),
            rag_provider=provider_config.authentication_config.rag_provider,
        )


RagAuthenticationConfigTypes = Union[ApiKeyRagAuthenticationConfig]


class RagProviderConfiguration(BaseModel):
    id: uuid.UUID
    task_id: str
    authentication_config: RagAuthenticationConfigTypes
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _from_request_model(
        task_id: str,
        request: RagProviderConfigurationRequest,
    ) -> "RagProviderConfiguration":
        if isinstance(
            request.authentication_config,
            ApiKeyRagAuthenticationConfigRequest,
        ):
            config = ApiKeyRagAuthenticationConfig._from_request_model(
                request.authentication_config,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Authentication method {type(request.authentication_config)} is not supported.",
            )

        return RagProviderConfiguration(
            id=uuid.uuid4(),
            task_id=task_id,
            authentication_config=config,
            description=request.description,
            name=request.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @staticmethod
    def _from_database_model(db_config) -> "RagProviderConfiguration":
        """Create from polymorphic database model"""
        if (
            db_config.authentication_method
            == RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
        ):
            # This should be a DatabaseApiKeyRagProviderConfiguration
            auth_config = ApiKeyRagAuthenticationConfig._from_database_model(db_config)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Unsupported authentication method: {db_config.authentication_method}",
            )

        return RagProviderConfiguration(
            id=db_config.id,
            task_id=db_config.task_id,
            authentication_config=auth_config,
            name=db_config.name,
            description=db_config.description,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at,
        )

    def to_response_model(self) -> RagProviderConfigurationResponse:
        return RagProviderConfigurationResponse(
            authentication_config=self.authentication_config.to_response_model(),
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
        )

    def _to_database_model(self) -> DatabaseRagProviderAuthenticationConfigurationTypes:
        if isinstance(self.authentication_config, ApiKeyRagAuthenticationConfig):
            return ApiKeyRagAuthenticationConfig._to_database_model(self)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Unsupported authentication method: {self.authentication_method}",
            )

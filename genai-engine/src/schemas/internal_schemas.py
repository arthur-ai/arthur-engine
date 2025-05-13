import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from opentelemetry import trace
from pydantic import BaseModel, Field
from schemas.common_schemas import (
    AuthUserRole,
    ExampleConfig,
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from schemas.enums import (
    ApplicationConfigurations,
    DocumentStorageEnvironment,
    InferenceFeedbackTarget,
    PIIEntityTypes,
    RuleDataType,
    RuleResultEnum,
    RuleScope,
    RuleScoringMethod,
    RuleType,
    ToxicityViolationType,
)
from schemas.request_schemas import NewRuleRequest, NewTaskRequest, NewMetricRequest
from schemas.response_schemas import (
    ApiKeyResponse,
    ApplicationConfigurationResponse,
    BaseDetailsResponse,
    ChatDocumentContext,
    DocumentStorageConfigurationResponse,
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
    PIIDetailsResponse,
    PIIEntitySpanResponse,
    RegexDetailsResponse,
    RegexSpanResponse,
    RuleResponse,
    SpanResponse,
    TaskResponse,
    ToxicityDetailsResponse,
    UserResponse,
    MetricResponse,
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

from db_models.db_models import (
    DatabaseApiKey,
    DatabaseApplicationConfiguration,
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
    DatabasePIIEntity,
    DatabasePromptRuleResult,
    DatabaseRegexEntity,
    DatabaseResponseRuleResult,
    DatabaseRule,
    DatabaseRuleResultDetail,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTaskToRules,
    DatabaseToxicityScore,
    DatabaseUser,
    DatabaseMetric,
)

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


class Task(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    rule_links: Optional[List[TaskToRuleLink]] = None

    @staticmethod
    def _from_request_model(x: NewTaskRequest):
        return Task(
            id=str(uuid.uuid4()),
            name=x.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @staticmethod
    def _from_database_model(x: DatabaseTask):
        return Task(
            id=x.id,
            name=x.name,
            created_at=x.created_at,
            updated_at=x.updated_at,
            rule_links=[
                TaskToRuleLink._from_database_model(link) for link in x.rule_links
            ],
        )

    def _to_database_model(self):
        return DatabaseTask(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def _to_response_model(self):
        response_rules = []
        for link in self.rule_links:
            response_rule: RuleResponse = link.rule._to_response_model()
            response_rule.enabled = link.enabled
            response_rules.append(response_rule)

        return TaskResponse(
            id=self.id,
            name=self.name,
            created_at=_serialize_datetime(self.created_at),
            updated_at=_serialize_datetime(self.updated_at),
            rules=response_rules,
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


class Span(BaseModel):
    id: str
    trace_id: str
    span_id: str
    start_time: datetime
    end_time: datetime
    task_id: Optional[str] = None
    raw_data: dict
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _from_database_model(db_span: DatabaseSpan) -> "Span":
        return Span(
            id=db_span.id,
            trace_id=db_span.trace_id,
            span_id=db_span.span_id,
            start_time=db_span.start_time,
            end_time=db_span.end_time,
            task_id=db_span.task_id,
            raw_data=db_span.raw_data,
            created_at=db_span.created_at,
            updated_at=db_span.updated_at,
        )

    def _to_database_model(self) -> DatabaseSpan:
        return DatabaseSpan(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            raw_data=self.raw_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def _to_response_model(self) -> SpanResponse:
        return SpanResponse(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            raw_data=self.raw_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def from_span_data(span_data: dict, user_id: str) -> "Span":
        """Create a Span from raw span data received from OpenTelemetry"""
        return Span(
            id=str(uuid.uuid4()),
            trace_id=span_data["trace_id"],
            span_id=span_data["span_id"],
            start_time=span_data["start_time"],
            end_time=span_data["end_time"],
            task_id=span_data["task_id"],
            raw_data=span_data["raw_data"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class Metric(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    metric_type: str
    metric_name: str
    metric_metadata: str

    @staticmethod
    def _from_request_model(request: NewMetricRequest) -> "Metric":
        return Metric(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metric_type=request.metric_type,
            metric_name=request.metric_name,
            metric_metadata=request.metric_metadata,
        )
    
    def _to_database_model(self) -> DatabaseMetric:
        return DatabaseMetric(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metric_type=self.metric_type,
            metric_name=self.metric_name,
            metric_metadata=self.metric_metadata,
        )
    
    def _to_response_model(self) -> MetricResponse:
        return MetricResponse(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metric_type=self.metric_type,
            metric_name=self.metric_name,
            metric_metadata=self.metric_metadata,
        )


class OrderedClaim(BaseModel):
    index_number: int
    text: str


def config_if_exists(key: str, configs: List[DatabaseApplicationConfiguration]):
    configs = {c.name: c.value for c in configs}
    if key in configs:
        return configs[key]
    else:
        return None

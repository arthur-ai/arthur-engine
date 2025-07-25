from datetime import datetime
from typing import List, Optional

import pgvector.sqlalchemy
import sqlalchemy.types as types
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from db_models.custom_types import RoleType
from utils import constants
from utils.utils import get_env_var

OUTPUT_DIMENSION_SIZE_ADA_002 = 1536


class CustomerDataString(types.TypeDecorator):
    """Some customers don't want us storing any of their input data, use this type instead of string to overwrite any content on SQL insert generation"""

    impl = types.String

    def process_bind_param(self, value, _):
        persistence = get_env_var(constants.GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR)
        if persistence == "disabled":
            return ""
        return value


class IsArchivable(object):
    """Mixin that identifies a class as being archivable"""

    archived = Column(Boolean, nullable=False, default=False)


# declarative base class
class Base(DeclarativeBase):
    pass


class DatabaseTask(Base, IsArchivable):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    is_agentic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rule_links: Mapped[List["DatabaseTaskToRules"]] = relationship(
        back_populates="task",
        lazy="joined",
    )
    metric_links: Mapped[List["DatabaseTaskToMetrics"]] = relationship(
        back_populates="task",
        lazy="joined",
    )


class DatabaseTaskToRules(Base):
    __tablename__ = "tasks_to_rules"
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
        primary_key=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rules.id"),
        index=True,
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    task: Mapped["DatabaseTask"] = relationship(back_populates="rule_links")
    rule: Mapped["DatabaseRule"] = relationship(lazy="joined")


class DatabaseRule(Base, IsArchivable):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    prompt_enabled: Mapped[bool] = mapped_column(Boolean)
    response_enabled: Mapped[bool] = mapped_column(Boolean)
    scoring_method: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    rule_data: Mapped[List["DatabaseRuleData"]] = relationship(lazy="joined")


class DatabaseRuleData(Base):
    __tablename__ = "rule_data"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("rules.id"), index=True)
    data_type: Mapped[str] = mapped_column(String)
    data: Mapped[str] = mapped_column(String)


class DatabaseInference(Base):
    __tablename__ = "inferences"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    result: Mapped[str] = mapped_column(String)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
        nullable=True,
    )
    conversation_id: Mapped[str] = mapped_column(String, index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    inference_prompt: Mapped["DatabaseInferencePrompt"] = relationship(lazy="joined")
    inference_response: Mapped["DatabaseInferenceResponse"] = relationship(
        lazy="joined",
    )
    inference_feedback: Mapped[List["DatabaseInferenceFeedback"]] = relationship(
        lazy="joined",
    )
    task: Mapped[DatabaseTask] = relationship(lazy="joined")

    __table_args__ = (
        Index(
            "idx_inferences_task_id_created_at",
            "task_id",
            "created_at",
        ),
    )


class DatabaseEmbeddingReference(Base):
    __tablename__ = "inference_embeddings"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    inference_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inferences.id"),
        index=True,
    )
    embedding_id: Mapped[str] = mapped_column(String, ForeignKey("embeddings.id"))
    embedding: Mapped["DatabaseEmbedding"] = relationship(
        "DatabaseEmbedding",
        cascade="all,delete",
        lazy="joined",
    )


class DatabaseInferencePrompt(Base):
    __tablename__ = "inference_prompts"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    inference_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inferences.id"),
        index=True,
        unique=True,
    )
    result: Mapped[str] = mapped_column(String)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    prompt_rule_results: Mapped[List["DatabasePromptRuleResult"]] = relationship(
        lazy="subquery",
    )
    content: Mapped["DatabaseInferencePromptContent"] = relationship(lazy="joined")
    tokens: Mapped[int] = mapped_column(Integer, nullable=True)


class DatabaseInferenceResponse(Base):
    __tablename__ = "inference_responses"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    inference_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inferences.id"),
        index=True,
        unique=True,
    )
    result: Mapped[str] = mapped_column(String)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    response_rule_results: Mapped[List["DatabaseResponseRuleResult"]] = relationship(
        lazy="subquery",
    )
    content: Mapped["DatabaseInferenceResponseContent"] = relationship(lazy="joined")
    tokens: Mapped[int] = mapped_column(Integer, nullable=True)


class DatabasePromptRuleResult(Base):
    __tablename__ = "prompt_rule_results"
    __table_args__ = (UniqueConstraint("inference_prompt_id", "rule_id"),)
    id: Mapped[str] = Column(String, primary_key=True, index=True)
    inference_prompt_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inference_prompts.id"),
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("rules.id"))
    rule_result: Mapped[str] = mapped_column(String)
    rule_details: Mapped["DatabaseRuleResultDetail"] = relationship(lazy="joined")
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    rule: Mapped["DatabaseRule"] = relationship(lazy="joined")
    UniqueConstraint("inference_prompt_id", "rule_id")


class DatabaseResponseRuleResult(Base):
    __tablename__ = "response_rule_results"
    __table_args__ = (UniqueConstraint("inference_response_id", "rule_id"),)
    id: Mapped[str] = Column(String, primary_key=True, index=True)
    inference_response_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inference_responses.id"),
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("rules.id"))
    rule_result: Mapped[str] = mapped_column(String)
    rule_details: Mapped["DatabaseRuleResultDetail"] = relationship(lazy="joined")
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    rule: Mapped["DatabaseRule"] = relationship(lazy="joined")
    UniqueConstraint("inference_response_id", "rule_id")


class DatabaseRuleResultDetail(Base):
    __tablename__ = "rule_result_details"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    prompt_rule_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_rule_results.id"),
        nullable=True,
    )
    response_rule_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("response_rule_results.id"),
        nullable=True,
    )
    score: Mapped[bool] = mapped_column(Boolean, nullable=True)
    message: Mapped[str] = mapped_column(String, nullable=True)
    claims: Mapped[List["DatabaseHallucinationClaim"]] = relationship(lazy="joined")
    pii_entities: Mapped[List["DatabasePIIEntity"]] = relationship(lazy="joined")
    toxicity_score: Mapped["DatabaseToxicityScore"] = relationship(lazy="joined")
    keyword_matches: Mapped[List["DatabaseKeywordEntity"]] = relationship(lazy="joined")
    regex_matches: Mapped[List["DatabaseRegexEntity"]] = relationship(lazy="joined")
    __table_args__ = (
        Index("ix_rule_result_details_prompt_rule_result_id", "prompt_rule_result_id"),
        Index(
            "ix_rule_result_details_response_rule_result_id",
            "response_rule_result_id",
        ),
    )


class DatabaseHallucinationClaim(Base):
    __tablename__ = "hallucination_claims"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    rule_result_detail_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rule_result_details.id"),
        index=True,
    )
    claim: Mapped[str] = mapped_column(CustomerDataString)
    valid: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(CustomerDataString)
    order_number: Mapped[int] = mapped_column(Integer, server_default=text("-1"))


class DatabasePIIEntity(Base):
    __tablename__ = "pii_entities"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    rule_result_detail_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rule_result_details.id"),
        index=True,
    )
    entity: Mapped[str] = mapped_column(String)
    span: Mapped[str] = mapped_column(CustomerDataString)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)


class DatabaseKeywordEntity(Base):
    __tablename__ = "keyword_matches"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    rule_result_detail_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rule_result_details.id"),
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String)


class DatabaseRegexEntity(Base):
    __tablename__ = "regex_matches"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    rule_result_detail_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rule_result_details.id"),
        index=True,
    )
    matching_text: Mapped[str] = mapped_column(CustomerDataString)
    # Nullable for past inferences before this feature that won't have this field populated
    pattern: Mapped[str] = mapped_column(String, nullable=True)


class DatabaseToxicityScore(Base):
    __tablename__ = "toxicity_scores"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    rule_result_detail_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rule_result_details.id"),
        index=True,
    )
    toxicity_score: Mapped[float] = mapped_column(Float)
    toxicity_violation_type: Mapped[str] = mapped_column(String)


# Store in seperate table as its TBD if this database will always hold the more sensitive customer data
class DatabaseInferencePromptContent(Base):
    __tablename__ = "inference_prompt_contents"
    __table_args__ = (UniqueConstraint("inference_prompt_id"),)
    inference_prompt_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inference_prompts.id"),
        primary_key=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(CustomerDataString)


# Store in seperate table as its TBD if this database will always hold the more sensitive customer data
class DatabaseInferenceResponseContent(Base):
    __tablename__ = "inference_response_contents"
    __table_args__ = (UniqueConstraint("inference_response_id"),)
    inference_response_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inference_responses.id"),
        primary_key=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(CustomerDataString)
    context: Mapped[str] = mapped_column(CustomerDataString, nullable=True)


class DatabaseDocument(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String)
    is_global: Mapped[bool] = mapped_column(Boolean)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    embeddings: Mapped[List["DatabaseEmbedding"]] = relationship(
        "DatabaseEmbedding",
        cascade="all,delete",
        back_populates="documents",
    )


class DatabaseEmbedding(Base):
    __tablename__ = "embeddings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id"),
        index=True,
    )
    text: Mapped[str] = mapped_column(String)
    seq_num: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[List[float]] = mapped_column(
        pgvector.sqlalchemy.Vector(OUTPUT_DIMENSION_SIZE_ADA_002),
    )
    documents = relationship("DatabaseDocument", back_populates="embeddings")


index = Index(
    "my_index",
    DatabaseEmbedding.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_l2_ops"},
)


class DatabaseApplicationConfiguration(Base):
    __tablename__ = "configurations"
    name: Mapped[str] = mapped_column(String, unique=True, primary_key=True)
    value: Mapped[str] = mapped_column(String)


class DatabaseUser(Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)


class DatabaseInferenceFeedback(Base):
    __tablename__ = "inference_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    inference_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inferences.id"),
        index=True,
    )
    target: Mapped[str] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())


class DatabaseApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key_hash: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    deactivated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, nullable=True)
    roles: Mapped[list[str]] = mapped_column(
        RoleType,
        server_default=text(f"'[\"{constants.DEFAULT_RULE_ADMIN}\"]'"),
        nullable=False,
    )

    def deactivate(self):
        self.is_active = False
        self.deactivated_at = datetime.now()


class DatabaseSpan(Base):
    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_span_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    span_kind: Mapped[str] = mapped_column(String, nullable=True)
    start_time: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, nullable=False)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=True,
        index=True,
    )
    raw_data: Mapped[dict] = mapped_column(postgresql.JSON, nullable=False)
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    updated_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    metric_results: Mapped[List["DatabaseMetricResult"]] = relationship(
        "DatabaseMetricResult",
        back_populates="span",
        lazy="joined",
    )


class DatabaseMetric(Base, IsArchivable):
    __tablename__ = "metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    metric_metadata: Mapped[str] = mapped_column(String)
    config: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class DatabaseTaskToMetrics(Base):
    __tablename__ = "tasks_to_metrics"
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
        primary_key=True,
    )
    metric_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("metrics.id"),
        index=True,
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    task: Mapped["DatabaseTask"] = relationship(back_populates="metric_links")
    metric: Mapped["DatabaseMetric"] = relationship(lazy="joined")


class DatabaseMetricResult(Base):
    __tablename__ = "metric_results"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    metric_type: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )  # JSON-serialized MetricScoreDetails
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    span_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("spans.id"),
        nullable=False,
        index=True,
    )
    metric_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("metrics.id"),
        nullable=False,
        index=True,
    )
    span: Mapped["DatabaseSpan"] = relationship(back_populates="metric_results")

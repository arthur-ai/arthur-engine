from datetime import datetime
from typing import List

import sqlalchemy.types as types
from db_models.custom_types import RoleType
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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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
    rule_links: Mapped[List["DatabaseTaskToRules"]] = relationship(
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

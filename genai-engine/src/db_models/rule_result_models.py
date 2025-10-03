from datetime import datetime
from typing import List

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, CustomerDataString


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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
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

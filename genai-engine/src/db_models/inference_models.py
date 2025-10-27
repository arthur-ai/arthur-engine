from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, CustomerDataString

if TYPE_CHECKING:
    from db_models.rule_result_models import (
        DatabasePromptRuleResult,
        DatabaseResponseRuleResult,
    )
    from db_models.task_models import DatabaseTask


class DatabaseInference(Base):
    __tablename__ = "inferences"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    result: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
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
    task: Mapped["DatabaseTask"] = relationship(lazy="joined")
    model_name: Mapped[str] = mapped_column(String, nullable=True)

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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    response_rule_results: Mapped[List["DatabaseResponseRuleResult"]] = relationship(
        lazy="subquery",
    )
    content: Mapped["DatabaseInferenceResponseContent"] = relationship(lazy="joined")
    tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str] = mapped_column(String, nullable=True)


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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())

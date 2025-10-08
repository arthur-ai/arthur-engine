from datetime import datetime
from typing import Optional

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base


class DatabaseAgenticPrompt(Base):
    """Database model for storing agentic prompts associated with tasks"""

    __tablename__ = "agentic_prompts"

    # Composite primary key: task_id + name
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)

    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String)
    model_provider: Mapped[str] = mapped_column(String)

    # Prompt Content - stored as JSON for flexibility
    messages: Mapped[dict] = mapped_column(JSON)
    tools: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tool_choice: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # LLM Parameters
    timeout: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stream: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_format: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    stop: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    presence_penalty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frequency_penalty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    logprobs: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    top_logprobs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    logit_bias: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    stream_options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    max_completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reasoning_effort: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    thinking: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Ensure name is unique within each task
    __table_args__ = (UniqueConstraint("task_id", "name", name="uq_task_prompt_name"),)

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="agentic_prompts")

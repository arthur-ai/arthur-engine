from datetime import datetime
from typing import List

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, IsArchivable


class DatabaseTask(Base, IsArchivable):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    is_agentic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rule_links: Mapped[List["DatabaseTaskToRules"]] = relationship(
        back_populates="task",
        lazy="joined",
    )
    metric_links: Mapped[List["DatabaseTaskToMetrics"]] = relationship(
        back_populates="task",
        lazy="joined",
    )
    agentic_prompts: Mapped[List["DatabaseAgenticPrompt"]] = relationship(
        back_populates="task",
        lazy="select",
    )
    llm_evals: Mapped[List["DatabaseLLMEval"]] = relationship(
        back_populates="task",
        lazy="select",
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

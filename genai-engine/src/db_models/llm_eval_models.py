from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base


class DatabaseLLMEval(Base):
    """Database model for storing llm evals associated with tasks"""

    __tablename__ = "llm_evals"

    # Composite primary key: task_id + name + version
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)

    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_provider: Mapped[str] = mapped_column(String, nullable=False)

    # Prompt Content - stored as JSON for flexibility
    instructions: Mapped[str] = mapped_column(String, nullable=False)
    variables: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        server_default="[]",
        default=list,
    )

    # Eval configurations
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
    )

    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="llm_evals")

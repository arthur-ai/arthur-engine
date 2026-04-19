import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, UUID, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseContinuousEvalTestRun(Base):
    __tablename__ = "continuous_eval_test_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    continuous_eval_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("continuous_evals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String, nullable=False)

    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

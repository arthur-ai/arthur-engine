import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text
from sqlalchemy.types import TIMESTAMP

from db_models.base import Base


class DatabaseOnboardingSubmission(Base):
    __tablename__ = "onboarding_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    form_variant: Mapped[str | None] = mapped_column(String, nullable=True)
    form_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

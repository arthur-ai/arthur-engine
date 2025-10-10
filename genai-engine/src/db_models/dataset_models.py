import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, UUID, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseDataset(Base):
    __tablename__ = "datasets"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    # metadata is a reserved sqlalchemy name so we'll use dataset_metadata
    dataset_metadata: Mapped[dict] = mapped_column(postgresql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)

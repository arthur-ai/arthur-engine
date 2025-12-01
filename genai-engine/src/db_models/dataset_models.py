import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base


class DatabaseDataset(Base):
    __tablename__ = "datasets"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    # metadata is a reserved sqlalchemy name so we'll use dataset_metadata
    dataset_metadata: Mapped[Any] = mapped_column(postgresql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # versions relationship include for cascade-delete functionality
    versions: Mapped[List["DatabaseDatasetVersion"]] = relationship(
        cascade="all,delete",
    )
    # transforms relationship include for cascade-delete functionality
    transforms: Mapped[List["DatabaseDatasetTransform"]] = relationship(
        cascade="all, delete-orphan",
    )
    latest_version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class DatabaseDatasetVersion(Base):
    __tablename__ = "dataset_versions"
    version_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("datasets.id"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    version_rows: Mapped[List["DatabaseDatasetVersionRow"]] = relationship(
        cascade="all,delete",
        lazy="joined",
        order_by="DatabaseDatasetVersionRow.created_at.desc()",
    )
    column_names: Mapped[List[str]] = mapped_column(JSON)


class DatabaseDatasetVersionRow(Base):
    __tablename__ = "dataset_version_rows"
    # using row-wise storage in case we ever move to a dataset versioning strategy that isn't full duplication
    # version_number must be in the primary key because a row may have been updated & have the same row_id in a later
    # version of the dataset, so a row_id is only unique to a certain version number of a dataset
    version_number: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    data: Mapped[Any] = mapped_column(postgresql.JSON)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())

    # Add composite index for efficient row lookups by version since dataset_id is not in the primary key
    # also add composite foreign key constraint (cannot be added on the columns:
    # https://docs.sqlalchemy.org/en/20/core/constraints.html#:~:text=It%E2%80%99s%20important%20to%20note%20that%20the%20ForeignKeyConstraint%20is%20the%20only%20way%20to%20define%20a%20composite%20foreign%20key.)
    __table_args__ = (
        Index(
            "ix_dataset_version_rows_dataset_version",
            "dataset_id",
            "version_number",
        ),
        ForeignKeyConstraint(
            ["version_number", "dataset_id"],
            ["dataset_versions.version_number", "dataset_versions.dataset_id"],
        ),
    )


class DatabaseDatasetTransform(Base):
    __tablename__ = "dataset_transforms"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    transform_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("trace_transforms.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "transform_id",
            name="uq_dataset_transforms_dataset_id_transform_id",
        ),
        Index("idx_dataset_transforms_dataset_id", "dataset_id"),
        Index("idx_dataset_transforms_transform_id", "transform_id"),
    )

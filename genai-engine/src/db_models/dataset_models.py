import uuid
from datetime import datetime
from typing import List

from sqlalchemy import TIMESTAMP, UUID, ForeignKey, Index, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    # versions relationship include for cascade-delete functionality
    versions: Mapped[List["DatabaseDatasetVersion"]] = relationship(
        cascade="all,delete",
    )


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
        foreign_keys="[DatabaseDatasetVersionRow.version_number, DatabaseDatasetVersionRow.dataset_id]",
    )


class DatabaseDatasetVersionRow(Base):
    __tablename__ = "dataset_version_rows"
    # using row-wise storage in case we ever move to a dataset versioning strategy that isn't full duplication
    # version_number must be in the primary key because a row may have been updated & have the same row_id in a later
    # version of the dataset, so a row_id is only unique to a certain version number of a dataset
    version_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dataset_versions.version_number"),
        primary_key=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("dataset_versions.dataset_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    data: Mapped[dict] = mapped_column(postgresql.JSON)

    # Add composite index for efficient row lookups by version since dataset_id is not in the primary key
    __table_args__ = (
        Index(
            "ix_dataset_version_rows_version_dataset",
            "version_number",
            "dataset_id",
        ),
    )

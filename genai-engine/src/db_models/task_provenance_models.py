from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from arthur_common.models.agent_governance_schemas import SourceClass
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseTaskProvenanceSource(Base):
    """One discovery source's report of one agent, held against the task it resolved to.

    A task's provenance is a list -- every sensor that has reported the agent, and every
    address each one reported it at -- and that list is unbounded: a Jamf source that
    finds one agent on 500 devices, all converging on one task through a shared service
    name, contributes 500 entries. That is why this is a table joined to `tasks` rather
    than a JSON column on it. A column would be rewritten whole on every scan that
    touched the task, and "which tasks did source X report since T" -- the question the
    fetch job asks after every scan -- would be a scan of every task's JSON rather than
    an index range.

    KEYED ON (source_id, external_id), the grain a scan reports at. An external ID maps
    to exactly one task (see `service_name_task_mappings`), so the key also fixes the
    task, and re-scanning the same finding updates its row rather than adding one.

    Only discovery findings land here. OTEL and manual tasks have no configured source
    to key on, so their single provenance entry is derived from the task's creation
    source when the response is built, rather than stored twice.
    """

    __tablename__ = "task_provenance_sources"

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    external_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "tasks.id",
            name="fk_task_provenance_sources_task_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    source_class: Mapped[SourceClass] = mapped_column(
        Enum(
            SourceClass,
            values_callable=lambda e: [x.value for x in e],
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # A `SourceAddress`, as JSON: instance, scope, resource kind and id, and the query
    # that surfaced the finding. The latest scan's answer, since a source config's query
    # can be edited between runs.
    address: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    # UTC, naive, and the engine's clock rather than the sensor's: these say when a scan
    # handed the finding over, which is what the fetch job windows on. When the sensor
    # itself saw the agent is evidence, and is the Platform's to hold.
    first_reported_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    last_reported_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

    __table_args__ = (
        Index(
            "idx_task_provenance_sources_source_reported",
            "source_id",
            "last_reported_at",
        ),
    )

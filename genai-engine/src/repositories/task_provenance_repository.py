import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, NamedTuple, Optional
from uuid import UUID

from arthur_common.models.agent_governance_schemas import (
    Platform,
    ProvenanceSource,
    RunsOn,
)
from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    func,
    literal,
    select,
)
from sqlalchemy.dialects.postgresql import Insert as PGInsertType
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import Insert as SQLiteInsertType
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from db_models import DatabaseTaskProvenanceSource

logger = logging.getLogger(__name__)

# Task IDs per IN clause when reading provenance in bulk.
_LOOKUP_CHUNK_SIZE = 500


def utc_naive(moment: datetime) -> datetime:
    """The instant as the naive UTC timestamp the provenance columns store.

    A naive input is taken to be UTC already, since that is what every caller inside the
    engine passes. An aware one -- a query parameter from the fetch job, say -- is
    converted, so a window expressed in any offset compares correctly.
    """
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def _latest(*moments: Optional[datetime]) -> Optional[datetime]:
    """The latest of the moments given, ignoring missing ones."""
    present = [moment for moment in moments if moment is not None]
    return max(present) if present else None


def _later_of(
    stored: SQLColumnExpression[Optional[datetime]],
    incoming: SQLColumnExpression[Optional[datetime]],
    is_postgres: bool,
) -> ColumnElement[Optional[datetime]]:
    """The later of two nullable timestamps, in SQL, taking whichever one is present.

    Postgres's GREATEST skips nulls, but SQLite's two-argument max returns null if
    either is, so each side is coalesced with the other first: a row stored before
    `last_seen` was, or a record that somehow lacks one, never erases the other value.
    """
    stored_or_incoming = func.coalesce(stored, incoming)
    incoming_or_stored = func.coalesce(incoming, stored)
    if is_postgres:
        return func.greatest(stored_or_incoming, incoming_or_stored)
    return func.max(stored_or_incoming, incoming_or_stored)


def _runs_on_to_keep(
    incoming: Optional[RunsOn],
    earlier: Optional[RunsOn],
) -> Optional[RunsOn]:
    """The `runs_on` a report leaves behind: its own answer only if it has one.

    UNKNOWN is a sensor saying it cannot tell, which is no more an answer than silence,
    so neither replaces a location already known. The same rule the served provenance
    applies across rows, applied within one; `_runs_on_kept` is its SQL twin.
    """
    if incoming is not None and incoming is not RunsOn.UNKNOWN:
        return incoming
    return earlier if earlier is not None else incoming


def _runs_on_kept(
    stored: SQLColumnExpression[Optional[RunsOn]],
    incoming: SQLColumnExpression[Optional[RunsOn]],
) -> ColumnElement[Optional[RunsOn]]:
    """`_runs_on_to_keep`, in SQL, for a report landing on a stored row."""
    return func.coalesce(
        func.nullif(incoming, literal(RunsOn.UNKNOWN.value)),
        stored,
        incoming,
    )


class ProvenanceReport(NamedTuple):
    """One resolved record, as `record_reports` stores it."""

    external_id: str
    task_id: str
    entry: ProvenanceSource
    # Where the record said the machine is and which OS it runs. Beside the entry rather
    # than on it: a task's provenance serves these as one answer per task, not one per
    # source, so the entry type has nowhere to carry them.
    runs_on: Optional[RunsOn] = None
    platform: Optional[Platform] = None


class TaskProvenanceRepository:
    """Reads and writes the per-source provenance rows held against discovered tasks.

    See `DatabaseTaskProvenanceSource` for why provenance is a joined table.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def record_reports(
        self,
        reports: Iterable[ProvenanceReport],
        reported_at: Optional[datetime] = None,
    ) -> None:
        """Upsert what one scan reported, in a single statement.

        A finding seen before keeps its `first_reported_at` and takes this scan's
        address, task and `last_reported_at`; a new one gets a row. The task is
        overwritten rather than kept because the resolver just answered for it, and the
        resolver is where identity lives.

        `last_seen` is not simply overwritten: it keeps the later of the stored and
        incoming values, so a batch that arrives out of order cannot move it backwards.
        Nor are `runs_on` and `platform`: a report that says nothing about them keeps
        what an earlier one said, since silence is not a new answer -- and a `runs_on`
        of UNKNOWN says nothing either.

        Args:
            reports: One per resolved record. Every entry must carry a `source_id` -- a
                report with no source cannot be found again by the source that made it.
                A key repeated within the batch keeps its last occurrence, the latest
                `last_seen` among them, and the last `runs_on` and `platform` any of
                them gave, since one statement cannot upsert the same row twice.
            reported_at: When the scan handed the batch over. Defaults to now.
        """
        now = utc_naive(reported_at or datetime.now(timezone.utc))
        rows: dict[tuple[UUID, str], dict[str, object]] = {}
        latest_seen: dict[tuple[UUID, str], Optional[datetime]] = {}
        kept_runs_on: dict[tuple[UUID, str], Optional[RunsOn]] = {}
        kept_platform: dict[tuple[UUID, str], Optional[Platform]] = {}
        for external_id, task_id, entry, runs_on, platform in reports:
            if entry.source_id is None:
                raise ValueError(
                    f"Provenance for '{external_id}' has no source_id; a discovery "
                    "report must name the source that made it",
                )
            key = (entry.source_id, external_id)
            latest_seen[key] = _latest(
                latest_seen.get(key),
                utc_naive(entry.last_seen) if entry.last_seen else None,
            )
            kept_runs_on[key] = _runs_on_to_keep(runs_on, kept_runs_on.get(key))
            kept_platform[key] = (
                platform if platform is not None else kept_platform.get(key)
            )
            rows[key] = {
                "source_id": entry.source_id,
                "external_id": external_id,
                "task_id": task_id,
                "source_class": entry.source_class,
                "vendor": entry.vendor,
                "address": (
                    entry.address.model_dump(mode="json") if entry.address else None
                ),
                "first_reported_at": now,
                "last_reported_at": now,
                "last_seen": latest_seen[key],
                "runs_on": kept_runs_on[key],
                "platform": kept_platform[key],
            }

        if not rows:
            return

        values = list(rows.values())
        stmt: PGInsertType | SQLiteInsertType
        # Postgres in production; SQLite backs the unit tests. Both spell the upsert the
        # same way once the dialect's insert is chosen; only "the later of two" differs.
        is_postgres = bool(
            self.db_session.bind and self.db_session.bind.dialect.name == "postgresql",
        )
        if is_postgres:
            stmt = pg_insert(DatabaseTaskProvenanceSource).values(values)
        else:
            stmt = sqlite_insert(DatabaseTaskProvenanceSource).values(values)

        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id", "external_id"],
            set_={
                "task_id": stmt.excluded.task_id,
                "source_class": stmt.excluded.source_class,
                "vendor": stmt.excluded.vendor,
                "address": stmt.excluded.address,
                "last_reported_at": stmt.excluded.last_reported_at,
                "last_seen": _later_of(
                    DatabaseTaskProvenanceSource.last_seen,
                    stmt.excluded.last_seen,
                    is_postgres,
                ),
                "runs_on": _runs_on_kept(
                    DatabaseTaskProvenanceSource.runs_on,
                    stmt.excluded.runs_on,
                ),
                "platform": func.coalesce(
                    stmt.excluded.platform,
                    DatabaseTaskProvenanceSource.platform,
                ),
            },
        )
        self.db_session.execute(stmt)
        self.db_session.commit()

        logger.debug(f"Recorded provenance for {len(values)} discovered record(s)")

    def get_by_task_ids(
        self,
        task_ids: Iterable[str],
    ) -> dict[str, list[DatabaseTaskProvenanceSource]]:
        """Every provenance row for each task, in the order each was first reported.

        One query per chunk rather than one per task, since the agent-tasks listing
        builds provenance for every task it returns.

        Returns:
            dict: task_id -> rows, holding only tasks that have any.
        """
        ids = list(dict.fromkeys(task_ids))
        by_task: dict[str, list[DatabaseTaskProvenanceSource]] = defaultdict(list)
        for start in range(0, len(ids), _LOOKUP_CHUNK_SIZE):
            chunk = ids[start : start + _LOOKUP_CHUNK_SIZE]
            rows = self.db_session.scalars(
                select(DatabaseTaskProvenanceSource)
                .where(DatabaseTaskProvenanceSource.task_id.in_(chunk))
                .order_by(
                    DatabaseTaskProvenanceSource.first_reported_at,
                    DatabaseTaskProvenanceSource.source_id,
                    DatabaseTaskProvenanceSource.external_id,
                ),
            ).all()
            for row in rows:
                by_task[row.task_id].append(row)

        return dict(by_task)

    @staticmethod
    def reported_task_ids(
        source_id: Optional[UUID] = None,
        reported_since: Optional[datetime] = None,
    ) -> Select[tuple[str]]:
        """The tasks a source reported, optionally only since some instant, as a subquery.

        A subquery rather than a list, so a source that reports thousands of tasks does
        not become thousands of bind parameters in the caller's IN clause.

        "Reported", not "created": a re-scan resolves the agents it already knew to the
        tasks they already have, and the fetch job still has to hear about every one of
        them, or an agent the source sees every day would read as gone the day after
        it was first found.
        """
        stmt = select(DatabaseTaskProvenanceSource.task_id).distinct()
        if source_id is not None:
            stmt = stmt.where(DatabaseTaskProvenanceSource.source_id == source_id)
        if reported_since is not None:
            stmt = stmt.where(
                DatabaseTaskProvenanceSource.last_reported_at
                >= utc_naive(reported_since),
            )
        return stmt

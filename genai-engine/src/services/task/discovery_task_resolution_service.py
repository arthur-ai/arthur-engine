import logging
from typing import Iterable, Optional
from uuid import UUID

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models import DatabaseTask
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from repositories.tasks_repository import TaskRepository
from schemas.agent_discovery_schemas import (
    DiscoveredRecordFailureReason,
    FailedDiscoveredRecord,
    ResolvedAgentTask,
    ResolveDiscoveredAgentsResponse,
    TaskResolutionMethod,
)
from schemas.enums import MappingKeyKind
from schemas.internal_schemas import Task

logger = logging.getLogger(__name__)

# A row of `service_name_task_mappings`, as the resolver's view of the table keys it.
MappingKey = tuple[MappingKeyKind, str]


class _TaskNotFound(Exception):
    """A record named, or resolved to, a task that is not there.

    Raised inside one record's resolution and caught by `resolve_records`, which
    reports that record as failed and moves on to the next.
    """

    def __init__(self, task_id: str) -> None:
        super().__init__(task_id)
        self.task_id = task_id


class DiscoveryTaskResolutionService:
    """Turns discovered records into tasks, and is where the identity guarantee lives.

    Everything downstream -- the fetch job, the inventory, coverage counts, triage --
    operates on whatever tasks this step produced, and nothing downstream can correct
    a bad key. Two findings that collapse onto one task stay collapsed; one agent that
    churns two tasks per scan stays churning.

    The ladder, which deliberately mirrors `TraceIngestionService._resolve_task_id`:

    1. The record names a task -> use it. Optional on this input only, since a SIEM
       does not know Arthur's task IDs. The one exception is an `external_id` that
       already maps to a different task: mappings are immutable, so the claim cannot
       move it, and the record resolves at rung 2 to the task that owns it.
    2. `external_id` already maps to a task -> use it. This is what makes a re-scan
       free: the first run wrote the mapping, every later run reads it.
    3. A service name the sensor observed already maps to a task -> use it, and map
       `external_id` to that task so the next run resolves at rung 2.
    4. Nothing matched -> mint a task and map `external_id` to it.

    THE KEY SPACE IS `service_name_task_mappings`, the same table OTEL resolution
    reads. That is the whole mechanism behind "a discovered agent someone later
    instruments resolves to the same task": its traces arrive carrying a service name,
    and the row is already there. Nothing reconciles the two afterwards, because
    nothing has to. `external_id` rows are written with `key_kind=external_id`, so
    they route later scans without ever being read as a service name: not by trace
    ingestion, and not by the service names a task reports.

    WHAT TWO SOURCES REPORTING ONE AGENT DOES, since D-03's upsert key assumes an
    answer: they converge only if they agree on `external_id` or if their observed
    service names overlap (rung 3). Otherwise they mint two tasks. That is v1's
    intended behavior -- `external_id` is canonical and no identity resolution runs
    across sensors -- and the corroboration case is D-09's provenance to express, by
    holding several evidence records against one task, not this resolver's to guess at.

    WHAT THIS DELIBERATELY DOES NOT DO: rename an existing task to the name the record
    carried, or rewrite its creation source from a later scan. Identity is stable; the
    per-sensor record of what was seen when is evidence, which D-09 persists. A record
    without an `external_id` never reaches here -- the connector output contract
    rejects it upstream, and the request model refuses it here -- so no finding is ever
    routed to the unmapped task.
    """

    def __init__(
        self,
        db_session: Session,
        task_repo: TaskRepository,
    ) -> None:
        self.db_session = db_session
        self.task_repo = task_repo
        self.mapping_repo = ServiceNameMappingRepository(db_session)

    def resolve_records(
        self,
        records: list[DiscoveredAgentRecord],
        org_id: Optional[UUID] = None,
    ) -> ResolveDiscoveredAgentsResponse:
        """Resolve a scan's worth of records to tasks, in the order submitted.

        Records are resolved one at a time against a mapping view seeded by a single
        query and kept current as tasks are minted, so two records in one batch that
        share an identity share a task rather than racing each other to create one.
        The tasks those mappings name are read in one query alongside it, so the cost
        of a scan is a handful of round trips plus what it actually writes, rather
        than growing with the number of records that resolve to something.

        Each mint commits on its own. A batch that fails partway therefore leaves the
        records it already resolved durably resolved, which is what makes the retry
        safe: the scan job re-submits the same records and they come back down rung 2.

        That only holds for a failure a retry can get past, so a record that names a
        task that does not exist fails on its own instead. Every explicit `task_id` in
        the batch is checked in one query before anything is written, and a record
        that fails it is reported in `failed` while the rest resolve. A task that
        disappears mid-batch is caught the same way.

        Args:
            records: The discovered records to resolve.
            org_id: Owning org for any task minted here. Defaults to the `default` org.

        Returns:
            Every record, in request order, in either `resolved` or `failed`.
        """
        # Seed the view with every key this batch could possibly match on, one query
        # per kind. `dict.fromkeys` rather than a set so the order is stable and the
        # emitted SQL is the same run to run, which makes the query log readable.
        known_mappings = self._load_mappings(
            MappingKeyKind.EXTERNAL_ID,
            dict.fromkeys(record.external_id for record in records),
        )
        known_mappings.update(
            self._load_mappings(
                MappingKeyKind.SERVICE_NAME,
                dict.fromkeys(
                    name for record in records for name in record.service_names
                ),
            ),
        )

        # Every task this batch can resolve to without minting one: the tasks the
        # records name outright, and the tasks the mapping view points at. Read
        # together in one query, because a steady-state re-scan resolves every record
        # at rung 2 and would otherwise pay the round trip the mapping view just
        # saved, once per record.
        known_tasks = self._load_tasks(
            (
                *(record.task_id for record in records if record.task_id),
                *known_mappings.values(),
            ),
        )

        resolved: list[ResolvedAgentTask] = []
        failed: list[FailedDiscoveredRecord] = []
        for record in records:
            if record.task_id and record.task_id not in known_tasks:
                failed.append(self._task_not_found(record, record.task_id))
                continue

            try:
                resolved.append(
                    self._resolve_record(
                        record,
                        known_tasks,
                        known_mappings,
                        org_id,
                    ),
                )
            except _TaskNotFound as e:
                failed.append(self._task_not_found(record, e.task_id))

        return ResolveDiscoveredAgentsResponse(resolved=resolved, failed=failed)

    def _resolve_record(
        self,
        record: DiscoveredAgentRecord,
        known_tasks: dict[str, DatabaseTask],
        known_mappings: dict[MappingKey, str],
        org_id: Optional[UUID],
    ) -> ResolvedAgentTask:
        """Walk one record down the ladder. See the class docstring for the rungs.

        Raises:
            _TaskNotFound: A task this record resolved to disappeared mid-batch.
        """
        # Rung 1: the caller already knows the task.
        if record.task_id:
            task = known_tasks[record.task_id]
            identity_owner_id = self._map_keys_to_task(record, task.id, known_mappings)
            if identity_owner_id == task.id:
                return ResolvedAgentTask(
                    external_id=record.external_id,
                    task_id=task.id,
                    name=task.name,
                    resolved_by=TaskResolutionMethod.EXPLICIT_TASK_ID,
                )

            # The identity already belongs elsewhere, and the mapping is immutable.
            # Reporting the requested task anyway would split this agent's findings
            # across two tasks and flip it between them from scan to scan, so it
            # falls through to rung 2, which now finds the owner in the view.
            logger.warning(
                f"Discovered record '{record.external_id}' asked for task "
                f"'{task.id}', but its identity already maps to task "
                f"'{identity_owner_id}'; resolving to the owner",
            )

        # Rung 2: a previous scan already minted a task for this identity.
        existing_task_id = known_mappings.get(
            (MappingKeyKind.EXTERNAL_ID, record.external_id),
        )
        if existing_task_id:
            task = self._require_task(existing_task_id, known_tasks)
            self._map_keys_to_task(record, task.id, known_mappings)
            return ResolvedAgentTask(
                external_id=record.external_id,
                task_id=task.id,
                name=task.name,
                resolved_by=TaskResolutionMethod.EXTERNAL_ID,
            )

        # Rung 3: the agent is already known under a service name this sensor saw --
        # its own traces are arriving, or another source reported the same name.
        for service_name in record.service_names:
            mapped_task_id = known_mappings.get(
                (MappingKeyKind.SERVICE_NAME, service_name),
            )
            if not mapped_task_id:
                continue
            task = self._require_task(mapped_task_id, known_tasks)
            logger.info(
                f"Discovered record '{record.external_id}' matched task "
                f"'{task.name}' ({task.id}) via service name '{service_name}'",
            )
            identity_owner_id = self._map_keys_to_task(
                record,
                task.id,
                known_mappings,
            )
            if identity_owner_id != task.id:
                # Another request claimed `external_id` between this batch reading
                # the mappings and writing one. The matched task existed before this
                # call, so there is nothing to discard -- only the answer changes.
                logger.info(
                    f"Discovered record '{record.external_id}' lost its identity "
                    f"claim to task '{identity_owner_id}'; resolving to the owner "
                    f"instead of '{task.id}'",
                )
                return self._resolve_to_owner(record, identity_owner_id, known_tasks)

            return ResolvedAgentTask(
                external_id=record.external_id,
                task_id=task.id,
                name=task.name,
                resolved_by=TaskResolutionMethod.SERVICE_NAME,
            )

        # Rung 4: nothing knows this agent yet. Bound to its own name because the
        # repository hands back the internal `Task`, not the `DatabaseTask` the rungs
        # above resolve to.
        created_task = self.task_repo.create_discovered_task(
            name=record.name,
            creation_source=record.task_creation_source,
            org_id=org_id,
        )
        logger.info(
            f"Minted task '{created_task.name}' ({created_task.id}) for discovered "
            f"record '{record.external_id}'",
        )
        identity_owner_id = self._map_keys_to_task(
            record,
            created_task.id,
            known_mappings,
        )
        if identity_owner_id != created_task.id:
            return self._yield_identity_to(
                record,
                created_task,
                identity_owner_id,
                known_tasks,
            )

        return ResolvedAgentTask(
            external_id=record.external_id,
            task_id=created_task.id,
            name=created_task.name,
            resolved_by=TaskResolutionMethod.CREATED,
        )

    def _yield_identity_to(
        self,
        record: DiscoveredAgentRecord,
        created_task: Task,
        owner_task_id: str,
        known_tasks: dict[str, DatabaseTask],
    ) -> ResolvedAgentTask:
        """Give up a task minted for an identity another request claimed first.

        Between rung 4 reading the mappings and writing one, a concurrent request --
        another connector's batch, or trace ingestion auto-creating for a service name
        this scan is discovering -- can take `external_id` for a task of its own. The
        mapping is immutable and the other side won, so this request's task is now a
        task no key points at: invisible to every later scan, but counted in the
        inventory and the coverage numbers as an agent nobody will ever attribute a
        finding to. It is deleted rather than left, because it was minted moments ago
        by this call and nothing has had the chance to reference it.

        The record then resolves to the winner and reports `EXTERNAL_ID`, which is
        what actually answered: by the time the caller hears back, the identity was
        already mapped. Reporting `CREATED` would tell the scan job it minted a task
        that no longer exists.
        """
        logger.info(
            f"Discovered record '{record.external_id}' lost its identity claim to "
            f"task '{owner_task_id}'; discarding the task minted for it "
            f"({created_task.id})",
        )
        self.task_repo.delete_task(created_task.id)
        return self._resolve_to_owner(record, owner_task_id, known_tasks)

    def _resolve_to_owner(
        self,
        record: DiscoveredAgentRecord,
        owner_task_id: str,
        known_tasks: dict[str, DatabaseTask],
    ) -> ResolvedAgentTask:
        """Resolve a record to the task that won its identity from under this batch.

        Reports `EXTERNAL_ID`, which is what actually answered: by the time the caller
        hears back, the identity was already mapped, and the next scan resolves the
        same way at rung 2.
        """
        owner_task = self._require_task(owner_task_id, known_tasks)
        return ResolvedAgentTask(
            external_id=record.external_id,
            task_id=owner_task.id,
            name=owner_task.name,
            resolved_by=TaskResolutionMethod.EXTERNAL_ID,
        )

    def _map_keys_to_task(
        self,
        record: DiscoveredAgentRecord,
        task_id: str,
        known_mappings: dict[MappingKey, str],
    ) -> str:
        """Key this record's identity, and the names it emits under, to its task.

        Mapping `external_id` is what makes the next scan a lookup instead of a
        decision. Mapping the observed service names is what makes traces from this
        agent land on the same task the moment someone instruments it.

        Mappings are immutable, so a key already pointing somewhere is left alone: the
        first answer wins, and a source that starts reporting a name another task
        already owns does not steal it. `create_mapping` enforces that against
        concurrent writers too -- on a conflict it returns the mapping that won rather
        than raising -- so what goes into `known_mappings` is the row that is actually
        in the table, not the one this call hoped to write.

        The identity is claimed before any service name, and a lost claim stops the
        rest: the service names would otherwise be keyed to a task rung 4 is about to
        delete, and the request that won the identity maps them to the winner anyway.

        Returns:
            The task that owns `record.external_id` once the writes are done, which is
            `task_id` unless another request claimed the identity first. Every rung
            that can write the identity acts on it, so the response names the task
            the table does: rungs 1 and 3 resolve to the owner, and rung 4 also
            discards the task it minted. Rung 2 read the identity from the view, so
            its claim never writes and cannot lose.
        """
        owner_task_id = self._claim_key(
            (MappingKeyKind.EXTERNAL_ID, record.external_id),
            task_id,
            known_mappings,
        )
        if owner_task_id != task_id:
            return owner_task_id

        for service_name in record.service_names:
            self._claim_key(
                (MappingKeyKind.SERVICE_NAME, service_name),
                task_id,
                known_mappings,
            )

        return owner_task_id

    def _load_tasks(self, task_ids: Iterable[str]) -> dict[str, DatabaseTask]:
        """Fetch tasks this batch may resolve to, archived ones included, in one query.

        A task ID missing from the result does not exist. For one a record named
        outright that is how a bad `task_id` is found before anything is written; for
        one a mapping points at it means the task was deleted, which `_require_task`
        turns into that record's own failure.

        Archived tasks are included for the same reason `_require_task` includes them:
        archiving decides what is shown, not who an agent is.
        """
        ids = list(dict.fromkeys(task_ids))
        if not ids:
            return {}

        tasks, _ = self.task_repo.query_tasks(
            ids=ids,
            include_archived=True,
            page_size=None,
        )
        return {task.id: task for task in tasks}

    def _task_not_found(
        self,
        record: DiscoveredAgentRecord,
        task_id: str,
    ) -> FailedDiscoveredRecord:
        """Report a record whose task is not there, and log it for the operator."""
        detail = (
            f"Discovered record '{record.external_id}' resolved to task "
            f"'{task_id}', which does not exist"
        )
        logger.warning(detail)
        return FailedDiscoveredRecord(
            external_id=record.external_id,
            task_id=task_id,
            reason=DiscoveredRecordFailureReason.TASK_NOT_FOUND,
            detail=detail,
        )

    def _load_mappings(
        self,
        key_kind: MappingKeyKind,
        keys: Iterable[str],
    ) -> dict[MappingKey, str]:
        """Read the task each of `keys` already maps to, keyed for the resolver's view."""
        return {
            (key_kind, key): task_id
            for key, task_id in self.mapping_repo.get_task_ids_by_service_names(
                keys,
                key_kind,
            ).items()
        }

    def _claim_key(
        self,
        key: MappingKey,
        task_id: str,
        known_mappings: dict[MappingKey, str],
    ) -> str:
        """Point one key at a task, and report which task it actually points at.

        `create_mapping` returns the mapping that won on a conflict rather than
        raising, so the task recorded here is the row that is in the table -- which is
        not always the one this call asked for.

        Raises:
            _TaskNotFound: `task_id` was deleted after this batch read it, so the
                mapping's foreign key refused the write.
        """
        if key not in known_mappings:
            key_kind, name = key
            try:
                mapping = self.mapping_repo.create_mapping(name, task_id, key_kind)
            except IntegrityError:
                raise _TaskNotFound(task_id)
            known_mappings[key] = mapping.task_id

        return known_mappings[key]

    def _require_task(
        self,
        task_id: str,
        known_tasks: dict[str, DatabaseTask],
    ) -> DatabaseTask:
        """Fetch a task a mapping pointed at, archived ones included.

        Served from the batch's task view, which `resolve_records` read in one query.
        A miss is a task the view could not have held -- one minted by an earlier
        record of this batch, or one a concurrent request claimed an identity for --
        so it falls back to a query of its own rather than being treated as absent.

        Archived tasks resolve normally, matching how trace ingestion routes to them:
        archiving is a decision about what to show, and minting a second task because
        the first was archived would break identity exactly where it matters most.

        Raises:
            _TaskNotFound: The task was deleted after this batch read the mapping.
        """
        task = known_tasks.get(task_id)
        if task is not None:
            return task

        try:
            task = self.task_repo.get_db_task_by_id(task_id, include_archived=True)
        except HTTPException:
            raise _TaskNotFound(task_id)

        known_tasks[task_id] = task
        return task

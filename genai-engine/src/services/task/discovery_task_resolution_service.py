import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from db_models import DatabaseTask
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from repositories.tasks_repository import TaskRepository
from schemas.agent_discovery_schemas import (
    DiscoveredAgentRecord,
    ResolvedAgentTask,
    TaskResolutionMethod,
)

logger = logging.getLogger(__name__)


class DiscoveryTaskResolutionService:
    """Turns discovered records into tasks, and is where the identity guarantee lives.

    Everything downstream -- the fetch job, the inventory, coverage counts, triage --
    operates on whatever tasks this step produced, and nothing downstream can correct
    a bad key. Two findings that collapse onto one task stay collapsed; one agent that
    churns two tasks per scan stays churning.

    The ladder, which deliberately mirrors `TraceIngestionService._resolve_task_id`:

    1. The record names a task -> use it. Optional on this input only, since a SIEM
       does not know Arthur's task IDs.
    2. `external_id` already maps to a task -> use it. This is what makes a re-scan
       free: the first run wrote the mapping, every later run reads it.
    3. A service name the sensor observed already maps to a task -> use it, and map
       `external_id` to that task so the next run resolves at rung 2.
    4. Nothing matched -> mint a task and map `external_id` to it.

    THE KEY SPACE IS `service_name_task_mappings`, the same table OTEL resolution
    reads. That is the whole mechanism behind "a discovered agent someone later
    instruments resolves to the same task": its traces arrive carrying a service name,
    and the row is already there. Nothing reconciles the two afterwards, because
    nothing has to.

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
    ) -> list[ResolvedAgentTask]:
        """Resolve a scan's worth of records to tasks, in the order submitted.

        Records are resolved one at a time against a mapping view seeded by a single
        query and kept current as tasks are minted, so two records in one batch that
        share an identity share a task rather than racing each other to create one.

        Each mint commits on its own. A batch that fails partway therefore leaves the
        records it already resolved durably resolved, which is what makes the retry
        safe: the scan job re-submits the same records and they come back down rung 2.

        Args:
            records: The discovered records to resolve.
            org_id: Owning org for any task minted here. Defaults to the `default` org.

        Returns:
            One ResolvedAgentTask per record, in request order.
        """
        # Seed the view with every key this batch could possibly match on, in one
        # query. `dict.fromkeys` rather than a set so the order is stable and the
        # emitted SQL is the same run to run, which makes the query log readable.
        lookup_keys = dict.fromkeys(
            key
            for record in records
            for key in (record.external_id, *record.service_names)
        )
        known_mappings = self.mapping_repo.get_task_ids_by_service_names(lookup_keys)

        return [
            self._resolve_record(record, known_mappings, org_id) for record in records
        ]

    def _resolve_record(
        self,
        record: DiscoveredAgentRecord,
        known_mappings: dict[str, str],
        org_id: Optional[UUID],
    ) -> ResolvedAgentTask:
        """Walk one record down the ladder. See the class docstring for the rungs."""
        # Rung 1: the caller already knows the task.
        if record.task_id:
            task = self._require_task(record.task_id, record.external_id)
            self._map_keys_to_task(record, task.id, known_mappings)
            return ResolvedAgentTask(
                external_id=record.external_id,
                task_id=task.id,
                name=task.name,
                resolved_by=TaskResolutionMethod.EXPLICIT_TASK_ID,
            )

        # Rung 2: a previous scan already minted a task for this identity.
        existing_task_id = known_mappings.get(record.external_id)
        if existing_task_id:
            task = self._require_task(existing_task_id, record.external_id)
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
            mapped_task_id = known_mappings.get(service_name)
            if not mapped_task_id:
                continue
            task = self._require_task(mapped_task_id, record.external_id)
            logger.info(
                f"Discovered record '{record.external_id}' matched task "
                f"'{task.name}' ({task.id}) via service name '{service_name}'",
            )
            self._map_keys_to_task(record, task.id, known_mappings)
            return ResolvedAgentTask(
                external_id=record.external_id,
                task_id=task.id,
                name=task.name,
                resolved_by=TaskResolutionMethod.SERVICE_NAME,
            )

        # Rung 4: nothing knows this agent yet.
        task = self.task_repo.create_discovered_task(
            name=record.name,
            creation_source=record.creation_source,
            org_id=org_id,
        )
        logger.info(
            f"Minted task '{task.name}' ({task.id}) for discovered record "
            f"'{record.external_id}'",
        )
        self._map_keys_to_task(record, task.id, known_mappings)
        return ResolvedAgentTask(
            external_id=record.external_id,
            task_id=task.id,
            name=task.name,
            resolved_by=TaskResolutionMethod.CREATED,
        )

    def _map_keys_to_task(
        self,
        record: DiscoveredAgentRecord,
        task_id: str,
        known_mappings: dict[str, str],
    ) -> None:
        """Key this record's identity, and the names it emits under, to its task.

        Mapping `external_id` is what makes the next scan a lookup instead of a
        decision. Mapping the observed service names is what makes traces from this
        agent land on the same task the moment someone instruments it.

        Mappings are immutable, so a key already pointing somewhere is left alone: the
        first answer wins, and a source that starts reporting a name another task
        already owns does not steal it.
        """
        for key in (record.external_id, *record.service_names):
            if key in known_mappings:
                continue
            self.mapping_repo.create_mapping(key, task_id)
            known_mappings[key] = task_id

    def _require_task(self, task_id: str, external_id: str) -> DatabaseTask:
        """Fetch a task the caller or a mapping pointed at, archived ones included.

        Archived tasks resolve normally, matching how trace ingestion routes to them:
        archiving is a decision about what to show, and minting a second task because
        the first was archived would break identity exactly where it matters most.
        """
        try:
            return self.task_repo.get_db_task_by_id(task_id, include_archived=True)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Discovered record '{external_id}' resolved to task "
                    f"'{task_id}', which does not exist"
                ),
            )

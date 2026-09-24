import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    DataSource,
    DiscoveryAgentCreationSource,
    EnrichedAgentMetadata,
    GCPAgentCreationSource,
    LLMModel,
    ManualAgentCreationSource,
    OTELAgentCreationSource,
    Provenance,
    ProvenanceSource,
    SourceAddress,
    SubAgent,
    TaskMetadata,
    Tool,
)
from arthur_common.models.enums import (
    PaginationSortMethod,
    RuleScope,
    RuleType,
)
from fastapi import HTTPException
from openinference.semconv.trace import OpenInferenceSpanKindValues
from opentelemetry import trace
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from db_models import (
    DatabaseRule,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTaskProvenanceSource,
    DatabaseTaskToMetrics,
    DatabaseTaskToRules,
)
from db_models.telemetry_models import DatabaseTraceMetadata
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.service_name_mapping_repository import (
    ServiceNameMappingRepository,
)
from repositories.task_provenance_repository import TaskProvenanceRepository
from schemas.enums import TaskSortField
from schemas.internal_schemas import (
    ApplicationConfiguration,
    Rule,
    Task,
)
from utils import constants
from utils.constants import DEFAULT_ORG_ID
from utils.trace import get_nested_value

tracer = trace.get_tracer(__name__)

LLM_RULE_TYPES = set(
    [
        RuleType.MODEL_HALLUCINATION_V2,
        RuleType.MODEL_SENSITIVE_DATA,
    ],
)

# Task IDs per IN clause when reading spans in bulk. Smaller than the other bulk
# lookups because each chunk also loads up to 30 days of those tasks' spans.
_SPAN_LOOKUP_CHUNK_SIZE = 100


class TaskRepository:
    def __init__(
        self,
        db_session: Session,
        rule_repository: RuleRepository,
        metric_repository: MetricRepository,
        application_config: ApplicationConfiguration,
    ):
        self.db_session = db_session
        self.rule_repository = rule_repository
        self.metric_repository = metric_repository
        self.app_config = application_config

    @tracer.start_as_current_span("query_tasks")
    def query_tasks(
        self,
        ids: Optional[list[str]] = None,
        task_name: Optional[str] = None,
        is_agentic: Optional[bool] = None,
        include_archived: bool = False,
        only_archived: bool = False,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        sort_field: Optional[TaskSortField] = None,
        last_active_start_time: Optional[datetime] = None,
        last_active_end_time: Optional[datetime] = None,
        page_size: Optional[int] = 10,
        page: int = 0,
        org_scope: Optional[UUID] = None,
        reported_by_source_id: Optional[UUID] = None,
        reported_since: Optional[datetime] = None,
    ) -> tuple[list[DatabaseTask], int]:
        stmt = self.db_session.query(DatabaseTask)
        # Tenant callers see only their own org's tasks. Admin (org_scope=None)
        # passes through and sees everything.
        if org_scope is not None:
            stmt = stmt.where(DatabaseTask.org_id == org_scope)
        if ids:
            stmt = stmt.where(DatabaseTask.id.in_(ids))
        if task_name:
            stmt = stmt.where(DatabaseTask.name.ilike(f"%{task_name}%"))
        if is_agentic is not None:
            stmt = stmt.where(DatabaseTask.is_agentic == is_agentic)
        if only_archived:
            stmt = stmt.where(DatabaseTask.archived == True)
        elif not include_archived:
            stmt = stmt.where(DatabaseTask.archived == False)
        # Provenance filters: the tasks a discovery source reported, and when. Only
        # discovered tasks have provenance rows, so either filter excludes the rest.
        if reported_by_source_id is not None or reported_since is not None:
            stmt = stmt.where(
                DatabaseTask.id.in_(
                    TaskProvenanceRepository.reported_task_ids(
                        source_id=reported_by_source_id,
                        reported_since=reported_since,
                    ),
                ),
            )

        # last_active is NOT a column on tasks: it is the most recent trace
        # end-time per task, derived from trace_metadata. We only join the
        # aggregation subquery when the caller filters or sorts on it, so the
        # default (no param) query is byte-for-byte the historical behavior.
        filtering_last_active = (
            last_active_start_time is not None or last_active_end_time is not None
        )
        sorting_last_active = sort_field == TaskSortField.LAST_ACTIVE
        last_active_column = None
        if filtering_last_active or sorting_last_active:
            last_active_query = self.db_session.query(
                DatabaseTraceMetadata.task_id.label("task_id"),
                func.max(DatabaseTraceMetadata.end_time).label("last_active"),
            )
            # trace_metadata carries a denormalized org_id; scope the
            # aggregation so tenants only see their own trace activity.
            if org_scope is not None:
                last_active_query = last_active_query.filter(
                    DatabaseTraceMetadata.org_id == org_scope,
                )
            last_active_subquery = last_active_query.group_by(
                DatabaseTraceMetadata.task_id,
            ).subquery()
            last_active_column = last_active_subquery.c.last_active

            if filtering_last_active:
                # INNER join intentionally drops tasks with no traces / null
                # last_active while the filter is active.
                stmt = stmt.join(
                    last_active_subquery,
                    DatabaseTask.id == last_active_subquery.c.task_id,
                )
                if last_active_start_time is not None:
                    stmt = stmt.where(last_active_column >= last_active_start_time)
                if last_active_end_time is not None:
                    stmt = stmt.where(last_active_column <= last_active_end_time)
            else:
                # Sorting only: keep trace-less tasks (LEFT join) and push their
                # null last_active to the end regardless of direction.
                stmt = stmt.outerjoin(
                    last_active_subquery,
                    DatabaseTask.id == last_active_subquery.c.task_id,
                )

        # Any: branches assign different column kinds (task columns vs the
        # last_active subquery column), which mypy would otherwise reject.
        order_column: Any = DatabaseTask.created_at
        if sort_field == TaskSortField.NAME:
            order_column = DatabaseTask.name
        elif sort_field == TaskSortField.UPDATED_AT:
            order_column = DatabaseTask.updated_at
        elif sort_field == TaskSortField.LAST_ACTIVE:
            order_column = last_active_column

        if sort == PaginationSortMethod.ASCENDING:
            ordering = asc(order_column)
        else:
            ordering = desc(order_column)
        if sorting_last_active:
            ordering = ordering.nulls_last()
        # The ID breaks ties, so a page boundary falls in the same place on every call
        # and paging through tasks created in the same instant neither skips nor
        # repeats any.
        stmt = stmt.order_by(ordering, DatabaseTask.id)

        # Calculate the count prior to applying the offset
        count = stmt.count()

        # page_size=None fetches all matching tasks (no offset/limit applied)
        if page_size is not None:
            if page is not None:
                stmt = stmt.offset(page * page_size)
            stmt = stmt.limit(page_size)
        results = stmt.all()

        return results, count

    def get_db_task_by_id(
        self,
        id: str,
        include_archived: bool = False,
    ) -> DatabaseTask:
        db_task = (
            self.db_session.query(DatabaseTask).filter(DatabaseTask.id == id).first()
        )
        if not db_task or (not include_archived and db_task.archived):
            raise HTTPException(
                status_code=404,
                detail="Task %s not found." % id,
                headers={"full_stacktrace": "false"},
            )
        return db_task

    def get_task_by_id(self, id: str) -> Task:
        db_task = self.get_db_task_by_id(id)
        task = Task._from_database_model(db_task)

        # Enrich with service names from service_name_task_mappings
        if task.is_agentic:
            service_name_repo = ServiceNameMappingRepository(self.db_session)
            service_names = service_name_repo.get_service_names_by_task_id(id)
            if service_names:
                task.service_names = service_names

        return task

    def _extract_agent_metadata(self, task_id: str) -> EnrichedAgentMetadata:
        """Extract tools, sub-agents, models, and span count from spans for an agent task.

        See `_extract_agent_metadata_for_tasks`, which this is the single-task form of.

        Args:
            task_id: UUID of the task to extract metadata for

        Returns:
            EnrichedAgentMetadata TypedDict with keys: tools, sub_agents, models, num_spans
        """
        return self._extract_agent_metadata_for_tasks([task_id])[task_id]

    def _extract_agent_metadata_for_tasks(
        self,
        task_ids: list[str],
    ) -> dict[str, EnrichedAgentMetadata]:
        """Extract tools, sub-agents, models, and span count from spans for many tasks.

        Queries the spans table for the given task_ids and extracts, per task:
        - Tools: spans where span_kind == TOOL (last 30 days)
        - Sub-agents: spans where span_kind == AGENT (last 30 days)
        - Models: extracted from LLM spans at attributes.llm.model_name (last 30 days)
        - Total number of spans (all time, all span kinds)

        Two queries per chunk of task IDs rather than two per task, since the
        agent-tasks listing enriches every task it returns.

        Args:
            task_ids: UUIDs of the tasks to extract metadata for

        Returns:
            dict: task_id -> EnrichedAgentMetadata, for every task asked about, with
            empty metadata for a task that has no spans.
        """
        # Query AGENT, TOOL, LLM spans for metadata extraction (last 30 days)
        relevant_span_kinds = [
            OpenInferenceSpanKindValues.AGENT.value,
            OpenInferenceSpanKindValues.TOOL.value,
            OpenInferenceSpanKindValues.LLM.value,
        ]
        thirty_days_ago = datetime.now() - timedelta(days=30)

        ids = list(dict.fromkeys(task_ids))
        tools: dict[str, set[str]] = defaultdict(set)
        sub_agents: dict[str, set[str]] = defaultdict(set)
        models: dict[str, set[str]] = defaultdict(set)
        data_sources: dict[str, set[str]] = defaultdict(set)
        span_counts: dict[str, int] = {}

        for start in range(0, len(ids), _SPAN_LOOKUP_CHUNK_SIZE):
            chunk = ids[start : start + _SPAN_LOOKUP_CHUNK_SIZE]
            spans = (
                self.db_session.query(
                    DatabaseSpan.task_id,
                    DatabaseSpan.span_kind,
                    DatabaseSpan.span_name,
                    DatabaseSpan.raw_data,
                )
                .filter(
                    DatabaseSpan.task_id.in_(chunk),
                    DatabaseSpan.span_kind.in_(relevant_span_kinds),
                    DatabaseSpan.created_at >= thirty_days_ago,
                )
                .all()
            )

            # Count all spans per task (not filtered by span_kind)
            counts = (
                self.db_session.query(DatabaseSpan.task_id, func.count(DatabaseSpan.id))
                .filter(DatabaseSpan.task_id.in_(chunk))
                .group_by(DatabaseSpan.task_id)
                .all()
            )
            span_counts.update((task_id, count) for task_id, count in counts)

            for span in spans:
                raw_data = span.raw_data or {}
                attributes = raw_data.get("attributes", {})

                # Extract data_source from metadata for all span kinds
                data_source = get_nested_value(attributes, "metadata.data_source")
                if data_source:
                    data_sources[span.task_id].add(data_source)

                if span.span_kind == OpenInferenceSpanKindValues.TOOL.value:
                    tool_name = (
                        get_nested_value(attributes, "tool_call.function.name")
                        or span.span_name
                    )
                    if tool_name:
                        tools[span.task_id].add(tool_name)

                elif span.span_kind == OpenInferenceSpanKindValues.AGENT.value:
                    agent_name = (
                        get_nested_value(attributes, "agent.name") or span.span_name
                    )
                    if agent_name:
                        sub_agents[span.task_id].add(agent_name)

                elif span.span_kind == OpenInferenceSpanKindValues.LLM.value:
                    model_name = get_nested_value(attributes, "llm.model_name")
                    if model_name:
                        models[span.task_id].add(model_name)

        return {
            task_id: {
                "tools": [
                    Tool(name=name, arguments=[])
                    for name in sorted(tools.get(task_id, ()))
                ],
                "sub_agents": [
                    SubAgent(name=name) for name in sorted(sub_agents.get(task_id, ()))
                ],
                "models": [
                    LLMModel(name=name) for name in sorted(models.get(task_id, ()))
                ],
                "data_sources": [
                    DataSource(url=url) for url in sorted(data_sources.get(task_id, ()))
                ],
                "num_spans": span_counts.get(task_id, 0),
            }
            for task_id in ids
        }

    def _get_task_creation_source(self, task: Task) -> Optional[AgentCreationSource]:
        """Get creation_source for a task, with service_names injected.

        Reads creation_source directly from task_metadata.
        For tasks without task_metadata, infers creation source from task properties.
        Injects task.service_names (from service_name_task_mappings) into every
        creation source that has somewhere to put them: a flat field on the
        pre-category GCP and OTEL variants, and observations.service_names on the
        discovery categories. MANUAL records a human decision rather than an
        observation, so it passes through untouched.

        Args:
            task: Task object with service_names already populated

        Returns:
            AgentCreationSource or None
        """
        service_names = task.service_names or []

        if task.task_metadata and task.task_metadata.creation_source:
            cs = task.task_metadata.creation_source.root

            # The pre-category variants carry service names as a flat field.
            if isinstance(cs, (GCPAgentCreationSource, OTELAgentCreationSource)):
                return AgentCreationSource(
                    root=cs.model_copy(update={"service_names": service_names}),
                )

            # The discovery categories carry them in observations. Without this they
            # are dropped: EnrichedTaskResponse has no service_names of its own, so
            # the creation source is the only route they take to a caller, and the
            # link between a discovered agent and traces already arriving is exactly
            # what the fetch job needs.
            if isinstance(cs, DiscoveryAgentCreationSource):
                return AgentCreationSource(
                    root=cs.model_copy(
                        update={
                            "observations": cs.observations.model_copy(
                                update={"service_names": service_names},
                            ),
                        },
                    ),
                )

            return AgentCreationSource(root=cs)

        # No task_metadata — infer from task properties
        if task.is_autocreated:
            return AgentCreationSource(
                root=OTELAgentCreationSource(service_names=service_names),
            )
        elif task.is_agentic:
            return AgentCreationSource(root=ManualAgentCreationSource())
        else:
            return None

    @staticmethod
    def _get_task_provenance(
        creation_source: Optional[AgentCreationSource],
        provenance_rows: list[DatabaseTaskProvenanceSource],
    ) -> Optional[Provenance]:
        """Assemble a task's provenance from its creation source and stored reports.

        Each stored row is one discovery source's report of the agent at one address.
        The creation source contributes an entry of its own only when no row stands in
        for it: an OTEL, manual or legacy GCP task was never reported by a configured
        source, so its creation source is the only provenance it has, while a task a
        scan minted is usually represented by that scan's row, which also names the
        source. "Usually", so a row has to match the finding before it replaces it: a
        task minted before rows were written, or whose minting scan failed to record
        its report, may have rows only from sources that converged on it later, and
        dropping the finding then loses the source that actually found the agent.

        Args:
            creation_source: The task's creation source, as served.
            provenance_rows: The task's stored reports, oldest first.

        Returns:
            Provenance, or None for a task with no creation source and no reports.
        """
        sources: list[ProvenanceSource] = []
        if creation_source is not None:
            origin = ProvenanceSource.from_creation_source(creation_source)
            represented = isinstance(
                creation_source.root,
                DiscoveryAgentCreationSource,
            ) and any(
                TaskRepository._reports_same_finding(origin, row)
                for row in provenance_rows
            )
            if not represented:
                sources.append(origin)

        sources.extend(
            ProvenanceSource(
                source_class=row.source_class,
                source_id=row.source_id,
                vendor=row.vendor,
                address=(
                    SourceAddress.model_validate(row.address) if row.address else None
                ),
            )
            for row in provenance_rows
        )

        if not sources:
            return None
        return Provenance(sources=sources)

    @staticmethod
    def _reports_same_finding(
        origin: ProvenanceSource,
        row: DatabaseTaskProvenanceSource,
    ) -> bool:
        """Whether a stored report is the finding a task was created from.

        Compared on identity -- class, vendor and every address field but the query --
        since a row holds the latest scan's address, and a source config's query can be
        edited between the scan that minted the task and the one that last reported it.
        """
        if row.source_class != origin.source_class or row.vendor != origin.vendor:
            return False
        if origin.address is None or row.address is None:
            return origin.address is None and row.address is None
        return SourceAddress.model_validate(row.address).model_dump(
            exclude={"query"},
        ) == origin.address.model_dump(exclude={"query"})

    def _enrich_tasks_with_service_names(self, tasks: list[Task]) -> list[Task]:
        """Enrich tasks with service names from service_name_task_mappings.

        Sets task.service_names for each agentic task.

        Args:
            tasks: List of tasks to enrich

        Returns:
            List of tasks with service_names populated
        """
        service_names = ServiceNameMappingRepository(
            self.db_session,
        ).get_service_names_by_task_ids(task.id for task in tasks if task.is_agentic)

        for task in tasks:
            if task.id in service_names:
                task.service_names = service_names[task.id]

        return tasks

    def get_all_tasks(self, org_scope: Optional[UUID] = None) -> list[Task]:
        # Continuously grab tasks until there are no more, DEFAULT_PAGE_SIZE at a time
        all_tasks: list[DatabaseTask] = []
        page = 0
        while True:
            db_tasks, _ = self.query_tasks(
                page=page,
                page_size=constants.DEFAULT_PAGE_SIZE,
                org_scope=org_scope,
            )
            if not db_tasks:
                break
            all_tasks.extend(db_tasks)
            page += 1

        tasks = [Task._from_database_model(op) for op in all_tasks]

        # Enrich tasks with service names
        tasks = self._enrich_tasks_with_service_names(tasks)

        return tasks

    def archive_task(self, task_id: str) -> None:
        db_task = self.get_db_task_by_id(task_id)

        # Prevent archiving of system tasks
        if db_task.is_system_task:
            raise HTTPException(
                status_code=400,
                detail="Cannot archive system tasks",
                headers={"full_stacktrace": "false"},
            )

        for link in db_task.rule_links:
            if link.rule.scope == RuleScope.TASK:
                self.rule_repository.archive_rule(link.rule_id, commit=False)

        for metric_link in db_task.metric_links:
            self.metric_repository.archive_metric(metric_link.metric_id, commit=False)

        db_task.archived = True
        self.db_session.commit()

    def unarchive_task(self, task_id: str) -> None:
        db_task = (
            self.db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == task_id)
            .first()
        )
        if not db_task:
            raise HTTPException(status_code=404, detail="Task %s not found." % task_id)
        if not db_task.archived:
            raise HTTPException(
                status_code=400,
                detail="Task %s is not archived." % task_id,
            )
        if db_task.is_system_task:
            raise HTTPException(status_code=400, detail="Cannot unarchive system tasks")

        for link in db_task.rule_links:
            if link.rule.scope == RuleScope.TASK:
                self.rule_repository.unarchive_rule(link.rule_id, commit=False)

        for metric_link in db_task.metric_links:
            self.metric_repository.unarchive_metric(metric_link.metric_id, commit=False)

        db_task.archived = False
        self.db_session.commit()

    def create_task(
        self,
        task: Task,
        with_default_rules: bool = True,
        commit: bool = True,
    ) -> Task:
        db_task = task._to_database_model()

        if with_default_rules:
            db_default_rules, _ = self.rule_repository.query_rules(
                rule_scopes=[RuleScope.DEFAULT],
            )
            db_task.rule_links = [
                DatabaseTaskToRules(task_id=task.id, rule_id=r.id)
                for r in db_default_rules
            ]
        self.db_session.add(db_task)
        if commit:
            self.db_session.commit()
        else:
            self.db_session.flush()

        result = Task._from_database_model(db_task)
        return result

    def create_auto_task(self, service_name: str) -> Task:
        """Create an auto-generated task for a service name.

        Auto-created tasks:
        - Have name set to the service_name
        - Have is_autocreated=True flag set
        - Are agentic (is_agentic=True)
        - Do NOT get default rules (with_default_rules=False)
        - Have no task_metadata (not a registered agent)
        - Are owned by the `default` org (OTEL auto-discovery is an admin path)

        Args:
            service_name: The service name to create a task for

        Returns:
            Task: The created task
        """
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            name=service_name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=True,
            org_id=DEFAULT_ORG_ID,
        )

        return self.create_task(task, with_default_rules=False)

    def create_discovered_task(
        self,
        name: str,
        creation_source: AgentCreationSource,
        org_id: Optional[UUID] = None,
    ) -> Task:
        """Create a task for an agent a discovery scan found.

        The same task shape `create_auto_task` mints for an unregistered OTEL trace --
        agentic, auto-created, no default rules -- differing only in that the sensor
        that found it is recorded. Discovery and OTEL auto-creation are the same event
        seen from two sides, and a scan-minted task that looked different from a
        trace-minted one would show up as two kinds of agent in every downstream view.

        Default rules are deliberately not applied: nobody asked for this task, and a
        discovered agent that is not sending traces has nothing for a rule to evaluate.

        Args:
            name: Human-readable agent name, used as the task name.
            creation_source: The sensor that reported the agent, with its upstream
                address and observations.
            org_id: Owning org. Defaults to the `default` org, as discovery is an
                admin path in the same way OTEL auto-discovery is.

        Returns:
            Task: The created task.
        """
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=True,
            org_id=org_id or DEFAULT_ORG_ID,
            task_metadata=TaskMetadata(creation_source=creation_source),
        )

        return self.create_task(task, with_default_rules=False)

    def find_by_gcp_engine_id(self, engine_id: str) -> Optional[DatabaseTask]:
        """Find a task by its GCP reasoning engine ID in task_metadata JSON.

        Args:
            engine_id: The GCP reasoning engine ID to search for

        Returns:
            The matching DatabaseTask, or None if not found
        """
        return (
            self.db_session.query(DatabaseTask)
            .filter(
                func.json_extract_path_text(
                    DatabaseTask.task_metadata,
                    "creation_source",
                    "gcp_reasoning_engine_id",
                )
                == engine_id,
            )
            .first()
        )

    def link_rule_to_task(
        self,
        task_id: str,
        rule_id: str,
        rule_type: RuleType,
    ) -> None:
        if rule_type in LLM_RULE_TYPES:
            llm_rule_count = (
                self.db_session.query(DatabaseTaskToRules)
                .join(DatabaseRule)
                .where(
                    DatabaseTaskToRules.task_id == task_id,
                    DatabaseTaskToRules.enabled,
                    DatabaseRule.type.in_(LLM_RULE_TYPES),
                )
                .count()
            )
            max_llm_rule_count = self.app_config.max_llm_rules_per_task_count
            if llm_rule_count >= max_llm_rule_count:
                raise HTTPException(
                    status_code=400,
                    detail=constants.ERROR_TOO_MANY_LLM_RULES_PER_TASK
                    % max_llm_rule_count,
                )

        new_link = DatabaseTaskToRules(
            task_id=task_id,
            rule_id=rule_id,
        )
        self.db_session.add(new_link)
        self.db_session.commit()

    def create_task_rule(self, task_id: str, rule: Rule) -> Rule:
        db_task = self.get_db_task_by_id(task_id)

        if rule.type in LLM_RULE_TYPES:
            self.check_llm_rule_count(
                [link.rule for link in db_task.rule_links if link.enabled],
            )

        new_link = DatabaseTaskToRules(
            task_id=db_task.id,
            rule_id=rule.id,
            rule=Rule._to_database_model(rule),
        )
        self.db_session.add(new_link)
        self.db_session.commit()

        return rule

    def get_db_links(
        self,
        task_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> list[DatabaseTaskToRules]:
        # At least one of these should be specified
        if task_id is None and rule_id is None:
            # This is an implementation error on our part if this ever happens
            raise HTTPException(
                status_code=500,
                detail=constants.ERROR_UNCAUGHT_GENERIC,
            )

        query = self.db_session.query(DatabaseTaskToRules)
        if task_id is not None:
            query = query.where(DatabaseTaskToRules.task_id == task_id)
        if rule_id is not None:
            query = query.where(DatabaseTaskToRules.rule_id == rule_id)
        return query.all()

    def toggle_task_rule_enabled(
        self,
        task_id: str,
        rule_id: str,
        enabled: bool,
    ) -> None:
        task = self.get_db_task_by_id(task_id)
        for rule_link in task.rule_links:
            if rule_link.rule_id == rule_id:
                rule_link.enabled = enabled
        self.db_session.commit()
        return

    def delete_rule_link(self, task_id: str, rule_id: str) -> None:
        task = self.get_db_task_by_id(task_id)
        for rule_link in task.rule_links:
            if rule_link.rule_id == rule_id:
                self.db_session.delete(rule_link)
        self.db_session.commit()

    def delete_task(self, task_id: str) -> None:
        db_task = self.get_db_task_by_id(task_id)

        # Prevent deletion of system tasks
        if db_task.is_system_task:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete system tasks",
                headers={"full_stacktrace": "false"},
            )

        self.db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
        self.db_session.commit()

    def update_all_tasks_add_default_rule(self, default_rule: Rule) -> None:
        tasks = self.get_all_tasks()
        tasks_to_rules: list[DatabaseTaskToRules] = [
            DatabaseTaskToRules(task_id=task.id, rule_id=default_rule.id)
            for task in tasks
        ]
        self.db_session.add_all(tasks_to_rules)
        self.db_session.commit()

    def update_all_tasks_remove_default_rule(self, default_rule_id: str) -> int:
        default_rule_links = (
            self.db_session.query(DatabaseTaskToRules)
            .where(DatabaseTaskToRules.rule_id == default_rule_id)
            .all()
        )
        for link in default_rule_links:
            self.db_session.delete(link)
        self.db_session.commit()

        return len(default_rule_links)

    def check_llm_rule_count(self, enabled_rules: list[DatabaseRule]) -> None:
        llm_rule_count = len(
            [rule for rule in enabled_rules if rule.type in LLM_RULE_TYPES],
        )
        max_llm_rule_count = self.app_config.max_llm_rules_per_task_count
        if llm_rule_count >= max_llm_rule_count:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_TOO_MANY_LLM_RULES_PER_TASK % max_llm_rule_count,
            )

    def link_metric_to_task(self, task_id: str, metric_id: str) -> None:
        # Validate the task exists (404) before creating the link.
        self.get_db_task_by_id(task_id)

        new_link = DatabaseTaskToMetrics(
            task_id=task_id,
            metric_id=metric_id,
            enabled=True,
        )
        self.db_session.add(new_link)
        self.db_session.commit()

    def toggle_task_metric_enabled(
        self,
        task_id: str,
        metric_id: str,
        enabled: bool,
    ) -> None:
        task = self.get_db_task_by_id(task_id)

        for metric_link in task.metric_links:
            if metric_link.metric_id == metric_id:
                metric_link.enabled = enabled
        self.db_session.commit()
        return

    def archive_metric_link(self, task_id: str, metric_id: str) -> None:
        task = self.get_db_task_by_id(task_id)
        for metric_link in task.metric_links:
            if metric_link.metric_id == metric_id:
                self.db_session.delete(metric_link)
        self.db_session.commit()

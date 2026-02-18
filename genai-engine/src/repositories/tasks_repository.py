import uuid
from datetime import datetime, timedelta
from typing import Optional

from arthur_common.models.enums import (
    PaginationSortMethod,
    RegisteredAgentProvider,
    RuleScope,
    RuleType,
)
from fastapi import HTTPException
from openinference.semconv.trace import OpenInferenceSpanKindValues
from opentelemetry import trace
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from db_models import (
    DatabaseAgentPollingData,
    DatabaseRule,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTaskToMetrics,
    DatabaseTaskToRules,
)
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.service_name_mapping_repository import (
    ServiceNameMappingRepository,
)
from schemas.internal_schemas import (
    AgentMetadata,
    ApplicationConfiguration,
    CreationSource,
    GCPCreationSource,
    ManualCreationSource,
    OTELCreationSource,
    Rule,
    SubAgent,
    Task,
    TaskMetadata,
    Tool,
)
from services.agent_discovery_service import parse_gcp_resource_path
from utils import constants
from utils.trace import get_nested_value

tracer = trace.get_tracer(__name__)

LLM_RULE_TYPES = set(
    [
        RuleType.MODEL_HALLUCINATION_V2,
        RuleType.MODEL_SENSITIVE_DATA,
    ],
)


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
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page_size: int = 10,
        page: int = 0,
    ) -> tuple[list[DatabaseTask], int]:
        stmt = self.db_session.query(DatabaseTask)
        if ids:
            stmt = stmt.where(DatabaseTask.id.in_(ids))
        if task_name:
            stmt = stmt.where(DatabaseTask.name.ilike(f"%{task_name}%"))
        if is_agentic is not None:
            stmt = stmt.where(DatabaseTask.is_agentic == is_agentic)
        if not include_archived:
            stmt = stmt.where(DatabaseTask.archived == False)
        if sort == PaginationSortMethod.DESCENDING:
            stmt = stmt.order_by(desc(DatabaseTask.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            stmt = stmt.order_by(asc(DatabaseTask.created_at))

        # Calculate the count prior to applying the offset
        count = stmt.count()

        if page is not None:
            stmt = stmt.offset(page * page_size)
        results = stmt.limit(page_size).all()

        return results, count

    def get_db_task_by_id(self, id: str) -> DatabaseTask:
        db_task = (
            self.db_session.query(DatabaseTask).filter(DatabaseTask.id == id).first()
        )
        if not db_task or db_task.archived:
            raise HTTPException(
                status_code=404,
                detail="Task %s not found." % id,
                headers={"full_stacktrace": "false"},
            )
        return db_task

    def get_task_by_id(self, id: str) -> Task:
        db_task = self.get_db_task_by_id(id)
        task = Task._from_database_model(db_task)

        # Enrich with service names if task is agentic
        if task.is_agentic:
            service_name_repo = ServiceNameMappingRepository(self.db_session)
            service_names = service_name_repo.get_service_names_by_task_id(id)

            if service_names:
                if task.task_metadata:
                    # Update existing TaskMetadata with service_names
                    task.task_metadata.service_names = service_names
                else:
                    # Create TaskMetadata with EXTERNAL provider for autocreated tasks
                    task.task_metadata = TaskMetadata(
                        provider=RegisteredAgentProvider.EXTERNAL,
                        service_names=service_names,
                    )

        return task

    def _extract_agent_metadata(self, task_id: str) -> AgentMetadata:
        """Extract tools, sub-agents, models, and span count from spans for an agent task.

        Queries the spans table for the given task_id and extracts:
        - Tools: spans where span_kind == TOOL
        - Sub-agents: spans where span_kind == AGENT
        - Models: extracted from LLM spans at attributes.llm.model_name
        - Total number of spans (limited to last 30 days)

        Args:
            task_id: UUID of the task to extract metadata for

        Returns:
            AgentMetadata TypedDict with keys: tools, sub_agents, models, num_spans
        """
        # Query all relevant spans (AGENT, TOOL, LLM) for this task within last 30 days
        relevant_span_kinds = [
            OpenInferenceSpanKindValues.AGENT.value,
            OpenInferenceSpanKindValues.TOOL.value,
            OpenInferenceSpanKindValues.LLM.value,
        ]
        thirty_days_ago = datetime.now() - timedelta(days=30)
        spans = (
            self.db_session.query(DatabaseSpan)
            .filter(
                DatabaseSpan.task_id == task_id,
                DatabaseSpan.span_kind.in_(relevant_span_kinds),
                DatabaseSpan.created_at >= thirty_days_ago,
            )
            .all()
        )

        tools_set = set()
        sub_agents_set = set()
        models_set = set()

        for span in spans:
            # Filter by span_kind to categorize
            if span.span_kind == OpenInferenceSpanKindValues.TOOL.value:
                # Tools: use span name
                if span.span_name:
                    tools_set.add(span.span_name)

            elif span.span_kind == OpenInferenceSpanKindValues.AGENT.value:
                # Sub-agents: use span name
                if span.span_name:
                    sub_agents_set.add(span.span_name)

            elif span.span_kind == OpenInferenceSpanKindValues.LLM.value:
                # Models: extract from attributes.llm.model_name
                raw_data = span.raw_data or {}
                attributes = raw_data.get("attributes", {})
                model_name = get_nested_value(attributes, "llm.model_name")
                if model_name:
                    models_set.add(model_name)

        # Convert sets to sorted lists and create schema objects
        return {
            "tools": [Tool(name=name, arguments=[]) for name in sorted(tools_set)],
            "sub_agents": [SubAgent(name=name) for name in sorted(sub_agents_set)],
            "models": sorted(list(models_set)),
            "num_spans": len(spans),
        }

    def _map_task_metadata_to_creation_source(
        self, task: Task
    ) -> tuple[Optional[str], Optional[CreationSource]]:
        """Map old task_metadata format to new creation_source format.

        This is a temporary helper for Phase 1 to work with the existing database schema.
        Will be removed in Phase 3 after database migration.

        Args:
            task: Task object with old-format task_metadata

        Returns:
            Tuple of (infrastructure, creation_source) where:
            - infrastructure: "GCP", "AWS", etc. or None
            - creation_source: GCPCreationSource, OTELCreationSource, or ManualCreationSource
        """
        # If no task_metadata, this is either a manual task or an auto-created task
        if not task.task_metadata:
            if task.is_autocreated:
                # Auto-created from OTEL traces
                return None, OTELCreationSource(
                    type="OTEL",
                    service_name=task.name,
                )
            elif task.is_agentic:
                # Manually created agentic task
                return None, ManualCreationSource(type="manual")
            else:
                # Non-agentic task
                return None, None

        # Extract old format fields
        provider = task.task_metadata.provider
        gcp_metadata = task.task_metadata.gcp_metadata
        service_names = task.task_metadata.service_names or []

        # Set infrastructure based on provider (uppercase for API response)
        infrastructure = provider.value.upper() if provider else None

        # Query agent_polling_data for last_fetched timestamp
        polling_data = (
            self.db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.task_id == task.id)
            .first()
        )
        last_fetched = polling_data.last_fetched if polling_data else None

        # Map to new format based on provider
        creation_source: CreationSource

        if provider == RegisteredAgentProvider.GCP:
            if not gcp_metadata:
                # Fallback for missing GCP metadata
                return infrastructure, ManualCreationSource(type="manual")

            # Parse resource_id to extract reasoning_engine_id
            resource_id = gcp_metadata.resource_id or ""
            _, gcp_region, gcp_reasoning_engine_id = parse_gcp_resource_path(
                resource_id
            )

            creation_source = GCPCreationSource(
                type="GCP",
                gcp_project_id=gcp_metadata.project_id or "",
                gcp_region=gcp_region or gcp_metadata.region or "",
                gcp_reasoning_engine_id=gcp_reasoning_engine_id or "",
                service_names=service_names,
                last_fetched=last_fetched,
            )
            return infrastructure, creation_source

        elif task.is_autocreated:
            # Auto-created from OTEL traces
            creation_source = OTELCreationSource(
                type="OTEL",
                service_name=task.name,  # Use task name as service name
            )
            return infrastructure, creation_source

        else:
            # Manually created task
            creation_source = ManualCreationSource(
                type="manual",
                service_names=service_names,
            )
            return infrastructure, creation_source

    def _enrich_tasks_with_service_names(self, tasks: list[Task]) -> list[Task]:
        """Enrich tasks with service names from service_name_task_mappings.

        Args:
            tasks: List of tasks to enrich

        Returns:
            List of tasks with service_names populated in task_metadata
        """
        service_name_repo = ServiceNameMappingRepository(self.db_session)

        for task in tasks:
            if task.is_agentic:
                service_names = service_name_repo.get_service_names_by_task_id(task.id)
                if service_names:
                    if task.task_metadata:
                        # Update existing TaskMetadata with service_names
                        task.task_metadata.service_names = service_names
                    else:
                        # Create TaskMetadata with EXTERNAL provider for autocreated tasks
                        task.task_metadata = TaskMetadata(
                            provider=RegisteredAgentProvider.EXTERNAL,
                            service_names=service_names,
                        )

        return tasks

    def get_all_tasks(self) -> list[Task]:
        # Continuously grab tasks until there are no more, DEFAULT_PAGE_SIZE at a time
        all_tasks: list[DatabaseTask] = []
        page = 0
        while True:
            db_tasks, _ = self.query_tasks(
                page=page,
                page_size=constants.DEFAULT_PAGE_SIZE,
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
                self.rule_repository.archive_rule(link.rule_id)

        for metric_link in db_task.metric_links:
            self.metric_repository.archive_metric(metric_link.metric_id)
        db_task.archived = True
        self.db_session.commit()

    def create_task(self, task: Task, with_default_rules: bool = True) -> Task:
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
        self.db_session.commit()

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
        )

        return self.create_task(task, with_default_rules=False)

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
        # Check if task is agentic before allowing metric linkage
        db_task = self.get_db_task_by_id(task_id)
        if not db_task.is_agentic:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_NON_AGENTIC_TASK_METRIC,
            )

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

        # Check if task is agentic when enabling a metric
        if enabled and not task.is_agentic:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_NON_AGENTIC_TASK_METRIC,
            )

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

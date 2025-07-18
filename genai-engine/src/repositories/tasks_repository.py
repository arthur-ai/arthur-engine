from db_models.db_models import DatabaseRule, DatabaseTask, DatabaseTaskToRules, DatabaseTaskToMetrics
from fastapi import HTTPException
from opentelemetry import trace
from repositories.rules_repository import RuleRepository
from repositories.metrics_repository import MetricRepository
from schemas.enums import PaginationSortMethod, RuleScope, RuleType
from schemas.internal_schemas import ApplicationConfiguration, Rule, Task
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from utils import constants
from typing import Optional

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
        ids: list[str] = None,
        task_name: str = None,
        include_archived: bool = False,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page_size: int = 10,
        page: int = 0,
    ) -> list[DatabaseTask]:
        stmt = self.db_session.query(DatabaseTask)
        if ids:
            stmt = stmt.where(DatabaseTask.id.in_(ids))
        if task_name:
            stmt = stmt.where(DatabaseTask.name.ilike(f"%{task_name}%"))
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
        return Task._from_database_model(self.get_db_task_by_id(id))

    def get_all_tasks(self):
        # Continuously grab tasks until there are no more, DEFAULT_PAGE_SIZE at a time
        all_tasks = []
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

        return tasks

    def archive_task(self, task_id: str):
        db_task = self.get_db_task_by_id(task_id)
        for link in db_task.rule_links:
            if link.rule.scope == RuleScope.TASK:
                self.rule_repository.archive_rule(link.rule_id)
        
        for link in db_task.metric_links:
            self.metric_repository.archive_metric(link.metric_id)
        db_task.archived = True
        self.db_session.commit()

    def create_task(self, task: Task, with_default_rules=True):
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

        return Task._from_database_model(db_task)

    def link_rule_to_task(self, task_id: str, rule_id: str, rule_type: RuleType):
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

    def create_task_rule(self, task_id: str, rule: Rule):
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

    def get_db_links(self, task_id=None, rule_id=None):
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

    def toggle_task_rule_enabled(self, task_id: str, rule_id: str, enabled: bool):
        task = self.get_db_task_by_id(task_id)
        for rule_link in task.rule_links:
            if rule_link.rule_id == rule_id:
                rule_link.enabled = enabled
        self.db_session.commit()
        return

    def delete_rule_link(self, task_id: str, rule_id: str):
        task = self.get_db_task_by_id(task_id)
        for rule_link in task.rule_links:
            if rule_link.rule_id == rule_id:
                self.db_session.delete(rule_link)
        self.db_session.commit()

    def delete_task(self, task_id: str):
        self.db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
        self.db_session.commit()

    def update_all_tasks_add_default_rule(self, default_rule: Rule):
        tasks = self.get_all_tasks()
        tasks_to_rules: list[DatabaseTaskToRules] = []
        for task in tasks:
            task_to_rule = DatabaseTaskToRules(
                task_id=task.id,
                rule_id=default_rule.id,
            )
            tasks_to_rules.append(task_to_rule)
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

    def check_llm_rule_count(self, enabled_rules: list[DatabaseRule]):
        llm_rule_count = len(
            [rule for rule in enabled_rules if rule.type in LLM_RULE_TYPES],
        )
        max_llm_rule_count = self.app_config.max_llm_rules_per_task_count
        if llm_rule_count >= max_llm_rule_count:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_TOO_MANY_LLM_RULES_PER_TASK % max_llm_rule_count,
            )

    def link_metric_to_task(self, task_id: str, metric_id: str):
        new_link = DatabaseTaskToMetrics(
            task_id=task_id,
            metric_id=metric_id,
            enabled=True
        )
        self.db_session.add(new_link)
        self.db_session.commit()

    def toggle_task_metric_enabled(self, task_id: str, metric_id: str, enabled: bool):
        task = self.get_db_task_by_id(task_id)
        for metric_link in task.metric_links:
            if metric_link.metric_id == metric_id:
                metric_link.enabled = enabled
        self.db_session.commit()
        return
    
    def archive_metric_link(self, task_id: str, metric_id: str):
        task = self.get_db_task_by_id(task_id)
        for metric_link in task.metric_links:
            if metric_link.metric_id == metric_id:
                self.db_session.delete(metric_link)
        self.db_session.commit()

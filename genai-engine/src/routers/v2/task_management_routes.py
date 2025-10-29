from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import RuleScope, RuleType
from arthur_common.models.request_schemas import (
    NewMetricRequest,
    NewRuleRequest,
    NewTaskRequest,
    SearchTasksRequest,
    UpdateMetricRequest,
    UpdateRuleRequest,
)
from arthur_common.models.response_schemas import (
    MetricResponse,
    RuleResponse,
    SearchTasksResponse,
    TaskResponse,
)
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse, Response

from clients.telemetry.telemetry_client import (
    TelemetryEventTypes,
    send_telemetry_event,
    send_telemetry_event_for_task_rule_create_completed,
)
from config.cache_config import cache_config
from dependencies import get_application_config, get_db_session
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.tasks_repository import TaskRepository
from repositories.tasks_rules_repository import TasksRulesRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, Metric, Rule, Task, User
from utils import constants
from utils.users import permission_checker
from utils.utils import common_pagination_parameters, public_endpoint

task_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)
rules_types = [rule.value for rule in RuleType]

################################
#### Task Management Routes ####
################################


@task_management_routes.post(
    "/tasks",
    description="Register a new task. When a new task is created, all existing default rules will be "
    "auto-applied for this new task. Optionally specify if the task is agentic.",
    response_model=TaskResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_task(
    request: NewTaskRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
    try:
        send_telemetry_event(TelemetryEventTypes.TASK_CREATE_INITIATED)
        if len(request.name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Task names cannot contain only white space characters",
            )

        rules_repo = RuleRepository(db_session)
        tasks_repo = TaskRepository(
            db_session,
            rules_repo,
            MetricRepository(db_session),
            application_config,
        )
        task = Task._from_request_model(request)
        task = tasks_repo.create_task(task)

        send_telemetry_event(TelemetryEventTypes.TASK_CREATE_COMPLETED)
        return task._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.get(
    "/tasks",
    description="[Deprecated] Use /tasks/search endpoint. This endpoint will be removed in a future release.",
    response_model=list[TaskResponse],
    tags=["Tasks"],
    deprecated=True,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_tasks(
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> list[TaskResponse]:
    try:
        rules_repo = RuleRepository(db_session)
        tasks_repo = TaskRepository(
            db_session,
            rules_repo,
            MetricRepository(db_session),
            application_config,
        )
        tasks = tasks_repo.get_all_tasks()

        return [task._to_response_model() for task in tasks]
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.delete(
    "/tasks/{task_id}",
    description="Archive task. Also archives all task-scoped rules. Associated default rules are unaffected.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def archive_task(
    task_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        rules_repo = RuleRepository(db_session)
        tasks_repo = TaskRepository(
            db_session,
            rules_repo,
            MetricRepository(db_session),
            application_config,
        )
        tasks_repo.archive_task(str(task_id))

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.get(
    "/tasks/{task_id}",
    description="Get tasks.",
    response_model=TaskResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_task(
    task_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
    try:
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task = task_repo.get_task_by_id(str(task_id))
        return task._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.post(
    "/task",
    description="Redirect to /tasks endpoint.",
    tags=["Tasks"],
)
@public_endpoint
def redirect_to_tasks() -> RedirectResponse:
    return RedirectResponse(
        url="/api/v2/tasks",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


############################
#### Task Search Routes ####
############################


@task_management_routes.post(
    "/tasks/search",
    description="Search tasks. Can filter by task IDs, task name substring, and agentic status.",
    response_model=SearchTasksResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def search_tasks(
    request: SearchTasksRequest,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SearchTasksResponse:
    try:
        rules_repo = RuleRepository(db_session)
        metrics_repo = MetricRepository(db_session)
        tasks_repo = TaskRepository(
            db_session,
            rules_repo,
            metrics_repo,
            application_config,
        )
        db_tasks, count = tasks_repo.query_tasks(
            ids=request.task_ids,
            task_name=request.task_name,
            is_agentic=request.is_agentic,
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
        )
        tasks = [Task._from_database_model(db_task) for db_task in db_tasks]
        return SearchTasksResponse(
            tasks=[task._to_response_model() for task in tasks],
            count=count,
        )
    except:
        raise
    finally:
        db_session.close()


#####################################
#### Task Rule Management Routes ####
#####################################


@task_management_routes.post(
    "/tasks/{task_id}/rules",
    description="Create a rule to be applied only to this task. Available rule types are {}."
    "Note: The rules are cached by the validation endpoints for {} seconds. ".format(
        ", ".join(rules_types),
        cache_config.TASK_RULES_CACHE_TTL,
    ),
    response_model=RuleResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_task_rule(
    task_id: UUID,
    request: NewRuleRequest = Body(
        None,
        openapi_examples=NewRuleRequest.model_config["json_schema_extra"],  # type: ignore[arg-type]
    ),
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RuleResponse:
    try:
        send_telemetry_event(TelemetryEventTypes.TASK_RULE_CREATE_INITIATED)
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        rule_repo = RuleRepository(db_session)
        task = task_repo.get_task_by_id(str(task_id))

        new_rule = rule_repo.create_rule(
            Rule._from_request_model(request, scope=RuleScope.TASK),
        )
        task_repo.link_rule_to_task(task.id, new_rule.id, new_rule.type)

        response_rule = new_rule._to_response_model()
        response_rule.enabled = True
        send_telemetry_event_for_task_rule_create_completed(new_rule.type)
        return response_rule
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.patch(
    "/tasks/{task_id}/rules/{rule_id}",
    description="Enable or disable an existing rule for this task including the default rules.",
    response_model=TaskResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_task_rules(
    task_id: UUID,
    rule_id: UUID,
    body: UpdateRuleRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
    try:
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task_repo.toggle_task_rule_enabled(str(task_id), str(rule_id), body.enabled)
        updated_task = task_repo.get_task_by_id(str(task_id))

        return updated_task._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.delete(
    "/tasks/{task_id}/rules/{rule_id}",
    description="Archive an existing rule for this task.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def archive_task_rule(
    task_id: UUID,
    rule_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        rule_repo = RuleRepository(db_session)
        rule = rule_repo.get_rule_by_id(str(rule_id))

        if rule.scope == RuleScope.DEFAULT:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_CANNOT_DELETE_DEFAULT_RULE,
            )

        tasks_rules_repo = TasksRulesRepository(db_session)
        task_rules = tasks_rules_repo._get_task_rules_ids(
            str(task_id),
            only_enabled=False,
        )
        if str(rule_id) not in task_rules:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_UNRELATED_TASK_RULE,
            )

        task_repo = TaskRepository(
            db_session,
            rule_repo,
            MetricRepository(db_session),
            application_config,
        )

        task_repo.delete_rule_link(str(task_id), str(rule_id))

        rules, _ = rule_repo.query_rules(rule_ids=[str(rule_id)])
        rule = rules[0]
        if rule.scope == RuleScope.TASK:
            rule_repo.archive_rule(str(rule_id))

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise
    finally:
        db_session.close()


#############################
#### Task Metrics Routes ####
#############################


@task_management_routes.post(
    "/tasks/{task_id}/metrics",
    description="Create metrics for a task. Only agentic tasks can have metrics.",
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_task_metric(
    task_id: UUID,
    request: NewMetricRequest = Body(
        None,
        openapi_examples=NewMetricRequest.model_config["json_schema_extra"],  # type: ignore[arg-type]
    ),
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> MetricResponse:
    try:
        metric_repo = MetricRepository(db_session)
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            metric_repo,
            application_config,
        )
        task = task_repo.get_task_by_id(str(task_id))
        metric = Metric._from_request_model(request)
        created_metric = metric_repo.create_metric(metric)
        task_repo.link_metric_to_task(task.id, created_metric.id)

        return created_metric._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.patch(
    "/tasks/{task_id}/metrics/{metric_id}",
    description="Update a task metric.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_task_metric(
    task_id: UUID,
    metric_id: UUID,
    body: UpdateMetricRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
    try:
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task_repo.toggle_task_metric_enabled(str(task_id), str(metric_id), body.enabled)
        updated_task = task_repo.get_task_by_id(str(task_id))
        return updated_task._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@task_management_routes.delete(
    "/tasks/{task_id}/metrics/{metric_id}",
    description="Archive a task metric.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def archive_task_metric(
    task_id: UUID,
    metric_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        metric_repo = MetricRepository(db_session)
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            metric_repo,
            application_config,
        )
        tasks_metrics_repo = TasksMetricsRepository(db_session)
        # task_repo.archive_metric_link(str(task_id), str(metric_id))
        # return Response(status_code=status.HTTP_204_NO_CONTENT)

        task_metrics = tasks_metrics_repo._get_task_metrics_ids(
            str(task_id),
            only_enabled=False,
        )
        if str(metric_id) not in task_metrics:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_UNRELATED_TASK_METRIC,
            )

        task_repo.archive_metric_link(str(task_id), str(metric_id))
        metric_repo.archive_metric(str(metric_id))

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except:
        raise
    finally:
        db_session.close()

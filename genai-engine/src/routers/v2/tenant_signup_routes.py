"""Public tenant signup endpoint (UP-4430).

Mints a fresh (organization, task, TENANT-USER api_key) triple in a single
transaction. Gated by GENAI_ENGINE_DEMO_MODE — returns 404 when disabled so
production deployments cannot distinguish "feature off" from "endpoint not
present."

The demo content (rules fixtures, demo items, chatbot) is intentionally not
created here; that lives on the in-flight feat/create-demo-task branch and
will be layered in when that PR lands.
"""

import logging
import secrets

from arthur_common.models.enums import APIKeysRolesEnum
from arthur_common.models.request_schemas import NewTaskRequest
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.config import Config
from dependencies import get_application_config, get_db_session
from repositories.api_key_repository import ApiKeyRepository
from repositories.metrics_repository import MetricRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from schemas.internal_schemas import ApplicationConfiguration, Task
from schemas.response_schemas import DemoTaskSignupResponse
from utils.utils import public_endpoint

logger = logging.getLogger(__name__)

tenant_signup_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)

_ORG_NAME_RETRIES = 2


@tenant_signup_routes.post(
    "/tenant/signup",
    description=(
        "Public tenant signup. Creates a new organization, a default demo "
        "task scoped to that org, and a TENANT-USER API key with `org_scope` "
        "set to the new org. Returns the four identifiers; the raw `api_key` "
        "value appears only in this response (the DB stores only its hash). "
        "Gated by GENAI_ENGINE_DEMO_MODE — returns 404 when disabled."
    ),
    response_model=DemoTaskSignupResponse,
    tags=["Tenant Signup"],
)
@public_endpoint
def create_tenant_signup(
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> DemoTaskSignupResponse:
    if not Config.demo_mode():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )

    orgs_repo = OrganizationsRepository(db_session)

    db_org = None
    for attempt in range(_ORG_NAME_RETRIES):
        name = f"demo-{secrets.token_hex(4)}"
        try:
            db_org = orgs_repo.create_organization(
                name=name,
                is_system=False,
                commit=False,
            )
            break
        except IntegrityError:
            db_session.rollback()
            if attempt == _ORG_NAME_RETRIES - 1:
                logger.exception(
                    "Could not allocate a unique demo org name after retries",
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not allocate organization",
                )

    assert db_org is not None  # loop guarantees this or we already raised

    try:
        rules_repo = RuleRepository(db_session)
        tasks_repo = TaskRepository(
            db_session,
            rules_repo,
            MetricRepository(db_session),
            application_config,
        )
        task = tasks_repo.create_task(
            Task._from_request_model(
                NewTaskRequest(name="Demo Task", is_agentic=True),
            ),
            org_id=db_org.id,
            commit=False,
        )

        api_key_repo = ApiKeyRepository(db_session)
        api_key = api_key_repo.create_api_key(
            description=f"demo signup for org {db_org.name}",
            roles=[APIKeysRolesEnum.TENANT_USER],
            org_id=db_org.id,
            commit=False,
        )

        db_session.commit()
    except Exception:
        db_session.rollback()
        raise

    return DemoTaskSignupResponse(
        org_id=db_org.id,
        task_id=task.id,
        task_name=task.name,
        api_key=api_key.key,
    )

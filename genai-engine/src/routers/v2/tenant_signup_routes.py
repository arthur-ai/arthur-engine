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

from clients.recaptcha.recaptcha_verifier import RecaptchaEnterpriseVerifier
from config.config import Config
from config.recaptcha_config import RecaptchaConfig
from dependencies import get_application_config, get_db_session
from repositories.api_key_repository import ApiKeyRepository
from repositories.demo_task_repository import DemoTaskRepository
from repositories.metrics_repository import MetricRepository
from repositories.onboarding_repository import OnboardingRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from schemas.internal_schemas import ApplicationConfiguration, Task
from schemas.request_schemas import TenantSignupRequest
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
        "Public tenant signup. Accepts try-it-out onboarding form data, "
        "persists an onboarding submission, and creates a new organization, "
        "a default demo task scoped to that org, and a TENANT-USER API key "
        "with `org_scope` set to the new org. Returns the four identifiers; "
        "the raw `api_key` value appears only in this response (the DB stores "
        "only its hash). Gated by GENAI_ENGINE_DEMO_MODE — returns 404 when "
        "disabled."
    ),
    response_model=DemoTaskSignupResponse,
    tags=["Tenant Signup"],
)
@public_endpoint
def create_tenant_signup(
    body: TenantSignupRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> DemoTaskSignupResponse:
    if not Config.demo_mode():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )

    # Gate on reCAPTCHA Enterprise before doing any provisioning work. When
    # reCAPTCHA is not configured the verifier fails open, so demo/dev flows
    # are unaffected.
    recaptcha_result = RecaptchaEnterpriseVerifier().verify(
        body.recaptcha_token,
        action=RecaptchaConfig.expected_action(),
    )
    if not recaptcha_result.success:
        logger.info(
            "Rejecting tenant signup: reCAPTCHA verification failed (%s)",
            recaptcha_result.reason,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reCAPTCHA verification failed.",
        )

    try:
        # Org-name collisions trigger IntegrityError; SQLAlchemy requires a
        # rollback before the session can be reused, so the retry is its own
        # tight catch — every other failure mode falls through to the outer
        # except, which rolls the entire transaction back.
        db_org = None
        orgs_repo = OrganizationsRepository(db_session)
        for _ in range(_ORG_NAME_RETRIES):
            try:
                db_org = orgs_repo.create_organization(
                    name=f"demo-{secrets.token_hex(4)}",
                    is_system=False,
                    commit=False,
                )
                break
            except IntegrityError:
                db_session.rollback()
        if db_org is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not allocate organization",
            )

        # Reuse the org's `demo-<hex>` name for the task so the two are easy
        # to correlate by eye in dashboards and logs.
        task = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        ).create_task(
            Task._from_request_model(
                NewTaskRequest(name=db_org.name, is_agentic=True),
                org_id=db_org.id,
            ),
            commit=False,
        )

        api_key = ApiKeyRepository(db_session).create_api_key(
            description=f"demo signup for org {db_org.name}",
            roles=[APIKeysRolesEnum.TENANT_USER],
            org_id=db_org.id,
            commit=False,
        )

        DemoTaskRepository(db_session).create_demo_items_for_task(
            task_id=task.id,
            user_id=api_key.id,
            commit=False,
        )

        OnboardingRepository(db_session).create_submission(
            form_variant=body.form_variant,
            form_data=body.form_data,
            commit=False,
        )

        db_session.commit()
    except ValueError as e:
        db_session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to signup tenant: {e}",
        )
    except HTTPException as e:
        db_session.rollback()
        raise e
    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to signup tenant: {e}",
        )

    # create_api_key always populates .key via set_key() before returning;
    # narrow the Optional[str] for the response model.
    assert api_key.key is not None
    return DemoTaskSignupResponse(
        org_id=db_org.id,
        task_id=task.id,
        task_name=task.name,
        api_key=api_key.key,
    )

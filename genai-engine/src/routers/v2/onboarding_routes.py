from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from dependencies import get_db_session
from repositories.onboarding_repository import OnboardingRepository
from routers.route_handler import GenaiEngineRoute
from schemas.request_schemas import OnboardingSubmissionRequest
from schemas.response_schemas import OnboardingSubmissionResponse
from utils.utils import public_endpoint

onboarding_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@onboarding_routes.post(
    "/onboarding/submissions",
    description="Submit try-it-out onboarding form data.",
    response_model=OnboardingSubmissionResponse,
    tags=["Onboarding"],
    status_code=status.HTTP_201_CREATED,
)
@public_endpoint
def create_onboarding_submission(
    body: OnboardingSubmissionRequest,
    db_session: Session = Depends(get_db_session),
) -> OnboardingSubmissionResponse:
    repository = OnboardingRepository(db_session)
    submission = repository.create_submission(
        form_variant=body.form_variant,
        form_data=body.form_data,
    )
    return OnboardingSubmissionResponse(
        id=submission.id,
        created_at=submission.created_at,
    )

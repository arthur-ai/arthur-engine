import logging
import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from db_models.onboarding_models import DatabaseOnboardingSubmission
from schemas.request_schemas import OnboardingTryItOutFormData

logger = logging.getLogger(__name__)


class OnboardingRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_submission(
        self,
        form_variant: Literal["linear", "wizard"] | None,
        form_data: OnboardingTryItOutFormData,
        *,
        commit: bool = True,
    ) -> DatabaseOnboardingSubmission:
        now = datetime.now()
        submission = DatabaseOnboardingSubmission(
            id=uuid.uuid4(),
            form_variant=form_variant,
            form_data=form_data.model_dump(),
            updated_at=now,
        )
        self.db_session.add(submission)
        if commit:
            self.db_session.commit()
            self.db_session.refresh(submission)
        else:
            self.db_session.flush()
        return submission

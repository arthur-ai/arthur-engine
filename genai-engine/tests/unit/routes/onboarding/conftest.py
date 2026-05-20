import uuid
from typing import Generator

import pytest

from db_models.onboarding_models import DatabaseOnboardingSubmission
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def tracked_onboarding_submissions() -> Generator[list[uuid.UUID], None, None]:
    submission_ids: list[uuid.UUID] = []
    yield submission_ids

    db_session = override_get_db_session()
    try:
        for submission_id in submission_ids:
            db_session.query(DatabaseOnboardingSubmission).filter(
                DatabaseOnboardingSubmission.id == submission_id,
            ).delete()
        db_session.commit()
    finally:
        db_session.close()

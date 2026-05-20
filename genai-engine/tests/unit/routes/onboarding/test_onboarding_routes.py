import uuid

import pytest
from fastapi.testclient import TestClient

from db_models.onboarding_models import DatabaseOnboardingSubmission
from tests.clients.base_test_client import app, override_get_db_session

SUBMISSIONS_URL = "/api/v2/onboarding/submissions"

SAMPLE_FORM_DATA = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
    "job_title": "Engineer",
    "company": "Analytical Engines",
    "maturity": "exploring",
    "brings": "evals",
    "brings_other": "",
    "competitors": ["langsmith"],
    "competitor_other": "",
    "attribution": "search",
    "attribution_other": "",
}


def _submit(
    client: TestClient,
    *,
    form_variant: str | None = "linear",
):
    return client.post(
        SUBMISSIONS_URL,
        json={
            "form_variant": form_variant,
            "form_data": SAMPLE_FORM_DATA,
        },
    )


@pytest.mark.unit_tests
def test_submit_onboarding_form_success(tracked_onboarding_submissions):
    client = TestClient(app)

    response = _submit(client)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "created_at" in body
    tracked_onboarding_submissions.append(uuid.UUID(body["id"]))

    db_session = override_get_db_session()
    try:
        submission = (
            db_session.query(DatabaseOnboardingSubmission)
            .filter(DatabaseOnboardingSubmission.id == uuid.UUID(body["id"]))
            .one()
        )
        assert submission.form_variant == "linear"
        assert submission.form_data["email"] == SAMPLE_FORM_DATA["email"]
    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_submit_onboarding_form_no_auth_required():
    client = TestClient(app)
    response = _submit(client)
    assert response.status_code == 201

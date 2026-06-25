"""Tests for the UP-4390 tenant token-credit gate and recorder.

Covers four surfaces:

  - `OrgTokenQuotaStatus.is_exhausted` — pure-logic predicate.
  - `enforce_token_quota` — the gate raised at LLM-call boundaries.
  - `record_org_token_usage` — atomic monotonic counter increment.
  - `extract_token_limit_message` — clean error-message extraction.

Plus an LLMClient-level test confirming the gate short-circuits the call
*before* it ever reaches litellm.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException

from clients.llm.llm_client import LLMClient
from db_models import DatabaseOrganization
from repositories.organizations_repository import (
    TOKEN_LIMIT_EXCEEDED_ERROR_CODE,
    TOKEN_LIMIT_EXCEEDED_MESSAGE,
    OrganizationsRepository,
    OrgTokenQuotaStatus,
    enforce_token_quota,
    extract_token_limit_message,
    record_org_token_usage,
)
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture(scope="function")
def tenant_org():
    """Create a tenant org with a fresh limit/usage state per test."""
    db_session = override_get_db_session()
    org = DatabaseOrganization(
        id=uuid.uuid4(),
        name=f"test-tenant-{uuid.uuid4().hex[:8]}",
        is_system=False,
        tokens_limit=None,
        tokens_used=0,
        created_at=datetime.now(),
    )
    db_session.add(org)
    db_session.commit()
    yield org
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == org.id,
    ).delete()
    db_session.commit()


# ---------------------------------------------------------------------------
# OrgTokenQuotaStatus.is_exhausted
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "limit,used,expected",
    [
        (None, 0, False),               # unmetered org
        (None, 1_000_000, False),       # unmetered, plenty of usage
        (1000, 0, False),               # fresh tenant
        (1000, 999, False),             # under the limit
        (1000, 1000, True),             # exactly at the limit
        (1000, 1001, True),             # over the limit
    ],
)
def test_is_exhausted(limit, used, expected):
    status = OrgTokenQuotaStatus(tokens_limit=limit, tokens_used=used)
    assert status.is_exhausted is expected


# ---------------------------------------------------------------------------
# enforce_token_quota
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_enforce_token_quota_passes_for_unmetered_org(tenant_org):
    """Orgs with tokens_limit IS NULL bypass the gate regardless of usage."""
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": None, "tokens_used": 999_999_999})
    db_session.commit()

    # Should not raise.
    enforce_token_quota(tenant_org.id)


@pytest.mark.unit_tests
def test_enforce_token_quota_passes_under_limit(tenant_org):
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 1000, "tokens_used": 500})
    db_session.commit()

    enforce_token_quota(tenant_org.id)


@pytest.mark.unit_tests
def test_enforce_token_quota_raises_429_at_limit(tenant_org):
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 1000, "tokens_used": 1000})
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        enforce_token_quota(tenant_org.id)

    assert exc_info.value.status_code == 429
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["error_code"] == TOKEN_LIMIT_EXCEEDED_ERROR_CODE
    assert detail["message"] == TOKEN_LIMIT_EXCEEDED_MESSAGE
    assert detail["tokens_limit"] == 1000
    assert detail["tokens_used"] == 1000


@pytest.mark.unit_tests
def test_enforce_token_quota_raises_429_over_limit(tenant_org):
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 1000, "tokens_used": 1500})
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        enforce_token_quota(tenant_org.id)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["tokens_used"] == 1500


@pytest.mark.unit_tests
def test_enforce_token_quota_passes_for_unknown_org():
    """Unknown org IDs fall through — billing isn't the place to surface 404s."""
    enforce_token_quota(uuid.uuid4())


# ---------------------------------------------------------------------------
# record_org_token_usage
# ---------------------------------------------------------------------------


def _read_tokens_used(org_id: uuid.UUID) -> int:
    db_session = override_get_db_session()
    return (
        db_session.query(DatabaseOrganization.tokens_used)
        .filter(DatabaseOrganization.id == org_id)
        .scalar()
    )


@pytest.mark.unit_tests
def test_record_org_token_usage_increments_atomically(tenant_org):
    """Repeated increments accumulate; SQL does the arithmetic server-side."""
    record_org_token_usage(tenant_org.id, 100)
    assert _read_tokens_used(tenant_org.id) == 100

    record_org_token_usage(tenant_org.id, 250)
    assert _read_tokens_used(tenant_org.id) == 350

    record_org_token_usage(tenant_org.id, 1)
    assert _read_tokens_used(tenant_org.id) == 351


@pytest.mark.unit_tests
@pytest.mark.parametrize("amount", [0, -1, -1000])
def test_record_org_token_usage_no_op_for_non_positive(tenant_org, amount):
    """Zero / negative amounts must never decrement — guards against
    accounting on LLM responses that didn't include a usage block."""
    record_org_token_usage(tenant_org.id, 500)
    assert _read_tokens_used(tenant_org.id) == 500

    record_org_token_usage(tenant_org.id, amount)
    assert _read_tokens_used(tenant_org.id) == 500


@pytest.mark.unit_tests
def test_record_org_token_usage_swallows_unknown_org_silently():
    """Recording against a non-existent org must not raise — the LLM call
    already happened; we don't want a billing-write failure to break the
    user-facing response."""
    record_org_token_usage(uuid.uuid4(), 100)  # nothing to assert; not raising is the assertion


# ---------------------------------------------------------------------------
# extract_token_limit_message
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_extract_token_limit_message_pulls_clean_message_from_429():
    exc = HTTPException(
        status_code=429,
        detail={
            "error_code": TOKEN_LIMIT_EXCEEDED_ERROR_CODE,
            "message": "Custom credit-limit message",
            "tokens_limit": 1000,
            "tokens_used": 1500,
        },
    )
    assert extract_token_limit_message(exc) == "Custom credit-limit message"


@pytest.mark.unit_tests
def test_extract_token_limit_message_returns_none_for_non_429():
    """500/400/etc shouldn't be confused with a credit-limit error."""
    assert extract_token_limit_message(HTTPException(500, "boom")) is None
    assert extract_token_limit_message(HTTPException(400, "bad request")) is None


@pytest.mark.unit_tests
def test_extract_token_limit_message_returns_none_for_other_429_shapes():
    """A 429 that isn't ours (e.g. provider rate-limit wrapped elsewhere)
    must not be misread as TOKEN_LIMIT_EXCEEDED."""
    exc = HTTPException(429, {"error_code": "PROVIDER_RATE_LIMIT", "message": "x"})
    assert extract_token_limit_message(exc) is None


@pytest.mark.unit_tests
def test_extract_token_limit_message_returns_none_for_non_http_exception():
    assert extract_token_limit_message(ValueError("nope")) is None
    assert extract_token_limit_message(RuntimeError("nope")) is None


# ---------------------------------------------------------------------------
# LLMClient gate — confirms the gate short-circuits before litellm is called
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.litellm.completion")
def test_llm_client_completion_blocks_exhausted_org(
    mock_completion,
    tenant_org,
):
    """When the gate trips, litellm.completion must never be invoked —
    the request never reaches the upstream provider."""
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 100, "tokens_used": 100})
    db_session.commit()

    llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="test-key")

    with pytest.raises(HTTPException) as exc_info:
        llm_client.completion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
            org_id=tenant_org.id,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error_code"] == TOKEN_LIMIT_EXCEEDED_ERROR_CODE
    mock_completion.assert_not_called()


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_llm_client_completion_passes_when_under_limit(
    mock_completion,
    mock_cost,
    tenant_org,
):
    """A tenant under their limit should reach litellm unimpeded."""
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 1000, "tokens_used": 100})
    db_session.commit()

    from litellm.types.utils import ModelResponse

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {"content": "ok"}
    mock_response.usage = None  # skip the post-call record path
    mock_completion.return_value = mock_response
    mock_cost.return_value = 0.0

    llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="test-key")
    response = llm_client.completion(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": "hi"}],
        org_id=tenant_org.id,
    )

    assert response.response is mock_response
    mock_completion.assert_called_once()


@pytest.mark.unit_tests
@pytest.mark.asyncio
@patch("clients.llm.llm_client.litellm.acompletion")
async def test_llm_client_acompletion_blocks_exhausted_org(
    mock_acompletion,
    tenant_org,
):
    """Same gate must fire on the async path before litellm is awaited."""
    db_session = override_get_db_session()
    db_session.query(DatabaseOrganization).filter(
        DatabaseOrganization.id == tenant_org.id,
    ).update({"tokens_limit": 50, "tokens_used": 1000})
    db_session.commit()

    llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="test-key")

    with pytest.raises(HTTPException) as exc_info:
        await llm_client.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
            org_id=tenant_org.id,
        )

    assert exc_info.value.status_code == 429
    mock_acompletion.assert_not_called()

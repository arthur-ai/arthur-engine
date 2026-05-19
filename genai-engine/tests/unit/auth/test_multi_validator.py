"""Tests for MultiMethodValidator.

The single test that distinguishes admin (cross-org) from tenant (single-org)
callers throughout the rest of multi-tenancy is request.state.org_scope. This
suite asserts it is set correctly on all three auth paths:

  - API key with org_id = NULL (admin) → org_scope = None
  - API key with org_id = <uuid> (tenant) → org_scope = <uuid>
  - JWT request (admin) → org_scope = None
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from arthur_common.models.common_schemas import AuthUserRole

from auth.multi_validator import MultiMethodValidator
from schemas.internal_schemas import User


def _make_request() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace())


def _run(validator: MultiMethodValidator, request, *, api_key_user, jwt_user):
    import asyncio

    api_key_client = MagicMock()
    api_key_client.validate.return_value = api_key_user
    jwk_client = MagicMock()
    jwk_client.validate.return_value = jwt_user

    return asyncio.run(
        validator.validate_api_multi_auth(
            request=request,
            jwk_client=jwk_client,
            token="test-token",
            api_key_validator_client=api_key_client,
            db_session=MagicMock(),
            creds=None,
        ),
    )


@pytest.mark.unit_tests
def test_api_key_admin_sets_org_scope_none():
    """Admin API key (org_id=NULL) → request.state.org_scope is None."""
    user = User(
        id="admin-key-id",
        email="",
        roles=[AuthUserRole(name="ORG_ADMIN", description="", composite=True)],
        org_scope=None,
    )
    request = _make_request()
    validator = MultiMethodValidator(api_key_validator_creators=[])

    result = _run(validator, request, api_key_user=user, jwt_user=None)

    assert result is user
    assert request.state.user_id == "admin-key-id"
    assert request.state.org_scope is None


@pytest.mark.unit_tests
def test_api_key_tenant_sets_org_scope_to_org_id():
    """Tenant API key (org_id=X) → request.state.org_scope = X."""
    org_id = uuid.uuid4()
    user = User(
        id="tenant-key-id",
        email="",
        roles=[AuthUserRole(name="TENANT-USER", description="", composite=True)],
        org_scope=org_id,
    )
    request = _make_request()
    validator = MultiMethodValidator(api_key_validator_creators=[])

    result = _run(validator, request, api_key_user=user, jwt_user=None)

    assert result is user
    assert request.state.user_id == "tenant-key-id"
    assert request.state.org_scope == org_id


@pytest.mark.unit_tests
def test_jwt_path_sets_org_scope_none():
    """JWT user → request.state.org_scope = None (v1 design)."""
    user = User(
        id="jwt-sub",
        email="user@example.com",
        roles=[AuthUserRole(name="ORG_ADMIN", description="", composite=True)],
    )
    request = _make_request()
    validator = MultiMethodValidator(api_key_validator_creators=[])

    # API key validation returns None so we fall through to JWT path.
    result = _run(validator, request, api_key_user=None, jwt_user=user)

    assert result is user
    assert request.state.user_id == "jwt-sub"
    assert request.state.org_scope is None

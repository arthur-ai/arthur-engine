"""GET /users/me returns identity+org info (UP-4426).

Tests exercise the handler body directly via __wrapped__ (which the
@public_endpoint decorator exposes through functools.wraps) so we don't
need the full FastAPI client stack — sidesteps the tests/unit/routes/
autouse client fixture which currently errors on tasks.org_id NOT NULL.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.common_schemas import AuthUserRole
from fastapi import HTTPException

from routers.user_routes import get_me
from schemas.internal_schemas import User
from schemas.response_schemas import MeResponse


def _role(name: str) -> AuthUserRole:
    return AuthUserRole(id="0", name=name, description="DUMMY", composite=True)


def _user(
    user_id: str = "user-123",
    roles: list[str] | None = None,
    org_scope: uuid.UUID | None = None,
) -> User:
    return User(
        id=user_id,
        email="x@example.com",
        roles=[_role(r) for r in (roles or [])],
        org_scope=org_scope,
    )


def _call_me(current_user: User | None) -> MeResponse:
    # get_me is a sync handler wrapped by @public_endpoint; __wrapped__ is the
    # original sync function (functools.wraps), so we can invoke it directly.
    return get_me.__wrapped__(
        current_user=current_user,
        db_session=MagicMock(),
    )


@pytest.mark.unit_tests
def test_get_me_unauthenticated_returns_401():
    with pytest.raises(HTTPException) as exc:
        _call_me(current_user=None)
    assert exc.value.status_code == 401


@pytest.mark.unit_tests
def test_get_me_admin_api_key_has_null_org():
    """Admin API key path: org_scope is None, no org lookup, org=null in response."""
    user = _user(user_id="admin-uuid", roles=["ORG-ADMIN"], org_scope=None)
    with patch(
        "routers.user_routes.OrganizationsRepository",
    ) as mock_repo_cls:
        result = _call_me(current_user=user)
        mock_repo_cls.assert_not_called()

    assert result.user_id == "admin-uuid"
    assert result.roles == ["ORG-ADMIN"]
    assert result.org_scope is None
    assert result.org is None


@pytest.mark.unit_tests
def test_get_me_tenant_api_key_populates_org():
    """Tenant API key path: org_scope set, org lookup runs, org populated."""
    org_id = uuid.uuid4()
    user = _user(user_id="tenant-uuid", roles=["TENANT-USER"], org_scope=org_id)

    db_org = MagicMock()
    db_org.id = org_id
    db_org.name = "demo-a3f9b2c1"

    with patch(
        "routers.user_routes.OrganizationsRepository",
    ) as mock_repo_cls:
        mock_repo_cls.return_value.get_organization_by_id.return_value = db_org
        result = _call_me(current_user=user)
        mock_repo_cls.return_value.get_organization_by_id.assert_called_once_with(
            org_id,
        )

    assert result.user_id == "tenant-uuid"
    assert result.roles == ["TENANT-USER"]
    assert result.org_scope == org_id
    assert result.org is not None
    assert result.org.id == org_id
    assert result.org.name == "demo-a3f9b2c1"


@pytest.mark.unit_tests
def test_get_me_jwt_user_has_null_org():
    """JWT path: org_scope is None (set only by API-key validator), org=null."""
    user = _user(
        user_id="keycloak-sub-abc",
        roles=["ORG-ADMIN", "default-roles-genai-engine"],
        org_scope=None,
    )
    with patch(
        "routers.user_routes.OrganizationsRepository",
    ) as mock_repo_cls:
        result = _call_me(current_user=user)
        mock_repo_cls.assert_not_called()

    assert result.user_id == "keycloak-sub-abc"
    assert set(result.roles) == {"ORG-ADMIN", "default-roles-genai-engine"}
    assert result.org_scope is None
    assert result.org is None


@pytest.mark.unit_tests
def test_get_me_tenant_with_missing_org_record_returns_null_org():
    """Defensive: if org_scope refers to a deleted org, org=null, no crash."""
    org_id = uuid.uuid4()
    user = _user(user_id="orphan-uuid", roles=["TENANT-USER"], org_scope=org_id)

    with patch(
        "routers.user_routes.OrganizationsRepository",
    ) as mock_repo_cls:
        mock_repo_cls.return_value.get_organization_by_id.return_value = None
        result = _call_me(current_user=user)

    assert result.org_scope == org_id
    assert result.org is None

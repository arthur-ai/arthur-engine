import uuid
from unittest.mock import MagicMock

import pytest
from arthur_common.models.common_schemas import AuthUserRole
from fastapi import HTTPException

from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from utils import constants
from utils.users import (
    enforce_org_scope,
    enforce_query_org_scope,
    get_user_info_from_payload,
    permission_checker,
)

pytest_plugins = ("pytest_asyncio",)


def _user_with_role(role: str) -> User:
    return User(
        id="dummy_id",
        email="foo@example.com",
        roles=[AuthUserRole(id="0", name=role, description="DUMMY", composite=True)],
    )


# Frozensets a TENANT-USER must be able to satisfy (per UP-4428).
TENANT_USER_ALLOWED = [
    PermissionLevelsEnum.TASK_READ,
    PermissionLevelsEnum.TASK_WRITE,
    PermissionLevelsEnum.INFERENCE_READ,
    PermissionLevelsEnum.INFERENCE_WRITE,
    PermissionLevelsEnum.FEEDBACK_READ,
    PermissionLevelsEnum.FEEDBACK_WRITE,
    PermissionLevelsEnum.DEFAULT_RULES_READ,
    PermissionLevelsEnum.USAGE_READ,
    PermissionLevelsEnum.MODEL_PROVIDER_READ,
]

# Admin-only frozensets a TENANT-USER must be rejected by.
TENANT_USER_DISALLOWED = [
    PermissionLevelsEnum.TRACES_WRITE,
    PermissionLevelsEnum.API_KEY_READ,
    PermissionLevelsEnum.API_KEY_WRITE,
    PermissionLevelsEnum.USER_READ,
    PermissionLevelsEnum.USER_WRITE,
    PermissionLevelsEnum.MODEL_PROVIDER_WRITE,
    PermissionLevelsEnum.DEFAULT_RULES_WRITE,
    PermissionLevelsEnum.APP_CONFIG_READ,
    PermissionLevelsEnum.APP_CONFIG_WRITE,
    PermissionLevelsEnum.ROTATE_SECRETS,
    PermissionLevelsEnum.PASSWORD_RESET,
]


@pytest.mark.parametrize(
    "payload, expected_user",
    [
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
            },
            User(id="dummy_id", email="foo@example.com", roles=[]),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
            },
            User(id="dummy_id", email="foo@example.com", roles=[], first_name="Foo"),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "family_name": "Bar",
            },
            User(id="dummy_id", email="foo@example.com", roles=[], last_name="Bar"),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
                "family_name": "Bar",
            },
            User(
                id="dummy_id",
                email="foo@example.com",
                roles=[],
                first_name="Foo",
                last_name="Bar",
            ),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
                "family_name": "Bar",
                "realm_access": {
                    "roles": [
                        "offline_access",
                        "uma_authorization",
                        "default-roles-genai-engine",
                    ],
                },
            },
            User(
                id="dummy_id",
                email="foo@example.com",
                first_name="Foo",
                last_name="Bar",
                roles=[
                    AuthUserRole(
                        id="0",
                        name="offline_access",
                        description="DUMMY",
                        composite=True,
                    ),
                    AuthUserRole(
                        id="1",
                        name="uma_authorization",
                        description="DUMMY",
                        composite=True,
                    ),
                    AuthUserRole(
                        id="2",
                        name="default-roles-genai-engine",
                        description="DUMMY",
                        composite=True,
                    ),
                ],
            ),
        ),
    ],
)
@pytest.mark.unit_tests
def test_get_user_info_from_payload(payload, expected_user):
    user = get_user_info_from_payload(payload)

    assert user == expected_user


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker():
    @permission_checker(set(["TEST"]))
    def x(current_user) -> bool:
        return True

    result = await x(
        current_user=User(
            id="dummy_id",
            email="foo@example.com",
            first_name="Foo",
            last_name="Bar",
            roles=[
                AuthUserRole(id="0", name="test", description="DUMMY", composite=True),
            ],
        ),
    )
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker_user_unauthorized():
    @permission_checker(set(["TEST"]))
    def x(current_user) -> bool:
        return True

    with pytest.raises(HTTPException) as error_info:
        _ = await x(current_user=None)
    assert error_info.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker_user_forbidden():
    @permission_checker(set(["ANOTHER_TEST"]))
    def x(current_user) -> bool:
        return True

    with pytest.raises(HTTPException) as error_info:
        _ = await x(
            current_user=User(
                id="dummy_id",
                email="foo@example.com",
                first_name="Foo",
                last_name="Bar",
                roles=[
                    AuthUserRole(
                        id="0",
                        name="test",
                        description="DUMMY",
                        composite=True,
                    ),
                ],
            ),
        )
    assert error_info.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.unit_tests
@pytest.mark.parametrize("permission", TENANT_USER_ALLOWED, ids=lambda p: p.name)
async def test_tenant_user_passes_allowed_permissions(permission):
    @permission_checker(permission.value)
    def x(current_user) -> bool:
        return True

    result = await x(current_user=_user_with_role(constants.TENANT_USER))
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit_tests
@pytest.mark.parametrize("permission", TENANT_USER_DISALLOWED, ids=lambda p: p.name)
async def test_tenant_user_rejected_for_admin_only_permissions(permission):
    @permission_checker(permission.value)
    def x(current_user) -> bool:
        return True

    with pytest.raises(HTTPException) as error_info:
        await x(current_user=_user_with_role(constants.TENANT_USER))
    assert error_info.value.status_code == 403


@pytest.mark.unit_tests
def test_traces_write_excludes_tenant_user():
    """POST /api/v1/traces is admin-only in v1 (per design §2 Non-Goals)."""
    assert constants.TENANT_USER not in PermissionLevelsEnum.TRACES_WRITE.value
    assert constants.ORG_ADMIN in PermissionLevelsEnum.TRACES_WRITE.value
    assert constants.TASK_ADMIN in PermissionLevelsEnum.TRACES_WRITE.value


@pytest.mark.asyncio
@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "permission",
    list(PermissionLevelsEnum),
    ids=lambda p: p.name,
)
async def test_org_admin_passes_every_permission(permission):
    """Regression: ORG-ADMIN keeps satisfying every permission set."""

    @permission_checker(permission.value)
    def x(current_user) -> bool:
        return True

    result = await x(current_user=_user_with_role(constants.ORG_ADMIN))
    assert result is True


# -------------------------------------------------------------------------
# Org-scope enforcement decorators (Patterns A, B, D — UP-4425).
# -------------------------------------------------------------------------


O1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
O2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
T1A = uuid.UUID("aaaaaaa1-0000-0000-0000-000000000000")  # belongs to O1
T1B = uuid.UUID("aaaaaaa2-0000-0000-0000-000000000000")  # belongs to O1
T2A = uuid.UUID("bbbbbbb1-0000-0000-0000-000000000000")  # belongs to O2


def _admin() -> User:
    return User(
        id="admin-id",
        email="admin@example.com",
        roles=[
            AuthUserRole(
                id="0",
                name=constants.ORG_ADMIN,
                description="DUMMY",
                composite=True,
            ),
        ],
        org_scope=None,
    )


def _tenant(org_id: uuid.UUID) -> User:
    return User(
        id="tenant-id",
        email="tenant@example.com",
        roles=[
            AuthUserRole(
                id="0",
                name=constants.TENANT_USER,
                description="DUMMY",
                composite=True,
            ),
        ],
        org_scope=org_id,
    )


def _mock_session_with_task_org_map(
    task_to_org: dict[uuid.UUID, uuid.UUID],
) -> MagicMock:
    """Build a MagicMock SQLAlchemy session that responds to:

    - select(DatabaseTask.org_id).where(DatabaseTask.id == <id>)   -> scalar_one_or_none
    - select(DatabaseTask.id).where(DatabaseTask.org_id == <org>)  -> scalars()
    """
    session = MagicMock()

    def execute_side_effect(stmt):
        # Read the WHERE clause params without rendering literals; UUID
        # types don't always have a literal processor for the default dialect.
        compiled = stmt.compile()
        params = dict(compiled.params)
        compiled_str = str(compiled)
        result = MagicMock()
        if "tasks.org_id" in compiled_str and "WHERE tasks.id" in compiled_str:
            # SELECT tasks.org_id WHERE tasks.id = :id_1
            requested_id = next(iter(params.values()))
            org = task_to_org.get(uuid.UUID(str(requested_id)))
            result.scalar_one_or_none.return_value = org
        elif "tasks.id" in compiled_str and "WHERE tasks.org_id" in compiled_str:
            # SELECT tasks.id WHERE tasks.org_id = :org_id_1
            requested_org = str(next(iter(params.values())))
            ids = [t for t, o in task_to_org.items() if str(o) == requested_org]
            result.scalars.return_value = iter(ids)
        return result

    session.execute.side_effect = execute_side_effect
    return session


# Pattern A — @enforce_org_scope


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_org_scope_admin_passthrough():
    @enforce_org_scope()
    def handler(task_id, db_session, current_user) -> bool:
        return True

    result = await handler(task_id=T2A, db_session=MagicMock(), current_user=_admin())
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_org_scope_tenant_match():
    @enforce_org_scope()
    def handler(task_id, db_session, current_user) -> bool:
        return True

    session = _mock_session_with_task_org_map({T1A: O1, T1B: O1, T2A: O2})
    result = await handler(task_id=T1A, db_session=session, current_user=_tenant(O1))
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_org_scope_tenant_mismatch_returns_404():
    @enforce_org_scope()
    def handler(task_id, db_session, current_user) -> bool:
        return True

    session = _mock_session_with_task_org_map({T1A: O1, T2A: O2})
    with pytest.raises(HTTPException) as exc:
        await handler(task_id=T2A, db_session=session, current_user=_tenant(O1))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_org_scope_tenant_task_missing_returns_404():
    @enforce_org_scope()
    def handler(task_id, db_session, current_user) -> bool:
        return True

    session = _mock_session_with_task_org_map({})  # no tasks
    with pytest.raises(HTTPException) as exc:
        await handler(task_id=T1A, db_session=session, current_user=_tenant(O1))
    assert exc.value.status_code == 404


# Pattern D — @enforce_query_org_scope


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_query_org_scope_admin_passthrough():
    @enforce_query_org_scope()
    def handler(task_ids, db_session, current_user) -> list:
        return task_ids

    result = await handler(
        task_ids=[T2A], db_session=MagicMock(), current_user=_admin()
    )
    assert result == [T2A]


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_query_org_scope_tenant_match():
    @enforce_query_org_scope()
    def handler(task_ids, db_session, current_user) -> list:
        return task_ids

    session = _mock_session_with_task_org_map({T1A: O1, T1B: O1, T2A: O2})
    result = await handler(
        task_ids=[T1A, T1B], db_session=session, current_user=_tenant(O1)
    )
    assert {str(t) for t in result} == {str(T1A), str(T1B)}


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_query_org_scope_tenant_outside_returns_403():
    @enforce_query_org_scope()
    def handler(task_ids, db_session, current_user) -> list:
        return task_ids

    session = _mock_session_with_task_org_map({T1A: O1, T2A: O2})
    with pytest.raises(HTTPException) as exc:
        await handler(task_ids=[T2A], db_session=session, current_user=_tenant(O1))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_enforce_query_org_scope_tenant_empty_injects_org_tasks():
    captured: dict = {}

    @enforce_query_org_scope()
    def handler(task_ids, db_session, current_user) -> bool:
        captured["task_ids"] = task_ids
        return True

    session = _mock_session_with_task_org_map({T1A: O1, T1B: O1, T2A: O2})
    await handler(task_ids=[], db_session=session, current_user=_tenant(O1))

    # Should have been expanded to the caller's org's tasks (in some order).
    # The decorator stores ids as strings for downstream query filters.
    assert {str(t) for t in captured["task_ids"]} == {str(T1A), str(T1B)}

"""POST /api/v2/tenant/signup public tenant signup (UP-4430).

Tests exercise the handler body directly via __wrapped__ (which the
@public_endpoint decorator exposes through functools.wraps) so we don't
need the full FastAPI client stack — sidesteps the tests/unit/routes/
autouse client fixture which currently errors on tasks.org_id NOT NULL.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from routers.v2.tenant_signup_routes import create_tenant_signup


def _call(db_session: MagicMock, application_config: MagicMock = None):
    # create_tenant_signup is a sync handler wrapped by @public_endpoint;
    # __wrapped__ is the original sync function.
    return create_tenant_signup.__wrapped__(
        db_session=db_session,
        application_config=application_config or MagicMock(),
    )


@pytest.fixture
def fake_org():
    return SimpleNamespace(id=uuid.uuid4(), name="demo-deadbeef")


@pytest.fixture
def fake_task():
    # Task shares the org's demo-<hex> name in the new flow; the fake
    # returned by the mocked repo just needs the same shape downstream code
    # accesses (id + name).
    return SimpleNamespace(id=str(uuid.uuid4()), name="demo-deadbeef")


@pytest.fixture
def fake_api_key():
    key = SimpleNamespace(key="base64-token-value")
    return key


@pytest.mark.unit_tests
def test_create_tenant_signup_demo_mode_off_returns_404():
    with patch(
        "routers.v2.tenant_signup_routes.Config.demo_mode",
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            _call(db_session=MagicMock())
    assert exc.value.status_code == 404


@pytest.mark.unit_tests
def test_create_tenant_signup_happy_path(fake_org, fake_task, fake_api_key):
    db_session = MagicMock()

    with (
        patch(
            "routers.v2.tenant_signup_routes.Config.demo_mode",
            return_value=True,
        ),
        patch(
            "routers.v2.tenant_signup_routes.OrganizationsRepository",
        ) as orgs_cls,
        patch(
            "routers.v2.tenant_signup_routes.TaskRepository",
        ) as tasks_cls,
        patch(
            "routers.v2.tenant_signup_routes.ApiKeyRepository",
        ) as keys_cls,
    ):
        orgs_cls.return_value.create_organization.return_value = fake_org
        tasks_cls.return_value.create_task.return_value = fake_task
        keys_cls.return_value.create_api_key.return_value = fake_api_key

        result = _call(db_session=db_session)

    # response shape matches DemoTaskSignupResponse
    assert result.org_id == fake_org.id
    assert result.task_id == fake_task.id
    assert result.task_name == fake_task.name
    assert result.api_key == fake_api_key.key

    # org was created with the expected name pattern + is_system=False + commit=False
    create_org_call = orgs_cls.return_value.create_organization.call_args
    assert create_org_call.kwargs["is_system"] is False
    assert create_org_call.kwargs["commit"] is False
    assert create_org_call.kwargs["name"].startswith("demo-")
    # secrets.token_hex(4) = 8 hex chars → name is exactly "demo-" + 8 chars
    assert len(create_org_call.kwargs["name"]) == len("demo-") + 8

    # task was created with org_id threaded onto the Task schema + commit=False
    create_task_call = tasks_cls.return_value.create_task.call_args
    assert create_task_call.kwargs["commit"] is False
    # the Task passed to create_task carries org_id from the new org AND
    # reuses the org's demo-<hex> name (so the two correlate visually).
    task_arg = create_task_call.args[0]
    assert task_arg.org_id == fake_org.id
    assert task_arg.name == fake_org.name

    # api key was created with TENANT-USER role, org_id, commit=False
    create_key_call = keys_cls.return_value.create_api_key.call_args
    assert create_key_call.kwargs["org_id"] == fake_org.id
    assert create_key_call.kwargs["commit"] is False
    roles = create_key_call.kwargs["roles"]
    assert len(roles) == 1
    assert roles[0].value == "TENANT-USER"

    # the route committed the transaction once after all entities flushed
    db_session.commit.assert_called_once()
    db_session.rollback.assert_not_called()


@pytest.mark.unit_tests
def test_create_tenant_signup_retries_org_name_once_on_collision(
    fake_org, fake_task, fake_api_key
):
    db_session = MagicMock()

    integrity_err = IntegrityError("INSERT", {}, Exception("unique violation"))

    with (
        patch(
            "routers.v2.tenant_signup_routes.Config.demo_mode",
            return_value=True,
        ),
        patch(
            "routers.v2.tenant_signup_routes.OrganizationsRepository",
        ) as orgs_cls,
        patch(
            "routers.v2.tenant_signup_routes.TaskRepository",
        ) as tasks_cls,
        patch(
            "routers.v2.tenant_signup_routes.ApiKeyRepository",
        ) as keys_cls,
    ):
        # First attempt collides, second succeeds.
        orgs_cls.return_value.create_organization.side_effect = [
            integrity_err,
            fake_org,
        ]
        tasks_cls.return_value.create_task.return_value = fake_task
        keys_cls.return_value.create_api_key.return_value = fake_api_key

        result = _call(db_session=db_session)

    assert orgs_cls.return_value.create_organization.call_count == 2
    # two distinct random names were attempted
    name1 = orgs_cls.return_value.create_organization.call_args_list[0].kwargs["name"]
    name2 = orgs_cls.return_value.create_organization.call_args_list[1].kwargs["name"]
    assert name1 != name2
    # rollback was called once (for the failed attempt), then commit once at the end
    assert db_session.rollback.call_count == 1
    db_session.commit.assert_called_once()
    assert result.org_id == fake_org.id


@pytest.mark.unit_tests
def test_create_tenant_signup_returns_500_after_two_name_collisions():
    db_session = MagicMock()
    integrity_err = IntegrityError("INSERT", {}, Exception("unique violation"))

    with (
        patch(
            "routers.v2.tenant_signup_routes.Config.demo_mode",
            return_value=True,
        ),
        patch(
            "routers.v2.tenant_signup_routes.OrganizationsRepository",
        ) as orgs_cls,
        patch(
            "routers.v2.tenant_signup_routes.TaskRepository",
        ),
        patch(
            "routers.v2.tenant_signup_routes.ApiKeyRepository",
        ),
    ):
        orgs_cls.return_value.create_organization.side_effect = [
            integrity_err,
            integrity_err,
        ]
        with pytest.raises(HTTPException) as exc:
            _call(db_session=db_session)

    assert exc.value.status_code == 500
    assert orgs_cls.return_value.create_organization.call_count == 2
    db_session.commit.assert_not_called()


@pytest.mark.unit_tests
def test_create_tenant_signup_rolls_back_when_api_key_step_fails(fake_org, fake_task):
    """If api_key creation fails after org+task are flushed, the whole
    transaction rolls back — no orphan org, no orphan task."""
    db_session = MagicMock()
    boom = RuntimeError("api key minting blew up")

    with (
        patch(
            "routers.v2.tenant_signup_routes.Config.demo_mode",
            return_value=True,
        ),
        patch(
            "routers.v2.tenant_signup_routes.OrganizationsRepository",
        ) as orgs_cls,
        patch(
            "routers.v2.tenant_signup_routes.TaskRepository",
        ) as tasks_cls,
        patch(
            "routers.v2.tenant_signup_routes.ApiKeyRepository",
        ) as keys_cls,
    ):
        orgs_cls.return_value.create_organization.return_value = fake_org
        tasks_cls.return_value.create_task.return_value = fake_task
        keys_cls.return_value.create_api_key.side_effect = boom

        with pytest.raises(RuntimeError):
            _call(db_session=db_session)

    db_session.rollback.assert_called_once()
    db_session.commit.assert_not_called()

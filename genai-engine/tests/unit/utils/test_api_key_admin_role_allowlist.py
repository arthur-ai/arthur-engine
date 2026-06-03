"""Admin POST /auth/api_keys/ must refuse TENANT-USER roles (UP-4428).

TENANT-USER keys are mintable only via the public tenant signup flow (UP-4430);
the admin-facing create endpoint must reject them explicitly so an ORG_ADMIN
cannot bypass the signup path.

This is a route-level allowlist test that calls the handler with the
permission_checker decorator stripped via __wrapped__, so we exercise the
body of create_api_key without needing the full FastAPI app stack.
"""

from unittest.mock import MagicMock

import pytest
from arthur_common.models.enums import APIKeysRolesEnum
from arthur_common.models.request_schemas import NewApiKeyRequest
from fastapi import HTTPException

from routers.api_key_routes import create_api_key
from utils import constants


def _call_handler(roles):
    """Invoke create_api_key's body, bypassing the @permission_checker decorator."""
    handler = getattr(create_api_key, "__wrapped__", create_api_key)
    return handler(
        new_api_key=NewApiKeyRequest(description="forbidden", roles=roles),
        db_session=MagicMock(),
        current_user=MagicMock(),
    )


@pytest.mark.unit_tests
def test_admin_create_rejects_tenant_user_role():
    """ORG_ADMIN minting roles=[TENANT-USER] must get 400."""
    with pytest.raises(HTTPException) as exc:
        _call_handler([APIKeysRolesEnum.TENANT_USER])
    assert exc.value.status_code == 400
    assert constants.TENANT_USER in exc.value.detail


@pytest.mark.unit_tests
def test_admin_create_rejects_tenant_user_alongside_other_role():
    """Mixed roles list with TENANT-USER still gets 400 — partial reject is enough."""
    with pytest.raises(HTTPException) as exc:
        _call_handler(
            [APIKeysRolesEnum.TASK_ADMIN, APIKeysRolesEnum.TENANT_USER],
        )
    assert exc.value.status_code == 400

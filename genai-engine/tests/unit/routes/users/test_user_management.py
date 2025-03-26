import pytest
from schemas.common_schemas import UserPermission
from schemas.enums import UserPermissionAction, UserPermissionResource
from tests.clients.base_test_client import GenaiEngineTestClientBase
from utils.utils import is_api_only_mode_enabled

all_permissions = set(
    [
        UserPermission(action=action, resource=resource)
        for action, resource in zip(
            UserPermissionAction.values(),
            UserPermissionResource.values(),
        )
    ],
)


@pytest.mark.unit_tests
@pytest.mark.skipif(
    is_api_only_mode_enabled(),
    reason="Skipping test because GENAI_ENGINE_API_ONLY_MODE_ENABLED is set to enabled",
)
def test_reset_password_not_authorized(client: GenaiEngineTestClientBase):
    status_code, response = client.reset_password("non-existing-id", "ZXCasd123!@#")
    assert status_code == 403
    assert response == {"detail": "You can't reset password for this user."}

from clients.auth.abc_keycloak_client import ABCAuthClient
from arthur_common.models.common_schemas import UserPermission
from arthur_common.models.request_schemas import CreateUserRequest


class MockAuthClient(ABCAuthClient):
    def check_user_permissions(self, user_id: str, permission: UserPermission):
        return True

    def create_user(self, request: CreateUserRequest) -> None:
        return super().create_user(request)

from clients.auth.abc_keycloak_client import ABCAuthClient
from schemas.common_schemas import UserPermission
from schemas.request_schemas import CreateUserRequest


class MockAuthClient(ABCAuthClient):
    def check_user_permissions(self, user_id: str, permission: UserPermission):
        return True

    def create_user(self, request: CreateUserRequest) -> None:
        return super().create_user(request)

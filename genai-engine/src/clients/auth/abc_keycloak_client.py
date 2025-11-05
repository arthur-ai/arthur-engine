from abc import ABC, abstractmethod

from arthur_common.models.common_schemas import UserPermission

from schemas.internal_schemas import User


class ABCAuthClient(ABC):
    @abstractmethod
    def create_user(self, email: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_user_permissions(
        self,
        user_id: str,
        permission_request: UserPermission,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def search_users(self, search_string: str, page: int, page_size: int) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str):
        raise NotImplementedError

    @abstractmethod
    def bootstrap_genai_engine_keycloak(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset_password(self, user_id: str, new_password: str) -> None:
        raise NotImplementedError

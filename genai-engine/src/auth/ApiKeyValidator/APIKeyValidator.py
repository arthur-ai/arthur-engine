from abc import ABC, abstractmethod

from schemas.internal_schemas import User


class APIKeyValidator(ABC):
    @abstractmethod
    def api_key_is_valid(self, key: str) -> User | None:
        raise NotImplementedError

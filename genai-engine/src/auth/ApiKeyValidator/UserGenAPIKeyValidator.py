import logging

import bcrypt
from cachetools import TTLCache

from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from repositories.api_key_repository import ApiKeyRepository
from schemas.internal_schemas import User

logger = logging.getLogger(__name__)


class UserGenAPIKeyValidator(APIKeyValidator):
    def __init__(
        self,
        api_key_cache: TTLCache[str, User],
        api_key_repo: ApiKeyRepository,
    ):
        self.api_key_cache = api_key_cache
        self.api_key_repo = api_key_repo

    def api_key_is_valid(self, api_key: str) -> User | None:
        # checking the key exists in cache
        if cached_key := self.api_key_cache.get(api_key):
            logger.debug("API key used for authentication [cached value]")
            return cached_key
        try:
            if db_api_key := self.api_key_repo.validate_key(api_key):
                self.api_key_cache[api_key] = db_api_key.get_user_representation()
                return self.api_key_cache[api_key]
            return None
        except AttributeError:
            db_api_keys = self.api_key_repo.get_all_active_api_keys()
            for db_api_key in db_api_keys:
                if db_api_key.key_hash and bcrypt.checkpw(
                    api_key.encode("utf-8"),
                    db_api_key.key_hash.encode("utf-8"),
                ):
                    self.api_key_cache[api_key] = db_api_key.get_user_representation()
                    return self.api_key_cache[api_key]
        return None

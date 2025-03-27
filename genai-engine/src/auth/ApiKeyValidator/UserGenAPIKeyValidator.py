import logging

import bcrypt
from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from cachetools import TTLCache
from repositories.api_key_repository import ApiKeyRepository
from schemas.internal_schemas import User

logger = logging.getLogger(__name__)


class UserGenAPIKeyValidator(APIKeyValidator):
    def __init__(
        self,
        api_key_cache: TTLCache[str, dict],
        api_key_repo: ApiKeyRepository,
    ):
        self.api_key_cache = api_key_cache
        self.api_key_repo = api_key_repo

    def api_key_is_valid(self, api_key: str) -> User | None:
        # checking the key exists in cache
        if cached_key := self.api_key_cache.get(api_key):
            logger.debug("API key used for authentication [cached value]")
            return cached_key

        # get all active keys from db
        db_api_keys = self.api_key_repo.get_all_active_api_keys()

        # iterate over all the active keys to check if the user provided key is valid
        for key in db_api_keys:
            # check if the stored hash matches for the api key sent by the user. bcrypt library allows us to do this without hasing the user supplied key again.
            if bcrypt.checkpw(api_key.encode("utf-8"), key.key_hash.encode("utf-8")):
                self.api_key_cache[api_key] = (
                    key.get_user_representation()
                )  # Store in cache for future use
                logger.debug("API key used for authentication")
                return self.api_key_cache[api_key]
        return None

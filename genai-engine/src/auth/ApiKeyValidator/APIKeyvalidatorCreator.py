# mypy: ignore-errors
from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from auth.ApiKeyValidator.MasterAPIKeyValidator import MasterAPIKeyValidator
from auth.ApiKeyValidator.UserGenAPIKeyValidator import UserGenAPIKeyValidator
from cachetools import TTLCache
from config.config import Config
from repositories.api_key_repository import ApiKeyRepository
from sqlalchemy.orm import Session


class APIKeyValidatorCreator:
    def __init__(self, validator_type: APIKeyValidatorType):
        self.validator_type = validator_type

    def get_api_key_validator(
        self,
        api_key_cache: TTLCache,
        db: Session,
    ) -> APIKeyValidator:
        match self.validator_type:
            case APIKeyValidatorType.MASTER:
                return MasterAPIKeyValidator([Config.api_key()])
            case APIKeyValidatorType.USER_GEN:
                return UserGenAPIKeyValidator(api_key_cache, ApiKeyRepository(db))

import logging

from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from cachetools import TTLCache
from schemas.custom_exceptions import (
    BadCredentialsException,
    UnableCredentialsException,
)
from schemas.internal_schemas import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class APIKeyValidatorClient:
    def __init__(self, api_key_cache: TTLCache):
        self.api_key_cache = api_key_cache

    def validate(
        self,
        api_key_validator_creators: list[APIKeyValidatorCreator],
        api_key: str,
        db_session: Session,
    ) -> User | None:
        """
        This function takes in a list of APIKeyValidatorCreator and uses them to validate the api key.
        :param api_key_validator_creators: List of APIKeyValidatorCreator. This will create teh appropriate
        validators for APi keys nad use them to validate the key
        :type api_key_validator_creators: list[APIKeyValidatorCreator]
        :param api_key: api key tp validate
        :type api_key: str

        :return: True if valid api key
        :raise BadCredentialsException: if the key is not valid
        :raise UnableCredentialsException: If any other error happens
        """
        api_key_validators: list[APIKeyValidator] = [
            creator.get_api_key_validator(self.api_key_cache, db_session)
            for creator in api_key_validator_creators
        ]

        for validator in api_key_validators:
            try:
                if user := validator.api_key_is_valid(api_key):
                    return user
            except Exception as e:
                logger.error("API Key validator error: %s" % str(e))
                raise UnableCredentialsException

        raise BadCredentialsException

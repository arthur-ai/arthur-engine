# create an authentication schema for authenticated endpoints
from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from auth.multi_validator import MultiMethodValidator

api_key_validator_creators = [
    APIKeyValidatorCreator(APIKeyValidatorType.USER_GEN),
    APIKeyValidatorCreator(APIKeyValidatorType.MASTER),
]
multi_validator = MultiMethodValidator(api_key_validator_creators)

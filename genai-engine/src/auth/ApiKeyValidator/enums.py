from enum import Enum


class APIKeyValidatorType(str, Enum):
    MASTER = "master"
    USER_GEN = "user_generated"

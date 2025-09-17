from enum import Enum

from utils import constants


class BaseEnum(str, Enum):
    @classmethod
    def values(self):
        values: list[str] = [e for e in self]
        return values

    def __str__(self):
        return self.value


class RuleDataType(str, Enum):
    REGEX = "regex"
    KEYWORD = "keyword"
    JSON = "json"
    TOXICITY_THRESHOLD = "toxicity_threshold"
    PII_THRESHOLD = "pii_confidence_threshold"
    PII_ALLOW_LIST = "allow_list"
    PII_DISABLED_PII = "disabled_pii_entities"
    HINT = "hint"


class RuleScoringMethod(str, Enum):
    # Better term for regex / keywords?
    BINARY = "binary"


class ToolClassEnum(int, Enum):
    INCORRECT = 0
    CORRECT = 1
    NA = 2

    def __str__(self):
        return str(self.value)


class DocumentType(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"


class DocumentStorageEnvironment(str, Enum):
    AWS = "aws"
    AZURE = "azure"


# These are keys in config key : value pairs
class ApplicationConfigurations(str, Enum):
    CHAT_TASK_ID = "chat_task_id"
    DOCUMENT_STORAGE_ENV = "document_storage_environment"
    DOCUMENT_STORAGE_BUCKET_NAME = "document_storage_bucket_name"
    DOCUMENT_STORAGE_ROLE_ARN = "document_storage_assumable_role_arn"
    DOCUMENT_STORAGE_CONTAINER_NAME = "document_storage_container_name"
    DOCUMENT_STORAGE_CONNECTION_STRING = "document_storage_connection_string"
    MAX_LLM_RULES_PER_TASK_COUNT = "max_llm_rules_per_task_count"


class ClaimClassifierResultEnum(str, Enum):
    CLAIM = "claim"
    NONCLAIM = "nonclaim"
    DIALOG = "dialog"


class PermissionLevelsEnum(Enum):
    API_KEY_READ = frozenset(
        [constants.ORG_ADMIN, constants.ORG_AUDITOR, constants.ADMIN_KEY],
    )
    API_KEY_WRITE = frozenset([constants.ORG_ADMIN, constants.ADMIN_KEY])
    APP_CONFIG_READ = frozenset([constants.ORG_ADMIN, constants.ORG_AUDITOR])
    APP_CONFIG_WRITE = frozenset([constants.ORG_ADMIN])
    CHAT_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.CHAT_USER,
        ],
    )
    DEFAULT_RULES_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.DEFAULT_RULE_ADMIN,
        ],
    )
    DEFAULT_RULES_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.DEFAULT_RULE_ADMIN,
            constants.TASK_ADMIN,
        ],
    )
    FEEDBACK_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
        ],
    )
    FEEDBACK_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
            constants.CHAT_USER,
        ],
    )
    INFERENCE_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
        ],
    )
    INFERENCE_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
            constants.CHAT_USER,
        ],
    )
    PASSWORD_RESET = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.DEFAULT_RULE_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
            constants.CHAT_USER,
        ],
    )
    TASK_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
        ],
    )
    TASK_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
        ],
    )
    USAGE_READ = frozenset([constants.ORG_ADMIN, constants.ORG_AUDITOR])
    USER_READ = frozenset([constants.ORG_ADMIN, constants.ORG_AUDITOR])
    USER_WRITE = frozenset([constants.ORG_ADMIN])

class ComparisonOperatorEnum(str, Enum):
    EQUAL = "eq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"

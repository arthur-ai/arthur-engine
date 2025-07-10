from enum import Enum

from utils import constants


class BaseEnum(str, Enum):
    @classmethod
    def values(self):
        values: list[str] = [e for e in self]
        return values

    def __str__(self):
        return self.value


# If you added values here, did you update permission_mappings.py?
class UserPermissionAction(BaseEnum, str, Enum):
    CREATE = "create"
    READ = "read"


# If you added values here, did you update permission_mappings.py?
class UserPermissionResource(BaseEnum, str, Enum):
    PROMPTS = "prompts"
    RESPONSES = "responses"
    RULES = "rules"
    TASKS = "tasks"


class PaginationSortMethod(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class RuleType(str, Enum):
    KEYWORD = "KeywordRule"
    MODEL_HALLUCINATION_V2 = "ModelHallucinationRuleV2"
    MODEL_SENSITIVE_DATA = "ModelSensitiveDataRule"
    PII_DATA = "PIIDataRule"
    PROMPT_INJECTION = "PromptInjectionRule"
    REGEX = "RegexRule"
    TOXICITY = "ToxicityRule"

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


class RuleScope(str, Enum):
    DEFAULT = "default"
    TASK = "task"


class RuleScoringMethod(str, Enum):
    # Better term for regex / keywords?
    BINARY = "binary"


class MetricType(str, Enum):
    QUERY_RELEVANCE = "QueryRelevance"
    RESPONSE_RELEVANCE = "ResponseRelevance"
    TOOL_SELECTION = "ToolSelection"

    def __str__(self):
        return self.value


class ToolClassEnum(int, Enum):
    WRONG_TOOL_SELECTED = 0
    CORRECT_TOOL_SELECTED = 1
    NO_TOOL_SELECTED = 2

    def __str__(self):
        return str(self.value)


class MetricDataType(str, Enum):
    QUERY_RELEVANCE = "query_relevance"
    RESPONSE_RELEVANCE = "response_relevance"
    TOOL_SELECTION = "tool_selection"


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


class InferenceFeedbackTarget(str, Enum):
    CONTEXT = "context"
    RESPONSE_RESULTS = "response_results"
    PROMPT_RESULTS = "prompt_results"


class RuleResultEnum(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    SKIPPED = "Skipped"
    UNAVAILABLE = "Unavailable"
    PARTIALLY_UNAVAILABLE = "Partially Unavailable"
    MODEL_NOT_AVAILABLE = "Model Not Available"

    def __str__(self):
        return self.value


class ToxicityViolationType(str, Enum):
    BENIGN = "benign"
    HARMFUL_REQUEST = "harmful_request"
    TOXIC_CONTENT = "toxic_content"
    PROFANITY = "profanity"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value


# Note: These string values are not arbitrary and map to Presidio entity types: https://microsoft.github.io/presidio/supported_entities/
class PIIEntityTypes(BaseEnum, str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    URL = "URL"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"

    @classmethod
    def to_string(cls):
        return ",".join(member.value for member in cls)


class TokenUsageScope(str, Enum):
    RULE_TYPE = "rule_type"
    TASK = "task"

    def __str__(self):
        return self.value


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


class APIKeysRolesEnum(Enum):
    DEFAULT_RULE_ADMIN: str = constants.DEFAULT_RULE_ADMIN
    TASK_ADMIN: str = constants.TASK_ADMIN
    VALIDATION_USER: str = constants.VALIDATION_USER
    ORG_AUDITOR: str = constants.ORG_AUDITOR
    ORG_ADMIN: str = constants.ORG_ADMIN

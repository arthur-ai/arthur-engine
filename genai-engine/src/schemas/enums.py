from enum import Enum

from utils import constants


class BaseEnum(str, Enum):
    @classmethod
    def values(self) -> list[str]:
        values: list[str] = [e for e in self]
        return values

    def __str__(self) -> str:
        return str(self.value)


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


# These are keys in config key : value pairs
class ApplicationConfigurations(str, Enum):
    DEFAULT_CURRENCY = "default_currency"
    MAX_LLM_RULES_PER_TASK_COUNT = "max_llm_rules_per_task_count"
    TRACE_RETENTION_DAYS = "trace_retention_days"
    CHATBOT_BLACKLIST_ENDPOINTS = "chatbot_blacklist_endpoints"


class ClaimClassifierResultEnum(str, Enum):
    CLAIM = "claim"
    NONCLAIM = "nonclaim"
    DIALOG = "dialog"


class TestRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    ERROR = "error"


class PermissionLevelsEnum(Enum):
    API_KEY_READ = frozenset(
        [constants.ORG_ADMIN, constants.ORG_AUDITOR, constants.ADMIN_KEY],
    )
    API_KEY_WRITE = frozenset([constants.ORG_ADMIN, constants.ADMIN_KEY])
    APP_CONFIG_READ = frozenset([constants.ORG_ADMIN, constants.ORG_AUDITOR])
    APP_CONFIG_WRITE = frozenset([constants.ORG_ADMIN])
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
            constants.TENANT_USER,
        ],
    )
    FEEDBACK_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    FEEDBACK_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
            constants.TENANT_USER,
        ],
    )
    INFERENCE_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    INFERENCE_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
            constants.TENANT_USER,
        ],
    )
    PASSWORD_RESET = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.DEFAULT_RULE_ADMIN,
            constants.TASK_ADMIN,
            constants.VALIDATION_USER,
        ],
    )
    TASK_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    TASK_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    TRACES_WRITE = frozenset(
        [
            constants.ORG_ADMIN,
            constants.TASK_ADMIN,
        ],
    )
    USAGE_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TENANT_USER,
        ],
    )
    USER_READ = frozenset([constants.ORG_ADMIN, constants.ORG_AUDITOR])
    USER_WRITE = frozenset([constants.ORG_ADMIN])
    DATASET_WRITE = frozenset(
        [constants.ORG_ADMIN, constants.TASK_ADMIN, constants.TENANT_USER],
    )
    DATASET_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    ROTATE_SECRETS = frozenset(
        [constants.ORG_ADMIN],
    )
    MODEL_PROVIDER_WRITE = frozenset(
        [constants.ORG_ADMIN, constants.TASK_ADMIN],
    )
    MODEL_PROVIDER_READ = frozenset(
        [
            constants.ORG_ADMIN,
            constants.ORG_AUDITOR,
            constants.TASK_ADMIN,
            constants.TENANT_USER,
        ],
    )
    # Read of the chatbot system task's model + prompt config. Admin-only:
    # this is system-wide config, not tenant data.
    CHATBOT_CONFIG_READ = frozenset(
        [constants.ORG_ADMIN, constants.ORG_AUDITOR],
    )
    # Write of the chatbot system task's config + clearing chatbot history.
    # Admin-only: chatbot is a system task; tenants have no business writing
    # its config or clearing its history.
    CHATBOT_CONFIG_WRITE = frozenset(
        [constants.ORG_ADMIN],
    )
    # Trigger a global agent discovery + polling cycle. Admin-only: this
    # discovers and polls every eligible task in the engine.
    AGENT_POLLING_ADMIN = frozenset(
        [constants.ORG_ADMIN, constants.TASK_ADMIN],
    )
    # Read of telemetry that isn't tied to any task (orphaned root spans,
    # cross-task debug views). Admin-only — tenants have no use for this
    # data and seeing it could expose other tenants' span names.
    TELEMETRY_ADMIN_READ = frozenset(
        [constants.ORG_ADMIN, constants.ORG_AUDITOR, constants.TASK_ADMIN],
    )
    # Run validation using only default (non-task-scoped) rules. Covers the
    # deprecated `/api/v2/validate_prompt` endpoint. Admin-only because there
    # is no task to enforce org scope against — tenants use the task-scoped
    # `/api/v2/tasks/{task_id}/validate_*` endpoints instead.
    DEFAULT_VALIDATION_RUN = frozenset(
        [constants.ORG_ADMIN, constants.TASK_ADMIN],
    )


class SecretType(str, Enum):
    MODEL_PROVIDER = "model_provider"
    RAG_PROVIDER = "rag_provider"


class RagProviderAuthenticationMethodEnum(str, Enum):
    API_KEY_AUTHENTICATION = "api_key"


class RagAPIKeyAuthenticationProviderEnum(str, Enum):
    WEAVIATE = "weaviate"


class ConnectionCheckOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class RagProviderEnum(str, Enum):
    WEAVIATE = "weaviate"


class RagSearchKind(str, Enum):
    VECTOR_SIMILARITY_TEXT_SEARCH = "vector_similarity_text_search"
    KEYWORD_SEARCH = "keyword_search"
    HYBRID_SEARCH = "hybrid_search"


class AgenticExperimentGeneratorType(str, Enum):
    UUID = "uuid"
    SESSION_ID = "session_id"


class SSEEventType(str, Enum):
    """Server-Sent Event types"""

    FINAL_RESPONSE = "final_response"
    ERROR = "error"
    SEARCH_COMPLETE = "search_complete"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    HISTORY_REPLACE = "history_replace"


class LLMMetadataSortField(str, Enum):
    """Sort field options for the LLM evals/prompts metadata list endpoints."""

    NAME = "name"
    LATEST_VERSION_CREATED_AT = "latest_version_created_at"


class TaskAnalyticsBucketSize(BaseEnum):
    """Time bucket granularity for task analytics time-series metrics."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class EvalKind(str, Enum):
    """Discriminator for all eval types stored in the llm_evals table."""

    LLM_AS_A_JUDGE = "llm_as_a_judge"
    PII = "pii"
    PII_V1 = "pii_v1"
    TOXICITY = "toxicity"
    PROMPT_INJECTION = "prompt_injection"

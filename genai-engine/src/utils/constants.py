import math
import os

##################################################################
# Application Server
GENAI_ENGINE_INGRESS_URI_ENV_VAR = "GENAI_ENGINE_INGRESS_URI"
GENAI_ENGINE_ADMIN_KEY_ENV_VAR = "GENAI_ENGINE_ADMIN_KEY"
GENAI_ENGINE_ENVIRONMENT_ENV_VAR = "GENAI_ENGINE_ENVIRONMENT"
GENAI_ENGINE_LOG_LEVEL_ENV_VAR = "GENAI_ENGINE_LOG_LEVEL"
ALLOW_ADMIN_KEY_GENERAL_ACCESS_ENV_VAR = "ALLOW_ADMIN_KEY_GENERAL_ACCESS"
MAX_API_KEYS_ENV_VAR = "MAX_API_KEYS"
GENAI_ENGINE_API_ONLY_MODE_ENABLED_ENV_VAR = "GENAI_ENGINE_API_ONLY_MODE_ENABLED"
GENAI_ENGINE_AGENTIC_UI_ENABLED_ENV_VAR = "GENAI_ENGINE_AGENTIC_UI_ENABLED"
GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR = "GENAI_ENGINE_ENABLE_PERSISTENCE"
GENAI_ENGINE_THREAD_POOL_MAX_WORKERS_ENV_VAR = "GENAI_ENGINE_THREAD_POOL_MAX_WORKERS"
DEFAULT_THREAD_POOL_MAX_WORKERS = math.floor(os.cpu_count() / 2) + 1
DEFAULT_PAGE_SIZE = 5  # Reduced for trace-level pagination
MAX_PAGE_SIZE = 5000

##################################################################
# Postgres
POSTGRES_USE_SSL_ENV_VAR = "POSTGRES_USE_SSL"

##################################################################
# Auth Environment Variables
GENAI_ENGINE_AUTH_CLIENT_SECRET_ENV_VAR = "AUTH_CLIENT_SECRET"
GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR = "AUTH_CLIENT_ID"
GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR = "KEYCLOAK_HOST_URI"
GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR = "KEYCLOAK_REALM"
GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR = "APP_SECRET_KEY"
GENAI_ENGINE_KEYCLOAK_VERIFY_SSL_ENV_VAR = "KEYCLOAK_VERIFY_SSL"

##################################################################
# OpenAI
GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS_ENV_VAR = (
    "GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS"
)
GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD_ENV_VAR = (
    "GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD"
)
GENAI_ENGINE_OPENAI_PROVIDER_ENV_VAR = "GENAI_ENGINE_OPENAI_PROVIDER"
GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR = (
    "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
)

##################################################################
# Rules
DEFAULT_MAX_LLM_RULES_PER_TASK = 3
DEFAULT_TOXICITY_RULE_THRESHOLD = 0.5
GENAI_ENGINE_TOXICITY_HARMFUL_REQUESTS_CHUNK_SIZE_ENV_VAR = (
    "GENAI_ENGINE_TOXICITY_HARMFUL_REQUESTS_CHUNK_SIZE"
)
GENAI_ENGINE_TOXICITY_MAX_CHUNK_SIZE_SIZE_ENV_VAR = (
    "GENAI_ENGINE_TOXICITY_MAX_CHUNK_SIZE"
)
GENAI_ENGINE_TOXICITY_MODEL_BATCH_SIZE_ENV_VAR = (
    "GENAI_ENGINE_TOXICITY_MODEL_BATCH_SIZE"
)
GENAI_ENGINE_USE_PII_MODEL_V2_ENV_VAR = "GENAI_ENGINE_USE_PII_MODEL_V2"
DEFAULT_PII_RULE_CONFIDENCE_SCORE_THRESHOLD = 0
GENAI_ENGINE_SENSITIVE_DATA_CHECK_MAX_TOKEN_LIMIT_ENV_VAR = (
    "GENAI_ENGINE_SENSITIVE_DATA_CHECK_MAX_TOKEN_LIMIT"
)
GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT_ENV_VAR = (
    "GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT"
)
GENAI_ENGINE_TOXICITY_CHECK_MAX_TOKEN_LIMIT_ENV_VAR = (
    "GENAI_ENGINE_TOXICITY_CHECK_MAX_TOKEN_LIMIT"
)
ENABLE_RELEVANCE_MODELS_ENV_VAR = "ENABLE_RELEVANCE_MODELS"

##################################################################
# Chat
GENAI_ENGINE_CHAT_ENABLED_ENV_VAR = "CHAT_ENABLED"
GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR = (
    "GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS"
)
MAX_CHAT_CONTEXT_LIMIT = 2048
MAX_CHAT_HISTORY_CONTEXT = 512

##################################################################
# String Constants
HALLUCINATION_CLAIMS_INVALID_MESSAGE = (
    "At least one claim was unsupported by the context."
)
HALLUCINATION_CLAIMS_VALID_MESSAGE = "All claims were supported by the context!"
HALLUCINATION_NO_CLAIMS_MESSAGE = "No claims were evaluated for hallucination."

HALLUCINATION_AT_LEAST_ONE_INDETERMINATE_LABEL_MESSAGE = "At least one claim was not fully evaluated due to an error with an upstream LLM response."
HALLUCINATION_INDETERMINATE_LABEL_MESSAGE = "This claim was sent for hallucination evaluation, but an error occurred due to an upstream LLM response."

ERROR_RULE_NOT_FOUND = "Rule %s does not exist"
ERROR_CANNOT_VALIDATE_INFERENCE_TWICE = (
    "This inference's response has already been validated. You cannot validate it again"
)
ERROR_INVALID_REGEX = "Invalid regex: %s"
ERROR_TOO_MANY_LLM_RULES_PER_TASK = "Only %d LLM rules (i.e. hallucination, sensitive data) inluding the default rules are allowed to be enabled on a task at a time. Please review the rules already enabled for this task."
ERROR_GENAI_ENGINE_RATE_LIMIT_EXCEEDED = "GenAI Engine rate limit exceeded"
ERROR_DEFAULT_RULE_ENGINE = "This rule could not be evaluated"
ERROR_TOKEN_LIMIT_EXCEEDED = (
    "Token limit exceeded. Please reduce the size of the input."
)
ERROR_INVALID_DOCUMENT_TYPE = (
    "Invalid document type. Must be one of application/pdf, text/csv, text/plain."
)
ERROR_UNCAUGHT_GENERIC = "Something went wrong."
ERROR_UNRELATED_TASK_RULE = "This rule id is not associated with this task."
ERROR_UNRELATED_TASK_METRIC = "This metric id is not associated with this task."
ERROR_NON_AGENTIC_TASK_METRIC = "Only agentic tasks can have metrics."
ERROR_INVALID_QUERY_PROMPT_STATUS = (
    "prompt_status parameter cannot contain values outside ('Pass', 'Fail')"
)
ERROR_INVALID_QUERY_RESPONSE_STATUS = (
    "response_status parameter cannot contain values outside ('Pass', 'Fail')"
)
ERROR_INVALID_INFERENCE_FEEDBACK_TARGET = "target parameter cannot contain values outside ('context', 'response_results', 'prompt_results')"
ERROR_USER_ALREADY_EXISTS = "User %s already exists."
ERROR_ROLE_DOESNT_EXIST = "Role %s does not exist."
ERROR_USER_NOT_FOUND = "User %s not found."
ERROR_ACTION_AND_RESOURCE_REQUIRED = "Both Action and Resource must be supplied."
ERROR_AUTHENTICATION_REQUIRED = "User must be authenticated"
ERROR_CANNOT_DELETE_DEFAULT_RULE = (
    "Default rules cannot be deleted. To disable a default rule, use patch instead."
)

ERROR_PAGE_SIZE_TOO_LARGE = (
    f"Invalid page size, must be greater than 0 and less than {MAX_PAGE_SIZE}"
)
HALLUCINATION_VALID_CLAIM_REASON = "No hallucination detected!"
HALLUCINATION_NONEVALUATION_EXPLANATION = "Not evaluated for hallucination."

HALLUCINATION_EXPLANATION_TRUE_POSITIVE_SIGNALS = [
    "not supported",
    "no support",
    "unsupported",
    "no evidence",
    "lack of evidence",
    "incorrect",
    "not correct",
    "context does not mention",
]
HALLUCINATION_EXPLANATION_FALSE_POSITIVE_SIGNALS = ["support", "correct", "evidence"]

KEYWORD_NO_MATCHES_MESSAGE = "No keywords found in text."
KEYWORD_MATCHES_MESSAGE = "Keywords found in text."

REGEX_NO_MATCHES_MESSAGE = "No regex match in text."
REGEX_MATCHES_MESSAGE = "Regex match in text."

# Make sure the policy and description match
GENAI_ENGINE_KEYCLOAK_PASSWORD_LENGTH = 12
GENAI_ENGINE_KEYCLOAK_PASSWORD_POLICY = f"length({GENAI_ENGINE_KEYCLOAK_PASSWORD_LENGTH}) and specialChars(1) and upperCase(1) and lowerCase(1)"
ERROR_PASSWORD_POLICY_NOT_MET = f"Password should be at least {GENAI_ENGINE_KEYCLOAK_PASSWORD_LENGTH} characters and contain at least one special character, lowercase character, and uppercase character."
ERROR_DEFAULT_METRICS_ENGINE = "This metric could not be evaluated"
##################################################################
# Headers
RESPONSE_TRACE_ID_HEADER = "x-trace-id"
X_CONTENT_TYPE_OPTIONS_HEADER = "X-Content-Type-Options"
X_FRAME_OPTIONS_HEADER = "X-Frame-Options"
STRICT_TRANSPORT_SECURITY_HEADER = "Strict-Transport-Security"
CONTENT_SECURITY_POLICY_HEADER = "Content-Security-Policy"
CROSS_ORIGIN_OPENER_POLICY_HEADER = "Cross-Origin-Opener-Policy"
CROSS_ORIGIN_EMBEDDER_POLICY_HEADER = "Cross-Origin-Embedder-Policy"
CROSS_ORIGIN_RESOURCE_POLICY_HEADER = "Cross-Origin-Resource-Policy"
PERMISSIONS_POLICY_HEADER = "Permissions-Policy"
REFERRER_POLICY_HEADER = "Referrer-Policy"

##################################################################
# APM
NEWRELIC_ENABLED_ENV_VAR = "NEWRELIC_ENABLED"
NEWRELIC_APP_NAME_ENV_VAR = "NEW_RELIC_APP_NAME"
NEWRELIC_CUSTOM_METRIC_RULE_FAILURES = "custom.rule_failures"

##################################################################
# RBAC
CHAT_USER: str = "CHAT-USER"
ORG_ADMIN: str = "ORG-ADMIN"
TASK_ADMIN: str = "TASK-ADMIN"
DEFAULT_RULE_ADMIN: str = "DEFAULT-RULE-ADMIN"
VALIDATION_USER: str = "VALIDATION-USER"
ORG_AUDITOR: str = "ORG-AUDITOR"
ADMIN_KEY: str = "ADMIN-KEY"

LEGACY_KEYCLOAK_ROLES: dict[str, str] = {
    "genai_engine_admin_user": TASK_ADMIN,
}

##################################################################
# Telemetry
TELEMETRY_ENABLED_ENV_VAR = "TELEMETRY_ENABLED"

##################################################################
# CONTEXT WINDOW LENGTHS

# Currently OpenAI doesn't offer a way of retrieving the context window length for a specific model programmatically
# Should that change, the below should be updated to use the new method

OPENAI_MODEL_CONTEXT_WINDOW_LENGTHS = {
    "o4-mini": 200000,
    "o4-mini-2025-04-16": 200000,
    "o3": 200000,
    "o3-2025-04-16": 200000,
    "o3-mini": 200000,
    "o3-mini-2025-01-31": 200000,
    "o1": 200000,
    "o1-2024-12-17": 200000,
    "o1-pro": 200000,
    "o1-pro-2025-03-19": 200000,
    "o1-preview": 128000,
    "o1-preview-2024-09-12": 128000,
    "o1-mini": 128000,
    "o1-mini-2024-09-12": 128000,
    "gpt-4.1": 1047576,
    "gpt-4.1-2025-04-14": 1047576,
    "gpt-4.1-nano": 1047576,
    "gpt-4.1-nano-2025-04-14": 1047576,
    "gpt-4.1-mini": 1047576,
    "gpt-4.1-mini-2025-04-14": 1047576,
    "gpt-4o": 128000,
    "gpt-4o-2024-08-06": 128000,
    "gpt-4o-2024-11-20": 128000,
    "gpt-4o-2024-05-13": 128000,
    "gpt-4o-audio-preview": 128000,
    "gpt-4o-audio-preview-2024-12-17": 128000,
    "gpt-4o-audio-preview-2025-06-03": 128000,
    "gpt-4o-audio-preview-2024-10-01": 128000,
    "gpt-4o-mini-audio-preview": 128000,
    "gpt-4o-mini-audio-preview-2024-12-17": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4o-mini-2024-07-18": 128000,
    "gpt-4o-realtime-preview": 128000,
    "gpt-4o-realtime-preview-2024-12-17": 128000,
    "gpt-4o-realtime-preview-2025-06-03": 128000,
    "gpt-4o-realtime-preview-2024-10-01": 128000,
    "gpt-4o-mini-realtime-preview": 128000,
    "gpt-4o-mini-realtime-preview-2024-12-17": 128000,
    "gpt-4o-search-preview": 128000,
    "gpt-4o-search-preview-2025-03-11": 128000,
    "gpt-4o-mini-search-preview": 128000,
    "gpt-4o-mini-search-preview-2025-03-11": 128000,
    "chatgpt-4o-latest": 128000,
    "computer-use-preview": 8192,
    "computer-use-preview-2025-03-11": 8192,
    "codex-mini-latest": 200000,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-2024-04-09": 128000,
    "gpt-4-0125-preview": 128000,
    "gpt-4": 8192,
    "gpt-4-0613": 8192,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-0125": 16385,
    "gpt-3.5-turbo-1106": 16385,
    "gpt-3.5-turbo-instruct": 4096,
}

AZURE_OPENAI_MODEL_CONTEXT_WINDOW_LENGTHS = {
    "o4-mini": 200000,
    "o4-mini-2025-04-16": 200000,
    "o3-mini": 200000,
    "o3-mini-alpha": 200000,
    "o3-mini-alpha-2024-12-17": 200000,
    "o3-mini-2025-01-31": 200000,
    "o1-2024-12-17": 200000,
    "o1-pro": 200000,
    "o1-pro-2025-03-19": 200000,
    "o1-mini-2024-09-12": 128000,
    "gpt-4.1": 1047576,
    "gpt-4.1-mini": 1047576,
    "gpt-4.1-nano": 1047576,
    "gpt-4.1-2025-04-14": 1047576,
    "gpt-4.1-mini-2025-04-14": 1047576,
    "gpt-4.1-nano-2025-04-14": 1047576,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4o-2024-05-13": 128000,
    "gpt-4o-2024-08-06": 128000,
    "gpt-4o-mini-2024-07-18": 128000,
    "gpt-4o-2024-11-20": 128000,
    "gpt-4o-audio-mai": 128000,
    "gpt-4o-realtime-preview": 128000,
    "gpt-4o-mini-realtime-preview-2024-12-17": 128000,
    "gpt-4o-realtime-preview-2024-12-17": 128000,
    "gpt-4o-canvas-2024-09-25": 128000,
    "gpt-4o-audio-preview-2024-10-01": 128000,
    "gpt-4o-audio-preview-2024-12-17": 128000,
    "gpt-4o-mini-audio-preview-2024-12-17": 128000,
    "gpt-4": 128000,
    "gpt-4-32k": 32768,
    "gpt-4-0125-Preview": 128000,
    "gpt-4-1106-Preview": 128000,
    "gpt-4-0314": 8192,
    "gpt-4-0613": 8192,
    "gpt-4-32k-0314": 32768,
    "gpt-4-32k-0613": 32768,
    "gpt-4-vision-preview": 128000,
    "gpt-4-turbo-2024-04-09": 128000,
    "gpt-4-turbo-jp": 128000,
    "gpt-35-turbo-0301": 4096,
    "gpt-35-turbo-0613": 4096,
    "gpt-35-turbo-1106": 16385,
    "gpt-35-turbo-0125": 16385,
    "gpt-35-turbo-instruct-0914": 4096,
    "gpt-35-turbo-16k-0613": 16385,
    "gpt-35-turbo": 16385,
    "gpt-35-turbo-instruct": 4096,
    "gpt-35-turbo-16k": 16385,
}

##################################################################
# MODELS THAT SUPPORT STRUCTURED OUTPUTS

OPENAI_STRUCTURED_OUTPUT_MODELS = set(
    [
        "o4-mini",
        "o4-mini-2025-04-16",
        "o3",
        "o3-2025-04-16",
        "o3-mini",
        "o3-mini-2025-01-31",
        "o1",
        "o1-2024-12-17",
        "o1-pro",
        "o1-pro-2025-03-19",
        "o1-preview",
        "o1-preview-2024-09-12",
        "gpt-4.1",
        "gpt-4.1-2025-04-14",
        "gpt-4.1-nano",
        "gpt-4.1-nano-2025-04-14",
        "gpt-4.1-mini",
        "gpt-4.1-mini-2025-04-14",
        "gpt-4o",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-11-20",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-search-preview",
        "gpt-4o-search-preview-2025-03-11",
        "gpt-4o-mini-search-preview",
        "gpt-4o-mini-search-preview-2025-03-11",
        "codex-mini-latest",
    ],
)

AZURE_OPENAI_STRUCTURED_OUTPUT_MODELS = set(
    [
        "o4-mini",
        "o4-mini-2025-04-16",
        "o3-mini",
        "o3-mini-alpha",
        "o3-mini-alpha-2024-12-17",
        "o3-mini-2025-01-31",
        "o1-2024-12-17",
        "o1-pro",
        "o1-pro-2025-03-19",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4.1-2025-04-14",
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-nano-2025-04-14",
        "gpt-4o",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-11-20",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
    ],
)

##################################################################

# Span-related constants
SPAN_KIND_LLM = "LLM"
SPAN_KIND_TOOL = "TOOL"
SPAN_VERSION_KEY = "arthur_span_version"
EXPECTED_SPAN_VERSION = "arthur_span_v1"
TASK_ID_KEY = "arthur.task"
METADATA_KEY = "metadata"
SPAN_KIND_KEY = "openinference.span.kind"

##################################################################

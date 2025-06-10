##################################################################
# Application Server
GENAI_ENGINE_INGRESS_URI_ENV_VAR = "GENAI_ENGINE_INGRESS_URI"
GENAI_ENGINE_ADMIN_KEY_ENV_VAR = "GENAI_ENGINE_ADMIN_KEY"
GENAI_ENGINE_ENVIRONMENT_ENV_VAR = "GENAI_ENGINE_ENVIRONMENT"
GENAI_ENGINE_LOG_LEVEL_ENV_VAR = "GENAI_ENGINE_LOG_LEVEL"
ALLOW_ADMIN_KEY_GENERAL_ACCESS_ENV_VAR = "ALLOW_ADMIN_KEY_GENERAL_ACCESS"
MAX_API_KEYS_ENV_VAR = "MAX_API_KEYS"
GENAI_ENGINE_API_ONLY_MODE_ENABLED_ENV_VAR = "GENAI_ENGINE_API_ONLY_MODE_ENABLED"
GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR = "GENAI_ENGINE_ENABLE_PERSISTENCE"
DEFAULT_PAGE_SIZE = 100
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

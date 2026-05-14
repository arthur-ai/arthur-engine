import os
import uuid
from logging import _nameToLevel as allowed_log_levels

from dotenv import load_dotenv

from utils import constants
from utils.utils import get_env_var

load_dotenv()


class Config:
    @classmethod
    def api_key(cls) -> str:
        return get_env_var(constants.GENAI_ENGINE_ADMIN_KEY_ENV_VAR) or ""

    @classmethod
    def max_api_key_limit(cls) -> int:
        max_api_key_limit = (
            get_env_var(constants.MAX_API_KEYS_ENV_VAR, default="100") or "100"
        )
        return int(max_api_key_limit)

    @classmethod
    def app_secret_key(cls) -> str:
        return get_env_var(
            constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR,
            none_on_missing=True,
        ) or str(uuid.uuid4())

    @classmethod
    def allow_admin_key_general_access(cls) -> bool:
        allow_admin_key_general_access: str | None = get_env_var(
            constants.ALLOW_ADMIN_KEY_GENERAL_ACCESS_ENV_VAR,
            none_on_missing=True,
        )
        if (
            not allow_admin_key_general_access
            or allow_admin_key_general_access.upper() != "ENABLED"
        ):
            return False
        return True

    @classmethod
    def demo_mode(cls) -> bool:
        demo_mode: str | None = get_env_var(
            constants.GENAI_ENGINE_DEMO_MODE_ENV_VAR,
            none_on_missing=True,
        )
        if not demo_mode or demo_mode.upper() != "ENABLED":
            return False
        return True

    @classmethod
    def get_log_level(cls) -> str:
        log_level: str | None = get_env_var(
            constants.GENAI_ENGINE_LOG_LEVEL_ENV_VAR,
            none_on_missing=True,
        )
        if not log_level or log_level.upper() not in allowed_log_levels.keys():
            return "INFO"
        return log_level.upper()

    @classmethod
    def audit_log_enabled(cls) -> bool:
        audit_log_enabled = get_env_var(
            constants.AUDIT_LOG_ENABLED_ENV_VAR,
            default="true",
        )
        return audit_log_enabled.lower() == "true"

    @classmethod
    def audit_log_retention_days(cls) -> int:
        audit_log_retention_days = get_env_var(
            constants.AUDIT_LOG_RETENTION_DAYS_ENV_VAR,
            default="365",
        )
        return int(audit_log_retention_days)

    @classmethod
    def audit_log_dir(cls) -> str:
        override = get_env_var(
            constants.AUDIT_LOG_OVERRIDE_PATH_ENV_VAR,
            none_on_missing=True,
        )

        if override and override.strip().lower() != "null":
            return override.strip()

        return os.path.join(os.path.dirname(__file__), "..", "..", "audit_logs")

    @classmethod
    def demo_mode_enabled(cls) -> bool:
        demo_mode_enabled = get_env_var(
            constants.GENAI_ENGINE_DEMO_MODE_ENABLED_ENV_VAR,
            default="false",
        )
        return demo_mode_enabled.lower() == "true"

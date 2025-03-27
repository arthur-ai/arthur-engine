import uuid
from logging import _nameToLevel as allowed_log_levels

from dotenv import load_dotenv
from utils import constants
from utils.utils import get_env_var

load_dotenv()


class Config:
    @classmethod
    def api_key(cls) -> str:
        return get_env_var(constants.GENAI_ENGINE_ADMIN_KEY_ENV_VAR)

    @classmethod
    def max_api_key_limit(cls) -> int:
        max_api_key_limit = get_env_var(constants.MAX_API_KEYS_ENV_VAR, default="100")
        return int(max_api_key_limit)

    @classmethod
    def app_secret_key(cls) -> str:
        return get_env_var(
            constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR,
            none_on_missing=True,
        ) or str(uuid.uuid4())

    @classmethod
    def allow_admin_key_general_access(cls) -> bool:
        return (
            get_env_var(
                constants.ALLOW_ADMIN_KEY_GENERAL_ACCESS_ENV_VAR,
                none_on_missing=True,
            )
            == "enabled"
        )

    @classmethod
    def get_log_level(cls) -> str:
        log_level = get_env_var(
            constants.GENAI_ENGINE_LOG_LEVEL_ENV_VAR,
            none_on_missing=True,
        )
        if not log_level or log_level.upper() not in allowed_log_levels.keys():
            return "INFO"
        return log_level.upper()

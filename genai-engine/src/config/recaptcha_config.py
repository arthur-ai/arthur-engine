"""Configuration accessors for reCAPTCHA Enterprise.

Values are read from the environment on every call (mirroring ``Config``) so
that tests can toggle them with ``patch.dict(os.environ, ...)``. reCAPTCHA is
only considered "enabled" when the project id, site key, and REST API key are
all present; otherwise verification is skipped (fail-open) so local/dev/demo
deployments work without any reCAPTCHA setup.
"""

import logging

from utils import constants
from utils.utils import get_env_var

logger = logging.getLogger(__name__)


class RecaptchaConfig:
    @classmethod
    def project_id(cls) -> str | None:
        return get_env_var(
            constants.RECAPTCHA_ENTERPRISE_PROJECT_ID_ENV_VAR,
            none_on_missing=True,
        )

    @classmethod
    def site_key(cls) -> str | None:
        return get_env_var(
            constants.RECAPTCHA_ENTERPRISE_SITE_KEY_ENV_VAR,
            none_on_missing=True,
        )

    @classmethod
    def api_key(cls) -> str | None:
        return get_env_var(
            constants.RECAPTCHA_ENTERPRISE_API_KEY_ENV_VAR,
            none_on_missing=True,
        )

    @classmethod
    def score_threshold(cls) -> float:
        raw = get_env_var(
            constants.RECAPTCHA_ENTERPRISE_SCORE_THRESHOLD_ENV_VAR,
            none_on_missing=True,
        )
        if not raw:
            return constants.DEFAULT_RECAPTCHA_SCORE_THRESHOLD
        try:
            return float(raw)
        except ValueError:
            logger.warning(
                "Invalid %s=%r; falling back to default %s",
                constants.RECAPTCHA_ENTERPRISE_SCORE_THRESHOLD_ENV_VAR,
                raw,
                constants.DEFAULT_RECAPTCHA_SCORE_THRESHOLD,
            )
            return constants.DEFAULT_RECAPTCHA_SCORE_THRESHOLD

    @classmethod
    def expected_action(cls) -> str:
        return (
            get_env_var(
                constants.RECAPTCHA_ENTERPRISE_EXPECTED_ACTION_ENV_VAR,
                none_on_missing=True,
            )
            or constants.DEFAULT_RECAPTCHA_EXPECTED_ACTION
        )

    @classmethod
    def enabled(cls) -> bool:
        return bool(cls.project_id() and cls.site_key() and cls.api_key())

import logging

from arthur_common.models.common_schemas import AuthUserRole

from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from config import config
from schemas.internal_schemas import User
from utils import constants

logger = logging.getLogger(__name__)


class MasterAPIKeyValidator(APIKeyValidator):
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.roles = [
            AuthUserRole(
                id="42",
                name=constants.ADMIN_KEY,
                description="API Token Admin",
                composite=True,
            ),
        ]
        if config.Config().allow_admin_key_general_access():
            self.roles.append(
                AuthUserRole(
                    name=constants.ORG_ADMIN,
                    description="API Token Org Admin",
                    composite=True,
                ),
            )

    def api_key_is_valid(self, key: str) -> User | None:
        if key in self.keys:
            logger.debug("Master key used for Authentication")
            return User(
                id="master-key",
                email="",
                roles=self.roles,
            )
        return None

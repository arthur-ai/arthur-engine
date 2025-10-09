import json
import logging

import sqlalchemy.types as types

logger = logging.getLogger(__name__)


class JsonType(types.TypeDecorator):
    impl = types.LargeBinary

    def process_bind_param(self, value, engine):
        return json.dumps(value).encode("utf-8")

    def process_result_value(self, value, engine):
        if value:
            return json.loads(value)
        else:
            return {}


class RoleType(JsonType):
    def process_result_value(self, value, engine):
        if value:
            roles = json.loads(value)
            if not isinstance(roles, list):
                logger.error(f"Role must be a list: {roles}")
                raise ValueError("Role must be a list")
            return roles
        else:
            return []

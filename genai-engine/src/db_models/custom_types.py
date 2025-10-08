import json
import logging
import os

import pgvector.sqlalchemy
import sqlalchemy.types as types
from sqlalchemy import String, TypeDecorator

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


class ConditionalVectorType(TypeDecorator):
    """Vector type that falls back to String if pgvector isn't available"""

    impl = String

    def __init__(self, dimension, **kwargs):
        self.dimension = dimension
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect):
        # Check if we're in an environment that supports vector
        if (
            os.environ.get("GENAI_ENGINE_CHAT_ENABLED") == "enabled"
            or os.environ.get("CHAT_ENABLED") == "enabled"
        ):
            try:
                # Try to use vector type
                pass
                # This would need a connection to check, so this is simplified
                return pgvector.sqlalchemy.Vector(self.dimension)
            except:
                pass

        # Fall back to String
        return String()

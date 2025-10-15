import json
import logging
import os

import sqlalchemy.types as types
from cryptography.fernet import Fernet, MultiFernet

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


class EncryptedJSON(types.TypeDecorator):
    impl = types.Text

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        encryption_keys: list[Fernet] = []
        raw_keys_str = os.getenv("GENAI_ENGINE_SECRET_STORE_KEY")
        if not raw_keys_str:
            raise ValueError(
                "GENAI_ENGINE_SECRET_STORE_KEY environment variable not set",
            )
        raw_keys = raw_keys_str.split("::")
        if not any(raw_keys):
            raise ValueError(
                "GENAI_ENGINE_SECRET_STORE_KEY environment variable must contain at least one key",
            )
        for key in raw_keys:
            if key:
                encryption_keys.append(Fernet(key.encode()))

        self.cipher = MultiFernet(encryption_keys)

    def process_bind_param(self, value: dict, dialect):
        if value is None:
            return None
        json_str = json.dumps(value)
        encrypted = self.cipher.encrypt(json_str.encode())
        return encrypted.decode()

    def process_result_value(self, value: str, dialect):
        if value is None:
            return None
        decrypted = self.cipher.decrypt(value.encode())
        return json.loads(decrypted)

import base64
import json
import logging
import os

import sqlalchemy.types as types
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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
        encryption_keys: list[bytes] = []
        salt = os.getenv(
            "GENAI_ENGINE_SECRET_STORAGE_SALT",
            "some_static_or_dynamic_salt",
        ).encode()
        passphrase = os.getenv("GENAI_ENGINE_SECRET_STORE_KEY")
        if not passphrase:
            raise ValueError(
                "GENAI_ENGINE_SECRET_STORE_KEY environment variable not set",
            )
        raw_keys = passphrase.split("::")
        if not any(raw_keys):
            raise ValueError(
                "GENAI_ENGINE_SECRET_STORE_KEY environment variable must contain at least one key",
            )
        for key in raw_keys:
            if key:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend(),
                )
                encoded_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                encryption_keys.append(Fernet(encoded_key))

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

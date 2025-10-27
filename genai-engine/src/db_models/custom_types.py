import base64
import hashlib
import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy.types import LargeBinary, Text, TypeDecorator

logger = logging.getLogger(__name__)


class JsonType(TypeDecorator[Any]):
    impl = LargeBinary

    def process_bind_param(self, value, engine) -> bytes:  # type: ignore[no-untyped-def]
        return json.dumps(value).encode("utf-8")

    def process_result_value(self, value, engine) -> Any:  # type: ignore[no-untyped-def]
        if value:
            return json.loads(value)
        else:
            return {}


class RoleType(JsonType):
    def process_result_value(self, value, engine) -> list[str]:  # type: ignore[no-untyped-def]
        if value:
            roles = json.loads(value)
            if not isinstance(roles, list):
                logger.error(f"Role must be a list: {roles}")
                raise ValueError("Role must be a list")
            return roles
        else:
            return []


class EncryptedJSON(TypeDecorator[Any]):
    impl = Text

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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
                # Derive a proper 32-byte Fernet key from the provided string
                # using SHA256 hash to ensure exactly 32 bytes
                key_bytes = hashlib.sha256(key.encode()).digest()
                fernet_key = base64.urlsafe_b64encode(key_bytes)
                encryption_keys.append(Fernet(fernet_key))

        self.cipher = MultiFernet(encryption_keys)

    def process_bind_param(self, value, dialect) -> str | None:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        json_str = json.dumps(value)
        encrypted = self.cipher.encrypt(json_str.encode())
        return encrypted.decode()

    def process_result_value(self, value, dialect) -> Any:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        try:
            decrypted = self.cipher.decrypt(value.encode())
            return json.loads(decrypted)

        except InvalidToken:
            # catch this exception, otherwise if a secret key is lost, it's not possible
            # to overwrite values in the database because we must first fetch the row to update
            # and loading the row fails
            logger.error(
                "failed to decrypt secret from database, did a key get rotated or reset?",
            )
            return None

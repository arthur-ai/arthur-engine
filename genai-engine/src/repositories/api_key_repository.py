import base64
import logging
import secrets
import uuid

import bcrypt
from arthur_common.models.enums import APIKeysRolesEnum
from fastapi import HTTPException
from sqlalchemy.orm import Session

from config.config import Config
from db_models import DatabaseApiKey
from schemas.internal_schemas import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_api_key(self, description: str, roles: list[APIKeysRolesEnum]):
        # Check the number of active keys
        active_keys_count = (
            self.db_session.query(DatabaseApiKey)
            .filter(DatabaseApiKey.is_active == True)
            .count()
        )

        if active_keys_count >= Config.max_api_key_limit():
            raise HTTPException(
                status_code=400,
                detail="Maximum number of active keys reached",
            )

        key = secrets.token_urlsafe(32)  # Generate a random API key
        key_hash = self.__get_key_hash(key)

        db_api_key = DatabaseApiKey(
            id=str(uuid.uuid4()),
            key_hash=key_hash,
            description=description,
            roles=[role.value for role in roles],
        )
        self.db_session.add(db_api_key)
        self.db_session.commit()

        key_with_id = base64.b64encode(f"{db_api_key.id}:{key}".encode("utf-8")).decode(
            "utf-8",
        )
        api_key = ApiKey._from_database_model(db_api_key)
        api_key.set_key(key_with_id)

        return api_key

    def get_api_key_by_id(self, api_key_id):
        db_api_key = (
            self.db_session.query(DatabaseApiKey)
            .filter(DatabaseApiKey.id == api_key_id)
            .first()
        )
        if db_api_key is None:
            raise HTTPException(status_code=404, detail="API Key not found")
        return ApiKey._from_database_model(db_api_key)

    def get_all_active_api_keys(self) -> list[ApiKey]:
        db_api_keys = (
            self.db_session.query(DatabaseApiKey)
            .filter(DatabaseApiKey.is_active == True)
            .all()
        )
        return [ApiKey._from_database_model(key) for key in db_api_keys]

    def deactivate_api_key(self, api_key_id):
        db_api_key = (
            self.db_session.query(DatabaseApiKey)
            .filter(DatabaseApiKey.id == api_key_id)
            .first()
        )
        if db_api_key is None:
            raise HTTPException(status_code=404, detail="API Key not found")

        db_api_key.deactivate()
        self.db_session.commit()
        return ApiKey._from_database_model(db_api_key)

    def __get_key_hash(self, key: str):
        # Setting number of rounds to 9, which translates to 2^9=512 rounds of hashing. The default is 12 which
        # takes around a quarter of a second to process, reducing to 9 rounds still keeps the hashing secure but
        # improves the speed of checking hash for every api from a quarter of a second to around 0.09 seconds
        return bcrypt.hashpw(key.encode("utf-8"), bcrypt.gensalt(rounds=9)).decode(
            "utf-8",
        )

    def validate_key(self, api_key: str) -> ApiKey | None:
        try:
            api_key_id, api_key_value = (
                base64.b64decode(api_key).decode("utf-8").split(":")
            )
        except (UnicodeEncodeError, base64.binascii.Error, ValueError):
            logger.debug(f"Invalid API key: {api_key}")
            raise AttributeError("Invalid API key")
        db_api_key = (
            self.db_session.query(DatabaseApiKey)
            .filter(DatabaseApiKey.id == api_key_id)
            .filter(DatabaseApiKey.is_active == True)
            .first()
        )
        if db_api_key:
            if bcrypt.checkpw(
                api_key_value.encode("utf-8"),
                db_api_key.key_hash.encode("utf-8"),
            ):
                return ApiKey._from_database_model(db_api_key)
        return None

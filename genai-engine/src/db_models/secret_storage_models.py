from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, String
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base
from db_models.custom_types import EncryptedJSON
from schemas.enums import SecretType


class DatabaseSecretStorage(Base):
    __tablename__ = "secret_storage"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[Any] = mapped_column(EncryptedJSON)
    secret_type: Mapped[SecretType] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())

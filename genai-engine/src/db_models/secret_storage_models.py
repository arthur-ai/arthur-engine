from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import TIMESTAMP, String
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base
from db_models.custom_types import EncryptedJSON
from schemas.enums import SecretType


class DatabaseSecretStorage(Base):
    __tablename__ = "secret_storage"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[Optional[Any]] = mapped_column(
        EncryptedJSON,
        default=None,
        nullable=True,
    )
    secret_type: Mapped[SecretType] = mapped_column(String)
    project_id: Mapped[Optional[str]] = mapped_column(
        String,
        default=None,
        nullable=True,
    )
    region: Mapped[Optional[str]] = mapped_column(String, default=None, nullable=True)
    vertex_credentials: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        EncryptedJSON,
        default=None,
        nullable=True,
    )
    aws_bedrock_credentials: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        EncryptedJSON,
        default=None,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())

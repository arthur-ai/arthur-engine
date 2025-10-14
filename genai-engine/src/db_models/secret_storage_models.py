from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base
from db_models.custom_types import EncryptedJSON
from schemas.enums import ProviderEnum


class DatabaseSecretStorage(Base):
    __tablename__ = "secret_storage"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[dict] = mapped_column(EncryptedJSON)
    owner_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("api_keys.id"),
        nullable=True,
    )
    secret_type: Mapped[ProviderEnum] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())

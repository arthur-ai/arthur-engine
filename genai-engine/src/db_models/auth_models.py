from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base
from db_models.custom_types import RoleType
from utils import constants


class DatabaseUser(Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)


class DatabaseApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key_hash: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    deactivated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    roles: Mapped[list[str]] = mapped_column(
        RoleType,
        server_default=text(f"'[\"{constants.DEFAULT_RULE_ADMIN}\"]'"),
        nullable=False,
    )

    def deactivate(self) -> None:
        self.is_active = False
        self.deactivated_at = datetime.now()

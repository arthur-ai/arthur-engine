from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseApplicationConfiguration(Base):
    __tablename__ = "configurations"
    name: Mapped[str] = mapped_column(String, unique=True, primary_key=True)
    value: Mapped[str] = mapped_column(String)

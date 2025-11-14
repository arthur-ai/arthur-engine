from datetime import datetime
from typing import Any, Optional

import sqlalchemy.types as types
from sqlalchemy import TIMESTAMP, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from utils import constants
from utils.utils import get_env_var

OUTPUT_DIMENSION_SIZE_ADA_002 = 1536


class CustomerDataString(types.TypeDecorator[str]):
    """Some customers don't want us storing any of their input data, use this type instead of string to overwrite any content on SQL insert generation"""

    impl = types.String

    def process_bind_param(self, value, _) -> str | Any:  # type: ignore[no-untyped-def]
        persistence = get_env_var(constants.GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR)
        if persistence == "disabled":
            return ""
        return value


class IsArchivable(object):
    """Mixin that identifies a class as being archivable"""

    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# declarative base class
class Base(DeclarativeBase):
    pass


class SoftDeletedModel(object):
    """Mixin that includes deleted_at field for objects that can be soft-deleted.
    To match existing behavior for prompts and rag setting configurations, other fields should be nulled out / set to
    empty values if this field is set.
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
    )

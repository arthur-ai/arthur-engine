import sqlalchemy.types as types
from sqlalchemy import Boolean, Column
from sqlalchemy.orm import DeclarativeBase

from utils import constants
from utils.utils import get_env_var

OUTPUT_DIMENSION_SIZE_ADA_002 = 1536


class CustomerDataString(types.TypeDecorator):
    """Some customers don't want us storing any of their input data, use this type instead of string to overwrite any content on SQL insert generation"""

    impl = types.String

    def process_bind_param(self, value, _):
        persistence = get_env_var(constants.GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR)
        if persistence == "disabled":
            return ""
        return value


class IsArchivable(object):
    """Mixin that identifies a class as being archivable"""

    archived = Column(Boolean, nullable=False, default=False)


# declarative base class
class Base(DeclarativeBase):
    pass

from typing import TypeVar

from sqlalchemy.orm import Query

QueryT = TypeVar("QueryT", bound=Query)

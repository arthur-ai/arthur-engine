from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Query

QueryT = TypeVar("QueryT", bound=Query)
FunctionT = TypeVar("FunctionT", bound=Callable[..., Any])

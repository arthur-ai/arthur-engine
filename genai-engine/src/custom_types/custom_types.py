from typing import Any, Callable, ParamSpec, TypeVar

from sqlalchemy.orm import Query

QueryT = TypeVar("QueryT", bound=Query)
FunctionT = TypeVar("FunctionT", bound=Callable[..., Any])
P = ParamSpec("P")
T = TypeVar("T")

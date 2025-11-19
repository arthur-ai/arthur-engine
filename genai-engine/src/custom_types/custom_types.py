from typing import Any, Callable, ParamSpec, TypeVar

from sqlalchemy.orm import Query

# QueryT: A bounded TypeVar for SQLAlchemy Query objects.
# Introduced to maintain type safety in filter aggregation functions that return
# SQLAlchemy Query instances, allowing proper type inference throughout the call chain.
QueryT = TypeVar("QueryT", bound=Query)

# FunctionT: A bounded TypeVar for callable objects.
# Used in authentication decorators to preserve the original function's type signature
# when wrapping functions that require API key permission validation.
FunctionT = TypeVar("FunctionT", bound=Callable[..., Any])

# P: A ParamSpec for capturing and preserving parameter specifications.
# Enables decorators to maintain the exact parameter signature of the wrapped function,
# providing accurate type hints and IDE autocomplete for decorated callables.
P = ParamSpec("P")

# T: A generic TypeVar for preserving return types.
# Used in decorators to ensure the return type of the decorated function remains
# unchanged, maintaining type safety when applying decorators that don't modify outputs.
T = TypeVar("T")


# PadTextT: A bounded TypeVar for text strings or lists of strings.
# Used in the pad_text function to ensure the input type is either a string or a list of strings,
# and the output type is a string or a list of strings.
PadTextT = TypeVar("PadTextT", str, list[str])

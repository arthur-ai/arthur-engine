from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, cast

from arthur_common.models.common_schemas import AuthUserRole
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from custom_types.custom_types import FunctionT
from db_models.task_models import DatabaseTask
from schemas.internal_schemas import Task, User


def get_user_info_from_payload(payload: dict[str, Any]) -> User:
    roles_from_payload: list[str] = payload.get("realm_access", {}).get("roles", [])
    loaded_roles: list[AuthUserRole] = []
    for i, role in enumerate(roles_from_payload):
        loaded_roles.append(
            AuthUserRole(id=str(i), name=role, description="DUMMY", composite=True),
        )
    user = User(id=payload["sub"], email=payload["email"], roles=loaded_roles)

    if given_name := payload.get("given_name"):
        user.first_name = given_name
    if family_name := payload.get("family_name"):
        user.last_name = family_name
    return user


def permission_checker(permissions: frozenset[str]) -> Callable[[FunctionT], FunctionT]:
    """Function that check if users permissions are in given set of permissions.

    Args:
        permissions (Set): Set of permissions
    """

    def auth_required(func: FunctionT) -> FunctionT:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Function that decorates given functions. Check if user has proper permissions
            and raises proper error message.

            Raises:
                HTTPException: 401, when user is not provided from given function
                HTTPException: 403, when provided user does not have permissions

            Returns:
                _type_: called given function
            """
            user: User | None = kwargs.get("current_user", None)
            if not user:
                raise HTTPException(
                    status_code=401,
                    headers={"full_stacktrace": "false"},
                )
            if not permissions & user.get_role_names_set():
                raise HTTPException(
                    status_code=403,
                    headers={"full_stacktrace": "false"},
                )

            if iscoroutinefunction(func):
                return await func(*args, **kwargs)

            return func(*args, **kwargs)

        return cast(FunctionT, wrapper)

    return auth_required


def _is_admin(user: User | None) -> bool:
    """An admin caller has no org scope. JWT users and admin API keys."""
    return user is None or user.org_scope is None


def _get_db_session_from_kwargs(kwargs: dict[str, Any]) -> Session:
    db_session = kwargs.get("db_session")
    if db_session is None:
        raise HTTPException(
            status_code=500,
            detail="db_session missing from handler kwargs; org-scope enforcement requires it",
        )
    return cast(Session, db_session)


def _fetch_task_org_id(db_session: Session, task_id: Any) -> str | None:
    """Single-column lookup used by the org-scope decorators."""
    org_id = db_session.execute(
        select(DatabaseTask.org_id).where(DatabaseTask.id == str(task_id)),
    ).scalar_one_or_none()
    return None if org_id is None else str(org_id)


async def _call(func: FunctionT, *args: Any, **kwargs: Any) -> Any:
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


def enforce_org_scope(
    path_param: str = "task_id",
) -> Callable[[FunctionT], FunctionT]:
    """Pattern A: enforce that the path's `task_id` belongs to the caller's org.

    Admin callers (`current_user.org_scope is None`) pass through. Tenant callers
    receive 404 if the path's task does not exist or belongs to a different org.

    The decorator requires that the route handler accepts `current_user` and
    `db_session` as keyword arguments via FastAPI `Depends(...)`.
    """

    def decorator(func: FunctionT) -> FunctionT:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: User | None = kwargs.get("current_user")
            if _is_admin(user):
                return await _call(func, *args, **kwargs)

            assert user is not None  # _is_admin guarantees non-None below
            path_task_id = kwargs.get(path_param)
            if path_task_id is None:
                # Routes that consume the path's task_id via
                # `Depends(get_validated_task)` won't have it in kwargs as a
                # standalone param — fall back to the resolved Task object.
                task_obj = kwargs.get("task")
                if isinstance(task_obj, Task):
                    path_task_id = task_obj.id
            if path_task_id is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"path param {path_param!r} not in handler kwargs",
                )

            db_session = _get_db_session_from_kwargs(kwargs)
            task_org_id = _fetch_task_org_id(db_session, path_task_id)
            if task_org_id is None or task_org_id != str(user.org_scope):
                # 404 rather than 403 to prevent enumeration of foreign tasks.
                raise HTTPException(
                    status_code=404,
                    detail="Task not found",
                    headers={"full_stacktrace": "false"},
                )

            return await _call(func, *args, **kwargs)

        return cast(FunctionT, wrapper)

    return decorator


def _find_task_ids_holder(
    kwargs: dict[str, Any],
    field: str,
) -> tuple[Any, str, list[str] | None] | None:
    """Locate the `task_ids` source in handler kwargs.

    Returns (holder, key_or_attr, current_value) where holder is either the
    kwargs dict or a Pydantic model on which the field lives. Returns None when
    the field is not present anywhere.

    Looks first at direct kwargs (e.g. `task_ids: list[str] = Query(...)`),
    then at any object in kwargs that exposes the attribute (e.g. a
    `TraceQueryRequest` or `SearchTasksRequest` body model).
    """
    # Direct kwarg
    if field in kwargs:
        return kwargs, field, kwargs.get(field)

    # Nested on a Pydantic model passed via Depends/Body
    for value in kwargs.values():
        if value is None:
            continue
        if isinstance(value, (str, bytes, int, float, bool, list, dict)):
            # Avoid scanning primitive containers
            continue
        if hasattr(value, field):
            return value, field, getattr(value, field)

    return None


def _set_task_ids(holder: Any, key_or_attr: str, value: list[str]) -> None:
    if isinstance(holder, dict):
        holder[key_or_attr] = value
    else:
        setattr(holder, key_or_attr, value)


def enforce_query_org_scope(
    query_param: str = "task_ids",
) -> Callable[[FunctionT], FunctionT]:
    """Pattern D: enforce that a list of `task_ids` is within the caller's org.

    The field can live as a direct query/kwarg on the handler or as an attribute
    on a Pydantic dependency (e.g. `TraceQueryRequest.task_ids`,
    `SearchTasksRequest.task_ids`).

    If the caller is a tenant and supplies values, every value must belong to
    the caller's org or the request 403s. If the caller is a tenant and supplies
    no values (None or empty), the decorator expands the filter to all of the
    caller's org's task IDs so downstream queries are transparently scoped.

    Admin callers pass through unchanged.
    """

    def decorator(func: FunctionT) -> FunctionT:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: User | None = kwargs.get("current_user")
            if _is_admin(user):
                return await _call(func, *args, **kwargs)

            assert user is not None
            db_session = _get_db_session_from_kwargs(kwargs)
            org_task_ids = {
                str(tid)
                for tid in db_session.execute(
                    select(DatabaseTask.id).where(
                        DatabaseTask.org_id == user.org_scope,
                    ),
                ).scalars()
            }

            located = _find_task_ids_holder(kwargs, query_param)
            if located is None:
                # The handler doesn't accept this field — nothing to constrain.
                return await _call(func, *args, **kwargs)

            holder, key_or_attr, supplied = located
            if not supplied:
                # No filter supplied — inject all of the caller's org's tasks.
                _set_task_ids(holder, key_or_attr, list(org_task_ids))
            else:
                # Normalize single-value (str/UUID) into a list for validation.
                supplied_list = (
                    [supplied] if isinstance(supplied, (str, bytes)) else list(supplied)
                )
                requested = {str(tid) for tid in supplied_list}
                if not requested.issubset(org_task_ids):
                    # 403 (not 404): the caller named these IDs explicitly.
                    raise HTTPException(
                        status_code=403,
                        detail="task_ids include items outside the caller's org",
                        headers={"full_stacktrace": "false"},
                    )

            return await _call(func, *args, **kwargs)

        return cast(FunctionT, wrapper)

    return decorator

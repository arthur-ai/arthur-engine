from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, cast

from arthur_common.models.common_schemas import AuthUserRole
from fastapi import HTTPException

from custom_types.custom_types import FunctionT
from schemas.internal_schemas import User


def get_user_info_from_payload(payload: dict) -> User:
    roles_from_payload = payload.get("realm_access", {}).get("roles", [])
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

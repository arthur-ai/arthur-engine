from functools import wraps

from fastapi import HTTPException
from schemas.common_schemas import AuthUserRole
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


def permission_checker(permissions: frozenset[str]):
    """Function that check if users permissions are in given set of permissions.

    Args:
        permissions (Set): Set of permissions
    """

    def auth_required(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
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
                )
            if not permissions & user.get_role_names_set():
                raise HTTPException(
                    status_code=403,
                )
            return func(*args, **kwargs)

        return wrapper

    return auth_required

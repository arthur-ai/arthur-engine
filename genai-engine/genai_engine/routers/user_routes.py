import logging
from typing import Annotated

from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from auth.multi_validator import MultiMethodValidator
from auth.oauth_validator import validate_token
from clients.auth.abc_keycloak_client import ABCAuthClient
from dependencies import get_keycloak_client
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from routers.route_handler import GenaiEngineRoute
from schemas.common_schemas import PaginationParameters, UserPermission
from schemas.enums import (
    PermissionLevelsEnum,
    UserPermissionAction,
    UserPermissionResource,
)
from schemas.internal_schemas import User
from schemas.request_schemas import CreateUserRequest, PasswordResetRequest
from schemas.response_schemas import UserResponse
from starlette import status
from utils.users import permission_checker
from utils.utils import common_pagination_parameters, constants, public_endpoint

api_key_validator_creators = [
    APIKeyValidatorCreator(APIKeyValidatorType.USER_GEN),
]
multi_validator = MultiMethodValidator(api_key_validator_creators)
logger = logging.getLogger()

user_management_routes = APIRouter(
    prefix="/users",
    route_class=GenaiEngineRoute,
    tags=["User Management"],
)


@user_management_routes.post(
    "",
    description=f"Creates a new user with specific roles. The available roles are {constants.TASK_ADMIN} "
    f"and {constants.CHAT_USER}. The 'temporary' field is for indicating if the user password needs to be reset at the first login.",
)
@permission_checker(permissions=PermissionLevelsEnum.USER_WRITE.value)
def create_user(
    request: CreateUserRequest,
    kc_client: ABCAuthClient = Depends(get_keycloak_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    kc_client.create_user(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_management_routes.get(
    "",
    description=f"Fetch users.",
    response_model=list[UserResponse],
)
@permission_checker(permissions=PermissionLevelsEnum.USER_READ.value)
def search_users(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    search_string: Annotated[
        str | None,
        Query(
            description="Substring to match on. Will search first name, last name, email.",
        ),
    ] = None,
    kc_client: ABCAuthClient = Depends(get_keycloak_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    users = kc_client.search_users(
        search_string=search_string,
        page=pagination_parameters.page,
        page_size=pagination_parameters.page_size,
    )
    return [user._to_response_model() for user in users]


@user_management_routes.get(
    "/permissions/check",
    description=f"Checks if the current user has the requested permission. Returns 200 status code for authorized or 403 if not.",
)
@public_endpoint
def check_user_permission(
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    action: UserPermissionAction = Query(
        None,
        description="Action to check permissions of.",
    ),
    resource: UserPermissionResource = Query(
        None,
        description="Resource to check permissions of.",
    ),
    kc_client: ABCAuthClient = Depends(get_keycloak_client),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=constants.ERROR_AUTHENTICATION_REQUIRED,
            headers={"full_stacktrace": "false"},
        )
    if not action and not resource:
        raise HTTPException(
            status_code=400,
            detail=constants.ERROR_ACTION_AND_RESOURCE_REQUIRED,
        )
    if kc_client.check_user_permissions(
        current_user.id,
        UserPermission(action=action, resource=resource),
    ):
        return Response(status_code=status.HTTP_200_OK)
    else:
        return Response(status_code=403)


@user_management_routes.delete("/{user_id}", description="Delete a user.")
@permission_checker(permissions=PermissionLevelsEnum.USER_WRITE.value)
def delete_user(
    user_id: Annotated[
        str,
        Path(description="User id, not email."),
    ],
    kc_client: ABCAuthClient = Depends(get_keycloak_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    kc_client.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_management_routes.post(
    "/{user_id}/reset_password",
    description="Reset password for user.",
)
@permission_checker(permissions=PermissionLevelsEnum.PASSWORD_RESET.value)
def reset_user_password(
    user_id: str,
    request_body: PasswordResetRequest,
    current_user: Annotated[User, Depends(validate_token)],
    kc_client: ABCAuthClient = Depends(get_keycloak_client),
):
    if (
        constants.ORG_ADMIN in [role.name for role in current_user.roles]
        or user_id == current_user.id
    ):
        kc_client.reset_password(user_id=user_id, new_password=request_body.password)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't reset password for this user.",
        )

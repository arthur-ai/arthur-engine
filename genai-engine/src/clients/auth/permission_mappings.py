from arthur_common.models.common_schemas import UserPermission
from arthur_common.models.enums import UserPermissionAction, UserPermissionResource

from utils.utils import constants

ROLE_NAMES_TO_PERMISSIONS: dict[str, set[UserPermission]] = {
    constants.TASK_ADMIN: set(
        [
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.PROMPTS,
            ),
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.RESPONSES,
            ),
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.TASKS,
            ),
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.RULES,
            ),
            UserPermission(
                action=UserPermissionAction.READ,
                resource=UserPermissionResource.PROMPTS,
            ),
            UserPermission(
                action=UserPermissionAction.READ,
                resource=UserPermissionResource.RESPONSES,
            ),
            UserPermission(
                action=UserPermissionAction.READ,
                resource=UserPermissionResource.TASKS,
            ),
            UserPermission(
                action=UserPermissionAction.READ,
                resource=UserPermissionResource.RULES,
            ),
        ],
    ),
    constants.CHAT_USER: set(
        [
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.PROMPTS,
            ),
            UserPermission(
                action=UserPermissionAction.CREATE,
                resource=UserPermissionResource.RESPONSES,
            ),
        ],
    ),
}

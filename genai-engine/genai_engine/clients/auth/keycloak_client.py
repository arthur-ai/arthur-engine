import json
import logging
from copy import deepcopy
from typing import Any, List

from clients.auth.abc_keycloak_client import ABCAuthClient
from clients.auth.permission_mappings import ROLE_NAMES_TO_PERMISSIONS
from config.keycloak_config import KeyCloakSettings
from fastapi import HTTPException
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError, KeycloakPostError
from pydantic import BaseModel, TypeAdapter
from schemas.common_schemas import AuthUserRole, UserPermission
from schemas.internal_schemas import User
from schemas.request_schemas import CreateUserRequest
from utils import constants
from utils.utils import get_env_var, is_api_only_mode_enabled

logger = logging.getLogger(__name__)

KEYCLOAK_USER_INFO_CLIENT_MAPPERS = [
    {
        "name": "email",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": False,
        "config": {
            "userinfo.token.claim": "true",
            "user.attribute": "email",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "claim.name": "email",
            "jsonType.label": "String",
        },
    },
    {
        "name": "picture",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": False,
        "config": {
            "userinfo.token.claim": "true",
            "user.attribute": "picture",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "claim.name": "picture",
            "jsonType.label": "String",
        },
    },
    {
        "name": "full name",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-full-name-mapper",
        "consentRequired": False,
        "config": {
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    },
    {
        "name": "user_type",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": False,
        "config": {
            "userinfo.token.claim": "true",
            "user.attribute": "user_type",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "claim.name": "arthur.user_type",
            "jsonType.label": "String",
        },
    },
]

KEYCLOAK_CLIENT_CONFIG_KEYS_TO_COMPARE = [
    "clientId",
    "name",
    "rootUrl",
    "adminUrl",
    "description",
    "baseUrl",
    "redirectUris",
    "webOrigins",
]

KEYCLOAK_ADMIN_CLIENT_CONFIG_KEYS_TO_COMPARE = [
    "clientId",
    "name",
    "rootUrl",
    "description",
]


class AuthUser(BaseModel):
    id: str
    name: str
    email: str


class KeycloakClient(ABCAuthClient):
    def __init__(
        self,
        keycloak_settings: KeyCloakSettings,
    ):
        self.kc_settings = keycloak_settings
        self.master_realm_admin = KeycloakAdmin(
            **self.kc_settings.get_master_admin_parameters(),
        )

    def get_genai_engine_realm_admin_connection(self) -> None:
        try:
            self.master_realm_admin.get_realm(self.kc_settings.GENAI_ENGINE_REALM)
        except KeycloakGetError as err:
            if err.response_code == 404:
                logger.warning(
                    self.kc_settings.GENAI_ENGINE_REALM + "realm not created yet.",
                )
            return
        self.genai_engine_realm_admin = KeycloakAdmin(
            **self.kc_settings.get_genai_engine_admin_parameters(),
        )

    def verify_user_exists(self, user_id: str) -> None:
        try:
            self.genai_engine_realm_admin.get_user(user_id)
        except KeycloakGetError as kge:
            if "User not found" in str(kge.error_message):
                raise HTTPException(
                    status_code=404,
                    detail=constants.ERROR_USER_NOT_FOUND % user_id,
                )
            else:
                raise kge
        except:
            raise

    def get_user_id(self, user_name: str) -> str | None:
        user_id = self.genai_engine_realm_admin.get_user_id(user_name)
        return user_id

    def get_realm_roles(self) -> list[AuthUserRole]:
        roles = self.genai_engine_realm_admin.get_realm_roles()
        adapter = TypeAdapter(list[AuthUserRole])
        realm_roles = adapter.validate_python(roles)
        return realm_roles

    def get_user_realm_roles(self, user_id: str) -> list[AuthUserRole]:
        user_roles = self.genai_engine_realm_admin.get_realm_roles_of_user(user_id)
        adapter = TypeAdapter(list[AuthUserRole])
        realm_roles = adapter.validate_python(user_roles)
        return realm_roles

    def get_user_permissions(self, user_id: str) -> set[UserPermission]:
        user_roles = self.get_user_realm_roles(user_id)

        permissions: set[UserPermission] = set()
        for role in user_roles:
            if role.name in ROLE_NAMES_TO_PERMISSIONS:
                for permission in ROLE_NAMES_TO_PERMISSIONS[role.name]:
                    permissions.add(permission)

        return permissions

    def search_users(self, search_string: str, page: int, page_size: int) -> list[User]:
        search_body = {}
        if search_string:
            search_body["search"] = search_string
        if page:
            search_body["first"] = page * page_size
        if page_size:
            search_body["max"] = page_size
        resp = self.genai_engine_realm_admin.get_users(search_body)

        users: list[User] = []
        for user in resp:
            user_roles = self.get_user_realm_roles(user["id"])
            users.append(
                User(
                    id=user["id"],
                    email=user["email"],
                    first_name=user["firstName"] if "firstName" in user else None,
                    last_name=user["lastName"] if "lastName" in user else None,
                    roles=user_roles,
                ),
            )
        return users

    def delete_user(self, user_id: str):
        self.verify_user_exists(user_id)
        self.genai_engine_realm_admin.delete_user(user_id)
        return None

    def create_user(self, user_request: CreateUserRequest) -> str:
        user_exists = self.get_user_id(user_request.email)
        if user_exists:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_USER_ALREADY_EXISTS % user_request.email,
            )
        realm_roles = self.get_realm_roles()
        role_name_to_role = {role.name: role for role in realm_roles}
        for role_name in user_request.roles:
            if role_name not in role_name_to_role:
                raise HTTPException(
                    status_code=400,
                    detail=constants.ERROR_ROLE_DOESNT_EXIST % role_name,
                )

        try:
            user_id = self.genai_engine_realm_admin.create_user(
                {
                    "email": user_request.email,
                    "username": user_request.email,
                    "firstName": user_request.firstName,
                    "lastName": user_request.lastName,
                    "credentials": [
                        {
                            "value": user_request.password,
                            "type": "password",
                            "temporary": user_request.temporary,
                        },
                    ],
                    "enabled": True,
                },
            )
        except KeycloakPostError as e:
            if e.response_code == 400:
                error_description = e.error_message.decode("utf-8")
                parsed_error_description = json.loads(error_description)
                raise HTTPException(
                    status_code=400,
                    detail=parsed_error_description["error_description"],
                )
            else:
                raise
        except:
            raise

        for role_name in user_request.roles:
            role = role_name_to_role[role_name]
            # This function needs both id and name to refer to a role, only one doesn't suffice
            self.genai_engine_realm_admin.assign_realm_roles(
                user_id,
                {"id": role.id, "name": role.name},
            )

        return user_id

    def create_ui_client(self):
        genai_engine_ui_client_config = create_client_config(
            client_id=f"{get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)}-ui",
            client_name="Arthur GenAI Engine UI",
            description="Default UI client for all GenAI Engine / Chat users",
            redirect_uris=["*"],
            web_origins=["/*", get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR)],
            post_logout_redirect_uris="",
        )
        if not (
            genai_engine_client_id := self.master_realm_admin.get_client_id(
                f"{get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)}-ui",
            )
        ):
            genai_engine_client_id = self.master_realm_admin.create_client(
                genai_engine_ui_client_config,
                skip_exists=True,
            )
        else:
            genai_engine_client_config_from_kc = self.master_realm_admin.get_client(
                genai_engine_client_id,
            )
            if not compare_config(
                genai_engine_client_config_from_kc,
                genai_engine_ui_client_config,
                KEYCLOAK_CLIENT_CONFIG_KEYS_TO_COMPARE,
            ):
                logger.info("GenAI Engine client config has changed. Updating...")
                genai_engine_ui_client_config = update_client_config(
                    genai_engine_client_config_from_kc,
                )
                self.master_realm_admin.update_client(
                    genai_engine_client_id,
                    genai_engine_ui_client_config,
                )
            else:
                logger.info("GenAI Engine client config is up to date.")
        logger.info("GenAI Engine client for UI authentication flow created.")

    def create_admin_client(self):
        genai_engine_admin_client = create_confidential_client_config(
            client_id=self.kc_settings.genai_engine_realm_admin_client_id,
            client_name="Arthur GenAI Engine Admin",
            client_secret=get_env_var(
                constants.GENAI_ENGINE_AUTH_CLIENT_SECRET_ENV_VAR,
            ),
            description="Default client for all GenAI Engine administration",
            standard_flow_enabled=False,
        )
        if not (
            genai_engine_admin_client_id := self.master_realm_admin.get_client_id(
                self.kc_settings.genai_engine_realm_admin_client_id,
            )
        ):
            self.master_realm_admin.create_client(
                genai_engine_admin_client,
                skip_exists=True,
            )
        else:
            genai_engine_admin_client_config = self.master_realm_admin.get_client(
                genai_engine_admin_client_id,
            )
            if not compare_config(
                genai_engine_admin_client_config,
                genai_engine_admin_client,
                KEYCLOAK_ADMIN_CLIENT_CONFIG_KEYS_TO_COMPARE,
            ):
                logger.info("GenAI Engine admin client config has changed. Updating...")
                genai_engine_admin_client = update_client_config(
                    genai_engine_admin_client_config,
                    admin_client=True,
                )
                self.master_realm_admin.update_client(
                    genai_engine_admin_client_id,
                    genai_engine_admin_client,
                )
            else:
                logger.info("GenAI Engine admin client config is up to date.")

    def create_api_client(self):
        genai_engine_api_client_config = create_client_config(
            client_id=f"{get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)}-api",
            client_name="Arthur GenAI Engine API",
            description="Default API client for all GenAI Engine / Chat users",
            redirect_uris=["*"],
            web_origins=["/*", get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR)],
            post_logout_redirect_uris="",
            direct_access_grants_enabled=True,
        )
        if not (
            genai_engine_client_id := self.master_realm_admin.get_client_id(
                f"{get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR)}-api",
            )
        ):
            genai_engine_client_id = self.master_realm_admin.create_client(
                genai_engine_api_client_config,
                skip_exists=True,
            )
        else:
            genai_engine_client_config_from_kc = self.master_realm_admin.get_client(
                genai_engine_client_id,
            )
            if not compare_config(
                genai_engine_client_config_from_kc,
                genai_engine_api_client_config,
                KEYCLOAK_CLIENT_CONFIG_KEYS_TO_COMPARE,
            ):
                logger.info("GenAI Engine client config has changed. Updating...")
                genai_engine_api_client_config = update_client_config(
                    genai_engine_client_config_from_kc,
                )
                self.master_realm_admin.update_client(
                    genai_engine_client_id,
                    genai_engine_api_client_config,
                )
            else:
                logger.info("GenAI Engine client config is up to date.")
        logger.info("GenAI Engine client for API authentication flow created.")

    def check_user_permissions(
        self,
        user_id: str,
        permission_request: UserPermission,
    ) -> bool:
        self.verify_user_exists(user_id)
        user_permissions = self.get_user_permissions(user_id)

        return permission_request in user_permissions

    def reset_password(self, user_id: str, new_password: str) -> None:
        self.genai_engine_realm_admin.set_user_password(
            user_id=user_id,
            password=new_password,
            temporary=True,
        )

    # This function should idempotently create any necessary KeyCloak configurations
    # We should be able to get up and running with no manual intervention from a raw keycloak instance
    def bootstrap_genai_engine_keycloak(self) -> None:
        if not self.kc_settings.ENABLED:
            logger.info("Keycloak is not enabled. Skipping bootstrap.")
            return
        realms = self.master_realm_admin.get_realms()
        genai_engine_realm_exists = any(
            realm["realm"] == self.kc_settings.GENAI_ENGINE_REALM for realm in realms
        )
        if not genai_engine_realm_exists:
            logger.info(
                f"{self.kc_settings.GENAI_ENGINE_REALM} doesn't exist in the Auth server. Creating it.",
            )
            self.master_realm_admin.create_realm(
                {
                    "realm": self.kc_settings.GENAI_ENGINE_REALM,
                    "displayName": "GenAI Engine",
                    "enabled": True,
                    "registrationAllowed": False,
                    "registrationEmailAsUsername": True,
                    "rememberMe": True,
                    "loginTheme": "arthur",
                    "accountTheme": "",
                    "adminTheme": "",
                    "emailTheme": "arthur",
                    "passwordPolicy": constants.GENAI_ENGINE_KEYCLOAK_PASSWORD_POLICY,
                    "clientSessionIdleTimeout": 1800,
                    "clientSessionMaxLifespan": 36000,
                },
                skip_exists=True,
            )
            logger.info("Created GenAI Engine realm in the Auth Server.")
        self.master_realm_admin.update_realm(
            self.kc_settings.GENAI_ENGINE_REALM,
            {
                "bruteForceProtected": True,
                "maxFailureWaitSeconds": 900,
                "minimumQuickLoginWaitSeconds": 60,
                "waitIncrementSeconds": 60,
                "quickLoginCheckMilliSeconds": 1000,
                "failureFactor": 10,
                "browserSecurityHeaders": {
                    "contentSecurityPolicyReportOnly": "",
                    "xContentTypeOptions": "nosniff",
                    "referrerPolicy": "no-referrer",
                    "xRobotsTag": "none",
                    "xFrameOptions": "SAMEORIGIN",
                    "contentSecurityPolicy": "frame-src 'self'; frame-ancestors 'self'; object-src 'none'; default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'",
                    "xXSSProtection": "1; mode=block",
                    "strictTransportSecurity": "max-age=31536000; includeSubDomains",
                },
            },
        )
        logger.info(
            "GenAI Engine realm updates complete to enforce the security policies in the Auth Server.",
        )

        try:
            self.master_realm_admin.change_current_realm(
                self.kc_settings.GENAI_ENGINE_REALM,
            )
            self.create_api_client()
            self.create_admin_client()
            if not is_api_only_mode_enabled():
                logger.info("Creating the UI client.")
                self.create_ui_client()

            # assign admin client roles to arthur clients
            realm_management_client_internal_id = self.master_realm_admin.get_client_id(
                "realm-management",
            )
            admin_roles = get_admin_roles(
                self.master_realm_admin,
                realm_management_client_internal_id,
            )
            assign_client_roles(
                self.master_realm_admin,
                self.kc_settings.genai_engine_realm_admin_client_id,
                realm_management_client_internal_id,
                admin_roles,
            )
            logger.info(
                "GenAI Engine Admin client for GenAI Engine realm management created.",
            )
        except Exception as e:
            logger.error(f"Error creating GenAI Engine Admin client: {e}")
            raise
        finally:
            self.master_realm_admin.change_current_realm(self.kc_settings.ADMIN_REALM)

        self.genai_engine_realm_admin = KeycloakAdmin(
            **self.kc_settings.get_genai_engine_admin_parameters(),
        )


def create_client_config(
    client_id: str,
    client_name: str,
    description: str,
    redirect_uris: List[str] = ["*"],
    web_origins: List[str] = ["/*"],
    post_logout_redirect_uris: str = "*",
    direct_access_grants_enabled: bool = False,
) -> dict[str, Any]:
    return {
        "clientId": client_id,
        "name": client_name,
        # The ASGI server we use (uvicorn) runs in HTTP mode. It takes in headers from the ALB request
        # and assumes its host is http://server_address. It'll then produce redirect urls relative to
        # the http address. We can address this by manually crafting each redirect URL to consume the HTTPS
        # address or just rely on the load balancers to redirect HTTP traffic to HTTPS and achieve the same
        # result. This is a bit easier for local development and code hygiene so rely on the ALBs. That said
        # this information in the request must match what's in keycloak for valid urls, so setup keycloak to
        # accept these http variables by striping the https prefix:
        "rootUrl": get_env_var(
            constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR,
        ).replace(
            "https",
            "http",
        ),
        "adminUrl": get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR),
        "description": description,
        "baseUrl": "",
        "redirectUris": redirect_uris,
        "webOrigins": web_origins,
        "alwaysDisplayInConsole": True,
        "directAccessGrantsEnabled": direct_access_grants_enabled,
        "implicitFlowEnabled": False,
        "standardFlowEnabled": True,
        "serviceAccountsEnabled": False,
        "authorizationServicesEnabled": False,
        "publicClient": True,
        "frontchannelLogout": True,
        "clientAuthenticatorType": "client-secret",
        "attributes": {
            "oidc.ciba.grant.enabled": "false",
            "backchannel.logout.session.required": "true",
            "post.logout.redirect.uris": post_logout_redirect_uris,
            "display.on.consent.screen": "false",
            "oauth2.device.authorization.grant.enabled": "false",
            "backchannel.logout.revoke.offline.tokens": "false",
        },
    }


# Creates a new backend client config for a given client id, client secret, and admin url.
def create_confidential_client_config(
    client_id: str,
    client_name: str,
    client_secret: str,
    description: str,
    standard_flow_enabled: bool,
    auth_svcs_enabled: bool = True,
    redirect_uris: List[str] = ["*"],
    web_origins: List[str] = ["/*"],
    post_logout_redirect_uris: str = "*",
) -> dict[str, Any]:
    return {
        "clientId": client_id,
        "name": client_name,
        "rootUrl": get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR).replace(
            "https",
            "http",
        ),
        "description": description,
        "secret": client_secret,
        "baseUrl": "",
        "redirectUris": redirect_uris,
        "webOrigins": web_origins,
        "alwaysDisplayInConsole": True,
        "standardFlowEnabled": standard_flow_enabled,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": auth_svcs_enabled,
        "authorizationServicesEnabled": auth_svcs_enabled,
        "frontchannelLogout": True,
        "clientAuthenticatorType": "client-secret",
        "attributes": {
            "oidc.ciba.grant.enabled": "false",
            "backchannel.logout.session.required": "true",
            "post.logout.redirect.uris": post_logout_redirect_uris,
            "display.on.consent.screen": "false",
            "oauth2.device.authorization.grant.enabled": "false",
            "backchannel.logout.revoke.offline.tokens": "false",
        },
        "protocolMappers": KEYCLOAK_USER_INFO_CLIENT_MAPPERS,
    }


def update_client_config(
    client_config: dict[str, Any],
    admin_client: bool = False,
) -> dict[str, Any]:
    config = deepcopy(client_config)
    if "rootUrl" in config:
        config["rootUrl"] = get_env_var(
            constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR,
        ).replace(
            "https",
            "http",
        )
    if "adminUrl" in config:
        config["adminUrl"] = get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR)
    if "webOrigins" in config:
        config["webOrigins"] = ["/*"]
        if not admin_client:
            config["webOrigins"].append(
                get_env_var(constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR),
            )
    return config


def compare_config(
    config1: dict[str, Any],
    config2: dict[str, Any],
    keys_to_compare: list[str] = [],
) -> bool:
    for key in keys_to_compare:
        if config1[key] != config2[key]:
            return False
    return True


# Returns RoleRepresentation of admin roles for client, user, realm, and authorization management permissions:
# includes role id & role name which are the fields needed to assign these roles to a user
def get_admin_roles(
    keycloak_client: KeycloakAdmin,
    internal_client_id: str,
) -> list[dict[str, Any]]:
    admin_role_names = [
        "manage-users",
        "manage-clients",
        "manage-realm",
        "manage-authorization",
    ]
    # we need to return the role name and id for a full RoleRepresentation to assign them to clients
    roles = []
    for role_name in admin_role_names:
        role_id = dict(keycloak_client.get_client_role(internal_client_id, role_name))[
            "id"
        ]
        roles.append({"id": role_id, "name": role_name})
    return roles


# Assigns roles from the realm management client to the client specified by the client_id parameter
def assign_client_roles(
    keycloak_client: KeycloakAdmin,
    client_id: str,
    realm_mgmt_client_internal_id: str,
    roles: list[dict[str, Any]],
) -> None:
    client_internal_id = keycloak_client.get_client_id(client_id)
    service_user = keycloak_client.get_client_service_account_user(client_internal_id)
    if service_user is not None:
        service_user_id = service_user["id"]
    else:
        raise ValueError(
            "arthur-client service user could not be retrieved for permissions management",
        )
    keycloak_client.assign_client_role(
        service_user_id,
        realm_mgmt_client_internal_id,
        roles,
    )
    logger.info(f"client roles {roles} assigned to client {client_id}")
